"""
Home Assistant backend — REST API.
Works with every light brand HA supports (3000+ integrations).
Requires: pip install requests
Setup: HA URL + a Long-Lived Access Token (Settings → Profile → Long-Lived Access Tokens).
"""

REQUIRES = ["requests"]
FRIENDLY_NAME = "Home Assistant"
SETUP_HINT = (
    "Go to HA → Settings → Profile → Long-Lived Access Tokens → Create Token.\n"
    "  Your HA URL is usually http://homeassistant.local:8123"
)


def discover():
    """HA cannot be auto-discovered; always requires manual URL + token."""
    return []


def list_lights(ha_url, token):
    """Return list of light entity IDs from HA."""
    import requests
    resp = requests.get(
        f"{ha_url.rstrip('/')}/api/states",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    resp.raise_for_status()
    return [s["entity_id"] for s in resp.json() if s["entity_id"].startswith("light.")]


class Light:
    def __init__(self, config):
        import requests as _r
        self._requests = _r
        self._url = config["ha_url"].rstrip("/")
        self._token = config["ha_token"]
        self._entity = config["entity_id"]

    def _headers(self):
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def get_state(self):
        resp = self._requests.get(
            f"{self._url}/api/states/{self._entity}",
            headers=self._headers(), timeout=5,
        )
        resp.raise_for_status()
        s = resp.json()
        return {
            "state": s["state"],
            "attributes": s.get("attributes", {}),
        }

    def set_state(self, state):
        if state["state"] == "off":
            self._requests.post(
                f"{self._url}/api/services/light/turn_off",
                headers=self._headers(),
                json={"entity_id": self._entity},
                timeout=5,
            )
        else:
            attrs = state.get("attributes", {})
            payload = {"entity_id": self._entity}
            if "brightness" in attrs:
                payload["brightness"] = attrs["brightness"]
            if "rgb_color" in attrs:
                payload["rgb_color"] = attrs["rgb_color"]
            elif "color_temp" in attrs:
                payload["color_temp"] = attrs["color_temp"]
            self._requests.post(
                f"{self._url}/api/services/light/turn_on",
                headers=self._headers(),
                json=payload,
                timeout=5,
            )

    def set_rgb(self, r, g, b):
        self._requests.post(
            f"{self._url}/api/services/light/turn_on",
            headers=self._headers(),
            json={"entity_id": self._entity, "rgb_color": [r, g, b], "brightness": 255},
            timeout=5,
        )

    def turn_off(self):
        self._requests.post(
            f"{self._url}/api/services/light/turn_off",
            headers=self._headers(),
            json={"entity_id": self._entity},
            timeout=5,
        )
