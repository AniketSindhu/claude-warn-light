"""
Philips Hue backend — local REST API via the Hue Bridge.
Requires: pip install phue
Setup: press the button on the bridge when prompted.
"""

REQUIRES = ["phue", "requests"]
FRIENDLY_NAME = "Philips Hue"
SETUP_HINT = "Press the button on your Hue Bridge when prompted — no account needed."


def discover():
    """Find Hue bridges on the local network via Philips' N-UPnP endpoint."""
    import requests
    try:
        resp = requests.get("https://discovery.meethue.com/", timeout=5)
        return [{"label": f"Hue Bridge ({b['internalipaddress']})",
                 "ip": b["internalipaddress"], "id": b.get("id", "")}
                for b in resp.json()]
    except Exception:
        return []


def pair_and_list_lights(bridge_ip):
    """Press the bridge button before calling this. Returns list of lights."""
    from phue import Bridge
    b = Bridge(bridge_ip)
    b.connect()  # requires button press on first call
    lights = b.get_light_objects("name")
    return list(lights.keys())


class Light:
    def __init__(self, config):
        from phue import Bridge
        self._bridge = Bridge(config["bridge_ip"])
        self._bridge.connect()
        self._name = config["light_name"]

    def get_state(self):
        light = self._bridge.get_light(self._name)
        return {
            "on": light["state"]["on"],
            "bri": light["state"].get("bri", 254),
            "hue": light["state"].get("hue", 0),
            "sat": light["state"].get("sat", 0),
            "ct": light["state"].get("ct", 370),
            "colormode": light["state"].get("colormode", "ct"),
        }

    def set_state(self, state):
        if not state["on"]:
            self._bridge.set_light(self._name, "on", False)
        else:
            cmd = {"on": True, "bri": state["bri"]}
            if state.get("colormode") == "hs":
                cmd["hue"] = state["hue"]
                cmd["sat"] = state["sat"]
            elif state.get("colormode") == "ct":
                cmd["ct"] = state["ct"]
            self._bridge.set_light(self._name, cmd)

    def set_rgb(self, r, g, b):
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self._bridge.set_light(self._name, {
            "on": True,
            "hue": int(h * 65535),
            "sat": int(s * 254),
            "bri": max(1, int(v * 254)),
        })

    def turn_off(self):
        self._bridge.set_light(self._name, "on", False)
