"""
Tuya/Wipro backend — local device control.
Requires: pip install tinytuya
Setup: Needs a Local Key from iot.tuya.com (developer account required).
       This is the harder path — try other backends first.
       Run `python3 -m tinytuya wizard` to extract keys automatically.
"""

REQUIRES = ["tinytuya"]
FRIENDLY_NAME = "Tuya / Wipro / Smart Life"
SETUP_HINT = (
    "This requires a free Tuya IoT developer account at https://iot.tuya.com\n"
    "  Then run: python3 -m tinytuya wizard\n"
    "  It will auto-discover your device ID, IP, and local key."
)


def discover():
    """Scan local network for Tuya devices (returns IPs but not keys)."""
    try:
        import tinytuya
        scanner = tinytuya.scanner.devices(verbose=False)
        results = []
        for dev in (scanner or []):
            ip = dev.get("ip", "")
            name = dev.get("name", ip)
            did = dev.get("gwId", "")
            results.append({
                "label": f"{name} ({ip})",
                "ip": ip,
                "device_id": did,
                "needs_key": True,
            })
        return results
    except Exception:
        return []


def _make_device(config):
    """
    Create the right tinytuya device object.
    v3.5 devices work better with the generic Device class;
    older versions use BulbDevice for convenience methods.
    """
    import tinytuya
    version = float(config.get("version", "3.3"))
    kwargs = dict(
        dev_id=config["device_id"],
        address=config["device_ip"],
        local_key=config["local_key"],
        version=version,
    )
    if version >= 3.5:
        dev = tinytuya.Device(**kwargs)
    else:
        dev = tinytuya.BulbDevice(**kwargs)
    dev.set_socketTimeout(8)
    return dev, version


def _set_colour_raw(dev, r, g, b):
    """Send colour via raw DPS — works for both BulbDevice and generic Device."""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    # Tuya HSV string: HHHHSSSSVVVV (each 4 hex digits, 0-1000 range)
    hue = int(h * 360)
    sat = int(s * 1000)
    val = int(v * 1000)
    hsv_str = f"{hue:04x}{sat:04x}{val:04x}"

    payload = {
        "20": True,          # power on
        "21": "colour",      # mode = colour
        "24": hsv_str,       # colour HSV
    }
    dev.set_multiple_values(payload)


class Light:
    def __init__(self, config):
        self._dev, self._version = _make_device(config)

    def get_state(self):
        try:
            data = self._dev.status()
            if not data or "Error" in data:
                return {"is_on": False}
            dps = data.get("dps", {})
            return {
                "is_on": dps.get("20", False),
                "mode": dps.get("21", "white"),
                "brightness": dps.get("22", 1000),
                "colour_temp": dps.get("23", 0),
                "colour_hsv": dps.get("24", ""),
            }
        except Exception:
            return {"is_on": False}

    def set_state(self, state):
        if not state.get("is_on", True):
            self._dev.set_value(20, False)
            return
        mode = state.get("mode", "white")
        hsv = state.get("colour_hsv", "")
        if mode == "colour" and hsv:
            self._dev.set_multiple_values({"20": True, "21": "colour", "24": hsv})
        else:
            bri = max(10, min(1000, int(state.get("brightness", 1000))))
            self._dev.set_multiple_values({"20": True, "21": "white", "22": bri})

    def set_rgb(self, r, g, b):
        _set_colour_raw(self._dev, r, g, b)

    def turn_off(self):
        self._dev.set_value(20, False)
