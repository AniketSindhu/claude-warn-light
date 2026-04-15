#!/usr/bin/env python3
"""
claude-warn-light daemon
────────────────────────
Persistent background process that keeps the light connection warm.
Hooks write a single line to the Unix socket; the daemon executes instantly.

Start:   python3 daemon.py start
Stop:    python3 daemon.py stop
Status:  python3 daemon.py status
Restart: python3 daemon.py restart
"""

import json
import os
import signal
import socket as socket_lib
import subprocess
import sys
import threading
import time

REPO       = os.path.dirname(os.path.abspath(__file__))
SOCK_PATH  = "/tmp/warn-light.sock"
PID_PATH   = "/tmp/warn-light.pid"
LOG_PATH   = "/tmp/warn-light.log"
CONFIG_PATH = os.path.expanduser("~/.claude/warn-light-config.json")
STATE_PATH  = os.path.expanduser("~/.claude/warn-light-state.json")

sys.path.insert(0, REPO)

# ── Global state ──────────────────────────────────────────────────────────────
_light  = None
_config = None
_lock   = threading.Lock()


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── Light helpers (run inside daemon, modules already imported) ───────────────

def _do_save_state():
    if os.path.exists(STATE_PATH):
        return  # Already saved — don't overwrite with current red state
    try:
        state = _light.get_state()
        with open(STATE_PATH, "w") as f:
            json.dump(state, f)
        log(f"State saved: {state}")
    except Exception as e:
        log(f"save_state error: {e}")


def _do_restore_state():
    if not os.path.exists(STATE_PATH):
        return
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
        _light.set_state(state)
        os.remove(STATE_PATH)
        log("State restored")
    except Exception as e:
        log(f"restore_state error: {e}")


def _do_blink_green_restore():
    if not os.path.exists(STATE_PATH):
        log("blink-green-restore: no state file, skipping")
        return
    try:
        for _ in range(2):
            _light.set_rgb(0, 220, 0)
            time.sleep(0.4)
            _light.turn_off()
            time.sleep(0.3)
        _do_restore_state()
    except Exception as e:
        log(f"blink_green error: {e}")


def _reconnect():
    global _light
    log("Reconnecting to light...")
    try:
        from controller import get_light
        _light = get_light(_config)
        _setup_persistent()
        log("Reconnected")
    except Exception as e:
        log(f"Reconnect failed: {e}")


def _setup_persistent():
    """Ask the backend to keep its socket open between calls (Tuya-specific)."""
    if _config.get("backend") == "tuya":
        try:
            _light._dev.set_socketPersistent(True)
            log("Tuya persistent socket enabled")
        except Exception:
            pass


def _heartbeat_loop():
    """Send keepalive pings every 7 s so the Tuya socket stays open."""
    while True:
        time.sleep(7)
        if _config.get("backend") == "tuya":
            try:
                with _lock:
                    _light._dev.heartbeat(nowait=True)
            except Exception:
                with _lock:
                    _reconnect()


# ── Command dispatcher ────────────────────────────────────────────────────────

COMMANDS = {
    "save-and-red": lambda: (_do_save_state(), _light.set_rgb(255, 0, 0)),
    "blink-green-restore": _do_blink_green_restore,
    "restore": _do_restore_state,
    "ping": lambda: None,
}


def handle_client(conn):
    try:
        cmd = conn.recv(64).decode().strip()
        log(f"← {cmd}")
        fn = COMMANDS.get(cmd)
        if fn:
            with _lock:
                fn()
            conn.send(b"ok\n")
        else:
            conn.send(b"unknown\n")
    except Exception as e:
        log(f"handle_client error: {e}")
        try:
            conn.send(f"err:{e}\n".encode())
        except Exception:
            pass
    finally:
        conn.close()


# ── Server ────────────────────────────────────────────────────────────────────

def run_server():
    global _light, _config

    # Load config + connect
    with open(CONFIG_PATH) as f:
        _config = json.load(f)

    log(f"Connecting to {_config.get('backend')} light...")
    from controller import get_light
    _light = get_light(_config)
    _setup_persistent()
    log("Light connected")

    # Start heartbeat thread
    threading.Thread(target=_heartbeat_loop, daemon=True).start()

    # Write PID
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))

    # Remove stale socket
    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)

    server = socket_lib.socket(socket_lib.AF_UNIX, socket_lib.SOCK_STREAM)
    server.bind(SOCK_PATH)
    server.listen(8)
    log(f"Listening on {SOCK_PATH}")

    def shutdown(sig, frame):
        log("Shutting down")
        server.close()
        for path in (SOCK_PATH, PID_PATH):
            if os.path.exists(path):
                os.remove(path)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        try:
            conn, _ = server.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
        except OSError:
            break


# ── CLI ───────────────────────────────────────────────────────────────────────

def get_pid():
    if os.path.exists(PID_PATH):
        try:
            pid = int(open(PID_PATH).read().strip())
            os.kill(pid, 0)   # check process is alive
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    return None


def cmd_start():
    if get_pid():
        print("Daemon already running")
        return
    log_f = open(LOG_PATH, "a")
    proc = subprocess.Popen(
        [sys.executable, __file__, "_serve"],
        stdout=log_f, stderr=log_f,
        close_fds=True,
    )
    # Wait up to 8 s for it to become ready
    for _ in range(40):
        time.sleep(0.2)
        if os.path.exists(SOCK_PATH):
            print(f"Daemon started (pid {proc.pid})")
            return
    print("Daemon did not start in time — check log:", LOG_PATH)


def cmd_stop():
    pid = get_pid()
    if not pid:
        print("Daemon not running")
        return
    os.kill(pid, signal.SIGTERM)
    print(f"Daemon stopped (pid {pid})")


def cmd_status():
    pid = get_pid()
    if pid:
        print(f"Running (pid {pid}), socket: {SOCK_PATH}")
    else:
        print("Not running")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    if action == "_serve":
        run_server()
    elif action == "start":
        cmd_start()
    elif action == "stop":
        cmd_stop()
    elif action == "restart":
        cmd_stop()
        time.sleep(1)
        cmd_start()
    elif action == "status":
        cmd_status()
    else:
        print(f"Usage: python3 daemon.py start|stop|restart|status")
