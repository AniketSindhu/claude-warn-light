#!/usr/bin/env python3
# Stop — fires when Claude finishes responding.
# Silent restore only — cleans up any stuck red state.
# The green blink already happened on PostToolUse when the user approved.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from send import ensure_daemon_and_send
    ensure_daemon_and_send("restore")
except Exception:
    pass
