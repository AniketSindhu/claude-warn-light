#!/usr/bin/env python3
"""
Hook: Claude Code 'Notification' event.
Claude is waiting for the user → turn the light RED.
Errors are swallowed so they never block Claude.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from controller import cmd_save_and_red
    cmd_save_and_red()
except Exception:
    pass
