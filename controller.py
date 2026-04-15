#!/usr/bin/env python3
"""
Universal light controller.
Loads the saved config, instantiates the right backend, exposes save/restore/red/green.
"""

import json
import os
import sys
import time

CONFIG_PATH = os.path.expanduser("~/.claude/warn-light-config.json")
STATE_PATH  = os.path.expanduser("~/.claude/warn-light-state.json")

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"Config not found at {CONFIG_PATH}. Run setup first:\n"
            f"  python3 {REPO}/setup.py"
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_light(config):
    backend_name = config["backend"]
    mod = __import__(f"backends.{backend_name}", fromlist=["Light"])
    return mod.Light(config)


# ── State persistence ─────────────────────────────────────────────────────────

def save_state(light):
    try:
        state = light.get_state()
        with open(STATE_PATH, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"[warn-light] save_state: {e}", file=sys.stderr)


def restore_state(light):
    if not os.path.exists(STATE_PATH):
        return
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
        light.set_state(state)
        os.remove(STATE_PATH)
    except Exception as e:
        print(f"[warn-light] restore_state: {e}", file=sys.stderr)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_save_and_red():
    config = load_config()
    light = get_light(config)
    # Only save original state on the FIRST notification.
    # If the state file already exists we're already in "waiting" mode —
    # don't overwrite it or the saved state becomes red and restore brings
    # you back to red instead of the real original colour.
    if not os.path.exists(STATE_PATH):
        save_state(light)
    light.set_rgb(255, 0, 0)


def cmd_blink_green_restore():
    if not os.path.exists(STATE_PATH):
        return  # Not in waiting state — nothing to do
    config = load_config()
    light = get_light(config)
    for _ in range(2):
        light.set_rgb(0, 220, 0)
        time.sleep(0.45)
        light.turn_off()
        time.sleep(0.35)
    restore_state(light)


def cmd_restore():
    if not os.path.exists(STATE_PATH):
        return
    config = load_config()
    light = get_light(config)
    restore_state(light)


def cmd_test():
    print("[warn-light] Running test sequence...")
    config = load_config()
    light = get_light(config)

    print("  1. Saving current state...")
    save_state(light)

    print("  2. Turning RED (simulating approval prompt)...")
    light.set_rgb(255, 0, 0)
    time.sleep(2)

    print("  3. Blinking GREEN twice (simulating approval)...")
    for _ in range(2):
        light.set_rgb(0, 220, 0)
        time.sleep(0.45)
        light.turn_off()
        time.sleep(0.35)

    print("  4. Restoring original state...")
    restore_state(light)
    print("[warn-light] Test complete.")


COMMANDS = {
    "save-and-red":         cmd_save_and_red,
    "blink-green-restore":  cmd_blink_green_restore,
    "restore":              cmd_restore,
    "test":                 cmd_test,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python3 controller.py <{'|'.join(COMMANDS)}>")
        sys.exit(1)
    try:
        COMMANDS[sys.argv[1]]()
    except Exception as e:
        print(f"[warn-light] Error: {e}", file=sys.stderr)
        sys.exit(1)
