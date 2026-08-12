from __future__ import annotations

import hashlib
import os
import platform

import requests

APP_NAME = "PANEL 50 PC OPTIMIZER"
OWNER_ID = "CGpMPtEl0y"
APP_VERSION = "1.0"
API_URL = "https://keyauth.win/api/1.3/"


def _hwid() -> str:
    seed = f"{platform.node()}|{platform.machine()}|{platform.processor()}|{os.getenv('USERNAME', '')}"
    return hashlib.sha256(seed.encode("utf-8", "ignore")).hexdigest()


class KeyAuthClient:
    """Minimal KeyAuth v1.3 license client.

    KeyAuth v1.3 does not require the application secret for init/license endpoints.
    The secret is deliberately not embedded in the public repository.
    """

    def __init__(self) -> None:
        self.session_id = ""

    def init(self) -> tuple[bool, str]:
        params = {
            "type": "init",
            "name": APP_NAME,
            "ownerid": OWNER_ID,
            "ver": APP_VERSION,
        }
        try:
            r = requests.get(API_URL, params=params, timeout=12)
            r.raise_for_status()
            data = r.json()
            self.session_id = data.get("sessionid", "")
            return bool(data.get("success")), data.get("message", "Unknown response")
        except Exception as exc:
            return False, f"KeyAuth connection failed: {exc}"

    def license(self, key: str) -> tuple[bool, str]:
        if not self.session_id:
            return False, "Session is not initialized."
        params = {
            "type": "license",
            "key": key.strip(),
            "sessionid": self.session_id,
            "name": APP_NAME,
            "ownerid": OWNER_ID,
            "hwid": _hwid(),
        }
        try:
            r = requests.get(API_URL, params=params, timeout=12)
            r.raise_for_status()
            data = r.json()
            return bool(data.get("success")), data.get("message", "License validation failed")
        except Exception as exc:
            return False, f"License validation failed: {exc}"
