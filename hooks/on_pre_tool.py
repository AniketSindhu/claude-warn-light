#!/usr/bin/env python3
"""
Hook: Claude Code 'PreToolUse' event.
If light is RED (state file exists), user just approved → blink GREEN + restore.
Errors are swallowed so they never block Claude.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from controller import cmd_blink_green_restore
    cmd_blink_green_restore()
except Exception:
    pass
