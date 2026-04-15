"""
Shared helper: send a command to the running daemon via Unix socket.
If the daemon isn't running, starts it first (one-time cost).
"""

import os
import socket
import subprocess
import sys
import time

SOCK_PATH = "/tmp/warn-light.sock"
REPO      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEMON    = os.path.join(REPO, "daemon.py")


def send(cmd: str, timeout: float = 2.0) -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(SOCK_PATH)
        s.sendall(cmd.encode())
        s.recv(64)
        s.close()
        return True
    except Exception:
        return False


def ensure_daemon_and_send(cmd: str):
    if send(cmd):
        return

    # Daemon not running — start it (background, detached)
    log = open("/tmp/warn-light.log", "a")
    subprocess.Popen(
        [sys.executable, DAEMON, "_serve"],
        stdout=log, stderr=log,
        close_fds=True,
    )

    # Wait up to 8 s for the socket to appear
    for _ in range(40):
        time.sleep(0.2)
        if os.path.exists(SOCK_PATH):
            break

    send(cmd, timeout=3.0)
