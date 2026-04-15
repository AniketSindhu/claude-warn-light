"""
LIFX backend — zero config, fully local UDP.
Requires: pip install lifxlan
"""

REQUIRES = ["lifxlan"]
FRIENDLY_NAME = "LIFX"
SETUP_HINT = "No account or app needed — just make sure the bulb is on the same Wi-Fi."


def discover():
    """Return list of {'label': ..., 'mac': ..., '_raw': ...}."""
    from lifxlan import LifxLAN
    lan = LifxLAN()
    devices = lan.get_lights()
    results = []
    for d in (devices or []):
        try:
            label = d.get_label()
        except Exception:
            label = str(d.mac_addr)
        results.append({"label": label, "mac": str(d.mac_addr), "_raw": d})
    return results


class Light:
    def __init__(self, config):
        from lifxlan import LifxLAN
        mac = config["mac"]
        lan = LifxLAN()
        devices = lan.get_lights() or []
        self._dev = None
        for d in devices:
            if str(d.mac_addr) == mac:
                self._dev = d
                break
        if not self._dev:
            raise RuntimeError(f"LIFX device {mac!r} not found on network.")

    def get_state(self):
        color = self._dev.get_color()        # [hue, sat, bri, kelvin]
        power = self._dev.get_power()
        return {"power": power, "color": list(color)}

    def set_state(self, state):
        if state["power"] == 0:
            self._dev.set_power(0)
        else:
            self._dev.set_color(state["color"], rapid=True)
            self._dev.set_power(65535)

    def set_rgb(self, r, g, b):
        # LIFX uses 16-bit HSBK; convert RGB → HSB
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hue = int(h * 65535)
        sat = int(s * 65535)
        bri = int(v * 65535)
        self._dev.set_color([hue, sat, bri, 3500], rapid=True)
        self._dev.set_power(65535)

    def turn_off(self):
        self._dev.set_power(0)
