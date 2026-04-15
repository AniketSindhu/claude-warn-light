#!/usr/bin/env python3
"""
claude-warn-light daemon
────────────────────────
Persistent background process that keeps the light connection warm.
Hooks write a single line to the Unix socket; the daemon responds instantly.

Start:   python3 daemon.py start
Stop:    python3 daemon.py stop
Status:  python3 daemon.py status
Restart: python3 daemon.py restart
"""

import fcntl
import json
import os
import signal
import socket as socket_lib
import subprocess
import sys
import threading
import time

REPO        = os.path.dirname(os.path.abspath(__file__))
SOCK_PATH   = "/tmp/warn-light.sock"
PID_PATH    = "/tmp/warn-light.pid"
LOCK_PATH   = "/tmp/warn-light.lock"   # prevents multiple daemon instances
LOG_PATH    = "/tmp/warn-light.log"
CONFIG_PATH = os.path.expanduser("~/.claude/warn-light-config.json")
STATE_PATH  = os.path.expanduser("~/.claude/warn-light-state.json")

sys.path.insert(0, REPO)

# ── Globals ───────────────────────────────────────────────────────────────────
_light  = None
_config = None
_lock   = threading.Lock()   # serialises light commands


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    # When running as daemon, stdout is already redirected to the log file.
    # Writing to the file separately would duplicate every line.
    if sys.stdout.isatty():
        # Interactive — write to file manually since stdout isn't redirected
        try:
            with open(LOG_PATH, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass
    print(line, flush=True)


# ── Light operations (always called under _lock) ──────────────────────────────

def _save_state():
    if os.path.exists(STATE_PATH):
        return  # don't overwrite — already saved the real original
    try:
        state = _light.get_state()
        with open(STATE_PATH, "w") as f:
            json.dump(state, f)
        log(f"Saved state: {state}")
    except Exception as e:
        log(f"save_state error: {e}")


def _restore_state():
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


def _blink_green_then_restore():
    """Called in a background thread — blinks green then restores."""
    with _lock:
        if not os.path.exists(STATE_PATH):
            return
        try:
            for _ in range(2):
                _light.set_rgb(0, 220, 0)
                time.sleep(0.4)
                _light.turn_off()
                time.sleep(0.3)
            _restore_state()
        except Exception as e:
            log(f"blink error: {e}")


# ── Command handlers ──────────────────────────────────────────────────────────

def handle_save_and_red():
    with _lock:
        _save_state()
        _light.set_rgb(255, 0, 0)
    return b"ok\n"


def handle_blink_green_restore():
    # Respond immediately, run blink in background so client doesn't time out
    if os.path.exists(STATE_PATH):
        threading.Thread(target=_blink_green_then_restore, daemon=True).start()
    return b"ok\n"


def handle_restore():
    with _lock:
        _restore_state()
    return b"ok\n"


COMMANDS = {
    "save-and-red":        handle_save_and_red,
    "blink-green-restore": handle_blink_green_restore,
    "restore":             handle_restore,
    "ping":                lambda: b"ok\n",
}


def handle_client(conn):
    try:
        cmd = conn.recv(64).decode().strip()
        log(f"← {cmd}")
        fn = COMMANDS.get(cmd)
        if fn:
            resp = fn()
            conn.send(resp)
        else:
            conn.send(b"unknown\n")
    except Exception as e:
        log(f"client error: {e}")
    finally:
        conn.close()


# ── Heartbeat keeps Tuya socket alive ─────────────────────────────────────────

def _heartbeat_loop():
    while True:
        time.sleep(7)
        if _config and _config.get("backend") == "tuya":
            try:
                with _lock:
                    _light._dev.heartbeat(nowait=True)
            except Exception:
                pass   # will reconnect on next real command


# ── Server ────────────────────────────────────────────────────────────────────

def run_server():
    global _light, _config

    # Exclusive lock — only one daemon at a time
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("Another daemon instance is already running. Exiting.")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        _config = json.load(f)

    log(f"Connecting to {_config.get('backend')} light...")
    from controller import get_light
    _light = get_light(_config)

    if _config.get("backend") == "tuya":
        try:
            _light._dev.set_socketPersistent(True)
            log("Tuya persistent socket enabled")
        except Exception:
            pass

    log("Light connected")
    threading.Thread(target=_heartbeat_loop, daemon=True).start()

    # Write PID
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))

    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)

    server = socket_lib.socket(socket_lib.AF_UNIX, socket_lib.SOCK_STREAM)
    server.bind(SOCK_PATH)
    server.listen(8)
    log(f"Ready on {SOCK_PATH}")

    def shutdown(sig, frame):
        log("Shutting down")
        server.close()
        for p in (SOCK_PATH, PID_PATH, LOCK_PATH):
            try: os.remove(p)
            except FileNotFoundError: pass
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

def _get_pid():
    try:
        pid = int(open(PID_PATH).read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def cmd_start():
    if _get_pid():
        print("Daemon already running")
        return
    log_f = open(LOG_PATH, "a")
    subprocess.Popen(
        [sys.executable, __file__, "_serve"],
        stdout=log_f, stderr=log_f,
        start_new_session=True,   # fully detach from parent
    )
    for _ in range(40):
        time.sleep(0.2)
        if os.path.exists(SOCK_PATH):
            pid = _get_pid()
            print(f"Daemon started (pid {pid})")
            return
    print("Daemon did not start — check log:", LOG_PATH)


def cmd_stop():
    # Kill every daemon instance, not just the one in PID file
    os.system("pkill -f 'daemon.py _serve' 2>/dev/null")
    for p in (SOCK_PATH, PID_PATH, LOCK_PATH):
        try: os.remove(p)
        except FileNotFoundError: pass
    print("Daemon stopped")


def cmd_status():
    pid = _get_pid()
    print(f"Running (pid {pid})" if pid else "Not running")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    {
        "_serve":  run_server,
        "start":   cmd_start,
        "stop":    cmd_stop,
        "restart": lambda: (cmd_stop(), time.sleep(1), cmd_start()),
        "status":  cmd_status,
    }.get(action, lambda: print("Usage: daemon.py start|stop|restart|status"))()
