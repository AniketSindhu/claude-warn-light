#!/usr/bin/env python3
"""
claude-warn-light setup wizard
──────────────────────────────
Auto-discovers smart lights on your network and walks through
the minimum config needed for each type. Run once, then forget.
"""

import json
import os
import sys
import subprocess
import socket
import threading
import time

REPO        = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.expanduser("~/.claude/warn-light-config.json")
SETTINGS    = os.path.expanduser("~/.claude/settings.json")

sys.path.insert(0, REPO)

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = "\033[0;31m";  G  = "\033[0;32m";  Y  = "\033[1;33m"
C  = "\033[0;36m";  B  = "\033[0;34m";  W  = "\033[1;37m"
DIM = "\033[2m";    NC = "\033[0m"

def p(text=""):   print(text)
def h(text):      print(f"\n{W}{text}{NC}")
def ok(text):     print(f"  {G}✓{NC}  {text}")
def warn(text):   print(f"  {Y}!{NC}  {text}")
def err(text):    print(f"  {R}✗{NC}  {text}")
def dim(text):    print(f"  {DIM}{text}{NC}")
def ask(prompt, default=None):
    d = f" [{default}]" if default else ""
    try:
        val = input(f"  {C}?{NC}  {prompt}{d}: ").strip()
    except (EOFError, KeyboardInterrupt):
        p(); sys.exit(0)
    return val or default or ""

def pick(options, prompt="Pick one"):
    for i, (label, _) in enumerate(options, 1):
        print(f"  {C}{i}{NC}  {label}")
    while True:
        try:
            raw = input(f"\n  {C}>{NC} {prompt}: ").strip()
        except (EOFError, KeyboardInterrupt):
            p(); sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        err(f"Enter a number between 1 and {len(options)}")


# ── Dependency installer ───────────────────────────────────────────────────────
def pip_install(packages):
    for pkg in packages:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", pkg],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            warn(f"Could not install {pkg} — you may need to run: pip3 install {pkg}")


def ensure_deps(requires):
    missing = []
    for pkg in requires:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"  Installing: {', '.join(missing)} ...", end=" ", flush=True)
        pip_install(missing)
        print("done")


# ── Network scan helpers ───────────────────────────────────────────────────────
def spinner(msg, stop_event):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while not stop_event.is_set():
        print(f"\r  {C}{frames[i % len(frames)]}{NC}  {msg}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print("\r" + " " * (len(msg) + 8) + "\r", end="", flush=True)


def scan_with_spinner(label, fn):
    stop = threading.Event()
    t = threading.Thread(target=spinner, args=(label, stop), daemon=True)
    t.start()
    try:
        result = fn()
    finally:
        stop.set()
        t.join()
    return result


# ── Backend discovery ─────────────────────────────────────────────────────────
BACKEND_ORDER = [
    ("lifx",           "LIFX",                    "Zero config — just on the same Wi-Fi"),
    ("hue",            "Philips Hue",              "Press button on bridge"),
    ("home_assistant", "Home Assistant",           "URL + token — works with ANY brand"),
    ("yeelight",       "Yeelight / Xiaomi",        "Enable LAN mode in app"),
    ("wled",           "WLED",                     "Just an IP address"),
    ("tuya",           "Tuya / Wipro / Smart Life","Needs IoT developer key (harder)"),
]


def run_discovery():
    h("Scanning your network for smart lights...")
    p()
    found = {}  # backend_name -> list of devices

    for name, friendly, hint in BACKEND_ORDER:
        try:
            mod = __import__(f"backends.{name}", fromlist=["discover", "REQUIRES"])
            ensure_deps(mod.REQUIRES)
            devices = scan_with_spinner(
                f"Scanning for {friendly}...",
                mod.discover,
            )
            if devices:
                ok(f"Found {len(devices)} {friendly} device(s)")
                for d in devices:
                    dim(f"   {d['label']}")
                found[name] = devices
            else:
                dim(f"No {friendly} devices found")
        except Exception as e:
            dim(f"Could not scan for {friendly}: {e}")

    return found


# ── Per-backend setup flows ────────────────────────────────────────────────────
def setup_lifx(devices):
    if not devices:
        warn("No LIFX devices were discovered. Make sure the bulb is on and on the same Wi-Fi.")
        return None
    h("LIFX setup")
    options = [(d["label"], d) for d in devices]
    label, device = pick(options, "Which light?")
    return {"backend": "lifx", "mac": device["mac"]}


def setup_hue(devices):
    h("Philips Hue setup")
    if not devices:
        warn("No Hue bridges found via auto-discovery.")
        ip = ask("Enter your Hue Bridge IP manually (or press Enter to skip)")
        if not ip:
            return None
        devices = [{"label": f"Hue Bridge @ {ip}", "ip": ip}]

    options = [(d["label"], d) for d in devices]
    label, bridge = pick(options, "Which Hue Bridge?")
    bridge_ip = bridge["ip"]

    p()
    warn("Press the button on your Hue Bridge NOW, then press Enter...")
    input("  Press Enter after pressing the bridge button: ")

    p("  Connecting and listing lights...")
    from backends.hue import pair_and_list_lights
    try:
        lights = pair_and_list_lights(bridge_ip)
    except Exception as e:
        err(f"Could not connect: {e}")
        return None

    if not lights:
        err("No lights found on this bridge.")
        return None

    ok(f"Found {len(lights)} light(s)")
    light_options = [(name, name) for name in lights]
    _, light_name = pick(light_options, "Which light to use?")
    return {"backend": "hue", "bridge_ip": bridge_ip, "light_name": light_name}


def setup_home_assistant(_devices):
    h("Home Assistant setup")
    p(f"  {DIM}Works with every brand HA supports — Wipro, Govee, Ikea, Aqara, etc.{NC}")
    p()
    ha_url = ask("HA URL", "http://homeassistant.local:8123")
    token   = ask("Long-Lived Access Token (Settings → Profile → scroll to bottom)")
    if not token:
        return None

    p("  Fetching lights from HA...")
    from backends.home_assistant import list_lights
    try:
        lights = list_lights(ha_url, token)
    except Exception as e:
        err(f"Could not connect: {e}")
        return None

    if not lights:
        err("No light entities found in HA.")
        return None

    ok(f"Found {len(lights)} light(s)")
    light_options = [(eid, eid) for eid in lights]
    _, entity_id = pick(light_options, "Which light?")
    return {"backend": "home_assistant", "ha_url": ha_url, "ha_token": token, "entity_id": entity_id}


def setup_yeelight(devices):
    h("Yeelight setup")
    if not devices:
        p()
        warn("No Yeelight bulbs found. Make sure LAN Control is enabled:")
        dim("Yeelight app → tap your bulb → Settings → LAN Control → ON")
        p()
        ip = ask("Enter the bulb's IP address (shown in app under Device Info)")
        if not ip:
            return None
        devices = [{"label": ip, "ip": ip}]

    options = [(d["label"], d) for d in devices]
    label, device = pick(options, "Which light?")
    return {"backend": "yeelight", "ip": device["ip"]}


def setup_wled(devices):
    h("WLED setup")
    if not devices:
        ip = ask("Enter your WLED device IP (shown in the WLED web UI or router)")
        if not ip:
            return None
        devices = [{"label": ip, "ip": ip}]

    options = [(d["label"], d) for d in devices]
    label, device = pick(options, "Which WLED device?")
    return {"backend": "wled", "ip": device["ip"]}


def setup_tuya(devices):
    h("Tuya / Wipro / Smart Life setup")
    p()
    warn("This requires a Tuya IoT Platform account (free).")
    dim("The fastest path:")
    dim("  1. Sign up at https://iot.tuya.com")
    dim("  2. Create a Cloud Project → link your Wipro/Smart Life app account")
    dim("  3. Run: python3 -m tinytuya wizard")
    dim("     It prints your device_id, ip, and local_key automatically.")
    p()
    device_id = ask("Device ID")
    device_ip = ask("Device IP")
    local_key = ask("Local Key")
    version   = ask("Tuya version", "3.3")
    if not all([device_id, device_ip, local_key]):
        return None
    return {
        "backend": "tuya",
        "device_id": device_id,
        "device_ip": device_ip,
        "local_key": local_key,
        "version": version,
    }


SETUP_FLOWS = {
    "lifx":            setup_lifx,
    "hue":             setup_hue,
    "home_assistant":  setup_home_assistant,
    "yeelight":        setup_yeelight,
    "wled":            setup_wled,
    "tuya":            setup_tuya,
}


# ── Hook injection ────────────────────────────────────────────────────────────
def inject_hooks():
    if not os.path.exists(SETTINGS):
        with open(SETTINGS, "w") as f:
            json.dump({}, f)

    with open(SETTINGS) as f:
        settings = json.load(f)

    hooks = settings.setdefault("hooks", {})

    def add(event, cmd):
        entries = hooks.setdefault(event, [])
        for entry in entries:
            for h in entry.get("hooks", []):
                if h.get("command") == cmd:
                    return  # already registered
        entries.append({"hooks": [{"type": "command", "command": cmd}]})

    py = sys.executable
    add("Notification", f"{py} {REPO}/hooks/on_notification.py")
    add("PreToolUse",   f"{py} {REPO}/hooks/on_pre_tool.py")
    add("Stop",         f"{py} {REPO}/hooks/on_stop.py")

    with open(SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)


# ── Main wizard ───────────────────────────────────────────────────────────────
def main():
    print(f"\n{C}{'─'*50}")
    print(f"  claude-warn-light  ·  setup wizard")
    print(f"{'─'*50}{NC}")
    p()
    print("  Your room light will turn RED when Claude asks")
    print("  for approval, and blink GREEN when you approve.")
    p()

    # Step 1: scan
    found = run_discovery()

    # Step 2: let user pick a backend
    p()
    h("Which light do you want to use?")
    p()

    options = []
    # Put discovered backends first
    for name, friendly, hint in BACKEND_ORDER:
        devices = found.get(name, [])
        if devices:
            options.append((f"{G}{friendly}{NC} — {len(devices)} found on your network  {DIM}({hint}){NC}", name, devices))
        else:
            options.append((f"{friendly}  {DIM}({hint}){NC}", name, []))

    # Display and pick
    for i, (label, name, devices) in enumerate(options, 1):
        marker = f"{G}●{NC}" if found.get(name) else " "
        print(f"  {C}{i}{NC} {marker} {label}")

    p()
    while True:
        try:
            raw = input(f"  {C}>{NC} Pick a number: ").strip()
        except (EOFError, KeyboardInterrupt):
            p(); sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            _, backend_name, devices = options[int(raw) - 1]
            break
        err(f"Enter 1–{len(options)}")

    # Step 3: run backend-specific setup
    config = SETUP_FLOWS[backend_name](devices)
    if not config:
        err("Setup cancelled.")
        sys.exit(1)

    # Step 4: save config
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    ok(f"Config saved to {CONFIG_PATH}")

    # Step 5: test
    p()
    h("Testing connection...")
    test_passed = False
    try:
        import controller
        controller.cmd_test()
        ok("Light test passed!")
        test_passed = True
    except Exception as e:
        err(f"Test failed: {e}")
        warn("Hooks will still be registered — fix the light and re-run to retest.")

    # Step 6: register hooks (always, even if test failed)
    p()
    h("Registering Claude Code hooks...")
    inject_hooks()
    ok(f"Hooks added to {SETTINGS}")

    if not test_passed:
        warn("Re-run 'python3 controller.py test' once the light is reachable.")

    # Done
    p()
    print(f"{G}{'─'*50}")
    print(f"  All done! Restart Claude Code to activate.")
    print(f"{'─'*50}{NC}")
    p()
    print("  From now on:")
    print(f"    {R}●{NC} Light turns RED    when Claude needs approval")
    print(f"    {G}●{NC} Blinks GREEN twice when you approve")
    print(f"    {DIM}●  Restores           when you deny or session ends{NC}")
    p()
    print(f"  Re-run anytime:  {C}python3 {REPO}/setup.py{NC}")
    print(f"  Test anytime:    {C}python3 {REPO}/controller.py test{NC}")
    p()


if __name__ == "__main__":
    main()
