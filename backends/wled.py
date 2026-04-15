"""
WLED backend — local HTTP/JSON API.
Works with any ESP8266/ESP32 LED controller running WLED firmware.
Requires: pip install requests
Setup: Just provide the IP address — no auth needed.
"""

REQUIRES = ["requests"]
FRIENDLY_NAME = "WLED"
SETUP_HINT = "No account needed. Just find your WLED device's IP (shown in its web UI or router)."


def discover():
    """mDNS-based WLED discovery (_wled._tcp)."""
    try:
        from zeroconf import ServiceBrowser, Zeroconf
        import socket, time

        found = []

        class Listener:
            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info:
                    ip = socket.inet_ntoa(info.addresses[0])
                    found.append({"label": f"WLED ({name.split('.')[0]}) @ {ip}", "ip": ip})

        zc = Zeroconf()
        ServiceBrowser(zc, "_wled._tcp.local.", Listener())
        time.sleep(2)
        zc.close()
        return found
    except Exception:
        return []


class Light:
    def __init__(self, config):
        import requests as _r
        self._requests = _r
        self._base = f"http://{config['ip']}/json"

    def get_state(self):
        resp = self._requests.get(self._base, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def set_state(self, state):
        seg = state.get("state", {}).get("seg", [{}])[0]
        on = state.get("state", {}).get("on", True)
        bri = state.get("state", {}).get("bri", 128)
        payload = {"on": on, "bri": bri}
        if "col" in seg:
            payload["seg"] = [{"col": seg["col"]}]
        self._requests.post(self._base, json={"state": payload}, timeout=5)

    def set_rgb(self, r, g, b):
        self._requests.post(
            self._base,
            json={"state": {"on": True, "bri": 255, "seg": [{"col": [[r, g, b]]}]}},
            timeout=5,
        )

    def turn_off(self):
        self._requests.post(self._base, json={"state": {"on": False}}, timeout=5)
