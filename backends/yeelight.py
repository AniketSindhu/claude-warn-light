"""
Yeelight backend — local LAN control (no cloud).
Requires: pip install yeelight
Setup: In the Yeelight app → bulb settings → enable "LAN Control".
"""

REQUIRES = ["yeelight"]
FRIENDLY_NAME = "Yeelight"
SETUP_HINT = "In the Yeelight app, tap your bulb → Settings → LAN Control → ON."


def discover():
    """Multicast scan for Yeelight devices on the local network."""
    from yeelight import discover_bulbs
    found = discover_bulbs(timeout=3)
    results = []
    for b in found:
        ip = b.get("ip", "")
        model = b.get("capabilities", {}).get("model", "bulb")
        name = b.get("capabilities", {}).get("name", "") or ip
        results.append({"label": f"{name} ({ip}, {model})", "ip": ip, "_raw": b})
    return results


class Light:
    def __init__(self, config):
        from yeelight import Bulb
        self._bulb = Bulb(config["ip"], auto_on=True)

    def get_state(self):
        props = self._bulb.get_properties(["power", "bright", "ct", "rgb", "color_mode"])
        return props

    def set_state(self, state):
        if state.get("power") == "off":
            self._bulb.turn_off()
            return
        mode = state.get("color_mode")
        if mode == "2":  # color temperature
            self._bulb.set_color_temp(int(state.get("ct", 4000)))
        elif mode == "1":  # rgb
            rgb_int = int(state.get("rgb", 16777215))
            r = (rgb_int >> 16) & 0xFF
            g = (rgb_int >> 8) & 0xFF
            b = rgb_int & 0xFF
            self._bulb.set_rgb(r, g, b)
        bright = int(state.get("bright", 100))
        self._bulb.set_brightness(bright)
        self._bulb.turn_on()

    def set_rgb(self, r, g, b):
        self._bulb.turn_on()
        self._bulb.set_rgb(r, g, b)

    def turn_off(self):
        self._bulb.turn_off()
