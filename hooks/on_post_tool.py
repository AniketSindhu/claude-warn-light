#!/usr/bin/env python3
# PostToolUse — fires right after a tool completes (i.e. right after user approves)
# Full green blink + restore to original state immediately.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from send import ensure_daemon_and_send
    ensure_daemon_and_send("blink-green-restore")
except Exception:
    pass
