#!/usr/bin/env python3
"""
Hook: fires on Claude Code 'PreToolUse' event.
If the light is currently RED (state file exists), the user just approved something
→ blink GREEN twice then restore original light state.

This script is safe to run even if the device is unreachable;
errors are silently swallowed so they never block Claude.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

try:
    from light_controller import cmd_blink_green_and_restore
    cmd_blink_green_and_restore()
except Exception:
    pass  # Never block Claude over a light bulb
