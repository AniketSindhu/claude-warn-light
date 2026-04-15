# claude-warn-light 💡

> Your room light turns **red** when Claude Code is waiting for your approval.  
> Blinks **green** when you approve. Goes back to normal when you're done.

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-hook--powered-8A2BE2?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge" />
</p>

---

## How it works

Claude Code has a [hooks system](https://docs.anthropic.com/en/docs/claude-code/hooks) that fires shell scripts on lifecycle events. This project wires three of those hooks to your smart bulb:

| Event | What happens |
|---|---|
| Claude needs your attention | 🔴 Light turns **red** |
| You approve the action | 🟢 Blinks **green** twice |
| You deny / session ends | Restores original colour |

Zero polling. Zero cloud latency. Pure local control.

---

## Supported lights

| Light | Setup friction | Protocol |
|---|---|---|
| **LIFX** | None — just on the same Wi-Fi | Local UDP |
| **Philips Hue** | Press button on bridge | Local REST |
| **Home Assistant** | URL + one token | Local REST |
| **Yeelight / Xiaomi** | One toggle in the app | Local TCP |
| **WLED** | Just an IP address | Local REST |
| **Tuya / Wipro / Smart Life** | Free IoT account + wizard | Local encrypted |

---

## Quick start

```bash
git clone https://github.com/yourusername/claude-warn-light.git
cd claude-warn-light
python3 setup.py
```

The setup wizard:
1. Scans your local network and highlights what it finds
2. Asks you to pick a light
3. Walks through the minimum config for that type
4. Runs a live test (red → green blink → restore)
5. Registers the Claude Code hooks automatically

**Restart Claude Code** after setup and you're done.

---

## Setup guides by light

### LIFX

**Friction: zero.** The bulb just needs to be on the same Wi-Fi network.

```bash
python3 setup.py
# pick LIFX — it auto-discovers and lists all bulbs
```

That's it. No app, no account, no IP address.

---

### Philips Hue

**Friction: press a button.**

```bash
python3 setup.py
# pick Philips Hue
```

The wizard finds your bridge automatically using Philips' discovery service. When prompted, press the physical button on top of the bridge — you have 30 seconds.

> Works with all Hue bulbs, light strips, and Play bars.

---

### Home Assistant

**Best choice if you have multiple brands or Tuya/Wipro lights.**  
One token gives access to everything HA already controls.

1. In Home Assistant: **Settings → Profile → Long-Lived Access Tokens → Create Token**
2. Copy the token (it's only shown once)

```bash
python3 setup.py
# pick Home Assistant
# enter your HA URL (usually http://homeassistant.local:8123)
# paste the token
# pick the light entity from the list
```

> Works with Wipro, Govee, IKEA Tradfri, Aqara, Shelly, and 3000+ other integrations.

---

### Yeelight / Xiaomi

**Friction: one toggle in the app.**

1. Open the Yeelight app
2. Tap your bulb → **Settings → LAN Control → ON**

```bash
python3 setup.py
# pick Yeelight — it auto-discovers LAN-enabled bulbs
```

> Works with all Yeelight and Mi Home bulbs that support LAN control.

---

### WLED

**Friction: just an IP address.**

```bash
python3 setup.py
# pick WLED
# enter the IP shown in the WLED web interface
```

The wizard also tries mDNS auto-discovery first — if your WLED device shows up, you won't even need to type the IP.

---

### Tuya / Wipro / Smart Life

**Friction: free developer account + a one-time wizard.**

This is the harder path, but it covers a huge range of affordable smart bulbs sold under Wipro, Atomberg, Syska, Ener-J, and dozens of other brands — all of which use the Tuya platform underneath.

**Step 1 — Create a free Tuya IoT account**

1. Go to [iot.tuya.com](https://iot.tuya.com) and sign up (free)
2. Click **Cloud → Create Cloud Project** (name it anything; pick "Smart Home")
3. Go to **Devices → Link Tuya App Account** and scan the QR code with your Wipro / Smart Life app

**Step 2 — Run the tinytuya wizard**

```bash
python3 -m tinytuya wizard
```

Enter your **API Key** and **API Secret** from the Cloud Project overview page when prompted. The wizard will print your device's ID, IP address, and local key.

> Note: Use `"version": "3.5"` if your device was manufactured after 2022.

**Step 3 — Run setup**

```bash
python3 setup.py
# pick Tuya / Wipro
# paste the device ID, IP, local key, and version from the wizard output
```

---

## Manual commands

```bash
# Run a full visual test
python3 controller.py test

# Stuck red? Restore immediately
python3 controller.py restore

# Re-run setup (switch lights, update credentials)
python3 setup.py
```

---

## How the hooks are wired

After setup, `~/.claude/settings.json` contains:

```json
{
  "hooks": {
    "Notification": [{ "hooks": [{ "type": "command", "command": "python3 .../hooks/on_notification.py" }] }],
    "PreToolUse":   [{ "hooks": [{ "type": "command", "command": "python3 .../hooks/on_pre_tool.py" }] }],
    "Stop":         [{ "hooks": [{ "type": "command", "command": "python3 .../hooks/on_stop.py" }] }]
  }
}
```

All hooks swallow exceptions silently — they will **never** block or slow down Claude.

---

## Project structure

```
claude-warn-light/
├── setup.py              # One-time interactive setup wizard
├── controller.py         # Universal controller (test, restore, etc.)
├── backends/
│   ├── lifx.py           # LIFX (local UDP, zero config)
│   ├── hue.py            # Philips Hue (local REST)
│   ├── home_assistant.py # Home Assistant (local REST)
│   ├── yeelight.py       # Yeelight (local TCP)
│   ├── wled.py           # WLED (local REST)
│   └── tuya.py           # Tuya / Wipro (local encrypted)
└── hooks/
    ├── on_notification.py # Fires when Claude needs attention → RED
    ├── on_pre_tool.py     # Fires on first tool after notification → GREEN + restore
    └── on_stop.py         # Fires when session ends → restore
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Light doesn't respond | Check it's on the same Wi-Fi. Run `python3 controller.py test` |
| Light stays red | Run `python3 controller.py restore` |
| LIFX not found | Power-cycle the bulb; ensure same subnet |
| Yeelight not found | LAN Control must be ON in the Yeelight app |
| Hue: "Link button not pressed" | Press within 30 s and retry |
| Tuya: "sign invalid" | API Secret was blank — copy the **Client Secret**, not the Client ID |
| Tuya: "Bulb not configured" | Set `"version": "3.5"` in `~/.claude/warn-light-config.json` |

---

## Requirements

- Python 3.8+
- Claude Code CLI
- A supported smart bulb on the same Wi-Fi network

Backend libraries are installed automatically by `setup.py` — only what's needed for your specific light.

---

## Contributing

PRs welcome. To add a new backend:

1. Create `backends/yourbackend.py` with `REQUIRES`, `FRIENDLY_NAME`, `SETUP_HINT`, `discover()`, and a `Light` class implementing `get_state()`, `set_state()`, `set_rgb()`, `turn_off()`
2. Add it to the `BACKEND_ORDER` list in `setup.py`

---

## License

MIT
