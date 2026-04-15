#!/usr/bin/env python3
"""
Hook: Claude Code 'Stop' event.
If light is still RED (denied / session ended), restore original state.
Errors are swallowed so they never block Claude.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from controller import cmd_restore
    cmd_restore()
except Exception:
    pass
