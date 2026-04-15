---
name: warn-light
description: Set up a smart bulb to turn red when Claude asks for approval and blink green when approved. Supports LIFX, Philips Hue, Home Assistant, Yeelight, WLED, Tuya/Wipro.
---

You are helping the user install and configure **claude-warn-light**.

When this skill is invoked, guide the user through these steps.

---

## What it does

- Light turns **RED** when Claude is waiting for your approval
- Blinks **GREEN twice** when you approve
- Restores original colour when you deny or the session ends

## Supported lights (ordered by setup ease)

| Brand | Friction |
|---|---|
| LIFX | Zero — just on same Wi-Fi |
| Philips Hue | Press button on bridge |
| Home Assistant | URL + token — works with **any** brand |
| Yeelight / Xiaomi | Enable LAN mode in app |
| WLED | IP address |
| Tuya / Wipro / Smart Life | Needs IoT developer key |

---

## Installation

**Step 1 — Get the code**

```bash
git clone https://github.com/YOUR_USERNAME/claude-warn-light.git
cd claude-warn-light
```

**Step 2 — Run the setup wizard**

```bash
python3 setup.py
```

The wizard will:
1. Scan your local network and show what lights it finds
2. Ask you to pick one (auto-detected lights are highlighted)
3. Walk through the minimum config for that type
4. Run a live test (red → green blink → restore)
5. Register the Claude Code hooks automatically

That's it. No manual editing of settings files.

---

## After setup

Re-run setup anytime to switch lights:
```bash
python3 setup.py
```

Test the light sequence manually:
```bash
python3 controller.py test
```

Manually restore if the light gets stuck red:
```bash
python3 controller.py restore
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Light doesn't respond | Check it's on the same Wi-Fi. Run `python3 controller.py test` |
| Light stays red after denial | Run `python3 controller.py restore` |
| Config lost | Re-run `python3 setup.py` |
| LIFX not found | Restart the bulb; ensure same subnet |
| Yeelight not found | App → bulb → Settings → LAN Control → ON |
| Hue button didn't work | Press within 30 seconds and try again |

---

## How hooks work

The wizard registers three Claude Code hooks in `~/.claude/settings.json`:

- **Notification** → turns light RED (Claude is waiting for attention)
- **PreToolUse** → blinks GREEN + restores (user approved, tool about to run)
- **Stop** → restores (session ended or denied while red)

All hooks fail silently so they never block Claude.
