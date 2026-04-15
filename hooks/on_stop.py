#!/usr/bin/env python3
# Stop — fires when Claude finishes responding → blink GREEN twice then restore
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from send import ensure_daemon_and_send
    ensure_daemon_and_send("blink-green-restore")
except Exception:
    pass
