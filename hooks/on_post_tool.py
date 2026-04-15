#!/usr/bin/env python3
# PostToolUse — fires right after a tool runs (i.e. right after user approves)
# Sends a quick green flash as immediate confirmation, then goes back to red.
# Full restore happens at Stop when Claude finishes the whole response.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from send import ensure_daemon_and_send
    ensure_daemon_and_send("flash-green")
except Exception:
    pass
