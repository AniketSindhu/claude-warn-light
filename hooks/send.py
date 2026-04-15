"""
Send a one-line command to the running daemon via Unix socket.
If the daemon isn't running, starts it first (one-time ~6s cost).
Never spawns a second daemon if one is already running.
"""

import os
import socket
import subprocess
import sys
import time

SOCK_PATH = "/tmp/warn-light.sock"
REPO      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEMON    = os.path.join(REPO, "daemon.py")


def _send_raw(cmd: str, timeout: float) -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(SOCK_PATH)
        s.sendall(cmd.encode())
        s.recv(16)
        s.close()
        return True
    except Exception:
        return False


def ensure_daemon_and_send(cmd: str):
    # Fast path — daemon already running
    if _send_raw(cmd, timeout=3.0):
        return

    # Daemon not running. Only start one if the socket file doesn't exist
    # (if the socket exists but we can't connect, daemon is mid-startup — just wait)
    if not os.path.exists(SOCK_PATH):
        log = open("/tmp/warn-light.log", "a")
        subprocess.Popen(
            [sys.executable, DAEMON, "_serve"],
            stdout=log, stderr=log,
            start_new_session=True,
        )

    # Wait up to 8 s for the socket to become ready
    for _ in range(40):
        time.sleep(0.2)
        if os.path.exists(SOCK_PATH):
            if _send_raw(cmd, timeout=3.0):
                return
            break

    # Last attempt
    _send_raw(cmd, timeout=3.0)
