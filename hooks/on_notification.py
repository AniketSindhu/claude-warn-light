#!/usr/bin/env python3
"""
Hook: fires on Claude Code 'Notification' event.
Claude is waiting for the user's attention → turn the light RED.

This script is safe to run even if the device is unreachable;
errors are silently swallowed so they never block Claude.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

try:
    from light_controller import cmd_save_and_red
    cmd_save_and_red()
except Exception:
    pass  # Never block Claude over a light bulb
