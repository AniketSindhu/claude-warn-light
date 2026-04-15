#!/usr/bin/env python3
"""
Hook: fires on Claude Code 'Stop' event.
If the light is still RED (user denied or session ended without approval)
→ restore original light state silently.

This script is safe to run even if the device is unreachable;
errors are silently swallowed so they never block Claude.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

try:
    from light_controller import cmd_restore
    cmd_restore()
except Exception:
    pass  # Never block Claude over a light bulb
