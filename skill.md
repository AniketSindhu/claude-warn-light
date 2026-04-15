---
name: warn-light
description: Set up a Wipro (Tuya) smart bulb to turn red when Claude asks for approval and blink green when approved.
---

You are helping the user install and configure the **claude-warn-light** skill. This skill turns a Wipro Wi-Fi smart bulb red whenever Claude Code is waiting for the user's approval, then blinks it green twice when the user approves.

Follow these steps precisely.

---

## Step 1 — Clone or locate the repo

Ask the user if they already have the `claude-warn-light` repo. If not, tell them to clone it:

```
git clone https://github.com/YOUR_USERNAME/claude-warn-light.git
cd claude-warn-light
```

If they already have it, ask for the path.

---

## Step 2 — Install tinytuya

Run in the repo directory:

```
pip3 install tinytuya
```

---

## Step 3 — Get Wipro light credentials

Wipro Wi-Fi bulbs use the Tuya platform. The user needs three values:

- **Device ID** — a ~22-character string uniquely identifying the bulb
- **Device IP** — the local IP of the bulb on their Wi-Fi (e.g. `192.168.1.42`)
- **Local Key** — a 16-character encryption key

**Easiest way to get these:**

1. Create a free account at https://iot.tuya.com
2. Go to **Cloud → Create a Cloud Project** (pick any name, select "Smart Home")
3. Under **Devices → Link Tuya App Account**, scan the QR code with the Wipro/Smart Life app
4. Your devices appear — copy the **Device ID**
5. Run the tinytuya wizard to auto-discover the IP and Local Key:

   ```
   python3 -m tinytuya wizard
   ```

   Enter the Tuya API credentials when prompted. It will write `devices.json` with all values.

**Alternative (no cloud account):**

Run the local network scan if you already know the Device ID and Local Key:

```
python3 -m tinytuya scan
```

---

## Step 4 — Write the config file

Create `~/.claude/warn-light-config.json` with the values from Step 3:

```json
{
  "device_id": "YOUR_DEVICE_ID",
  "device_ip": "192.168.1.XXX",
  "local_key": "YOUR_LOCAL_KEY",
  "version": "3.3",
  "state_file": "~/.claude/warn-light-state.json"
}
```

> Try version `3.1` if `3.3` does not work.

---

## Step 5 — Register the hooks

Add the following to `~/.claude/settings.json` (merge with any existing content):

```json
{
  "hooks": {
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /FULL/PATH/TO/claude-warn-light/hooks/on_notification.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /FULL/PATH/TO/claude-warn-light/hooks/on_pre_tool.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /FULL/PATH/TO/claude-warn-light/hooks/on_stop.py"
          }
        ]
      }
    ]
  }
}
```

Replace `/FULL/PATH/TO/claude-warn-light` with the actual absolute path to the cloned repo.

**Or run the automated install script** which does Steps 4 and 5 interactively:

```
bash install.sh
```

---

## Step 6 — Test the setup

```
python3 light_controller.py test
```

The bulb will:
1. Turn **red** (simulating an approval prompt)
2. Blink **green** twice (simulating an approval)
3. Return to its original colour

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `tinytuya not installed` | Run `pip3 install tinytuya` |
| `Config not found` | Check `~/.claude/warn-light-config.json` exists |
| Light does not respond | Check IP is reachable: `ping <device_ip>`. Ensure phone and Mac are on same Wi-Fi |
| Wrong colour / flickering | Try changing `"version"` between `"3.1"` and `"3.3"` |
| Light stays red after denial | Hook `on_stop.py` should restore it; test with `python3 light_controller.py restore` |

---

After setup, the skill operates fully automatically — no further interaction needed. The hooks run silently in the background and never block Claude.
