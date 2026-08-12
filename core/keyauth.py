from __future__ import annotations

import hashlib
import os
import platform

import requests

APP_NAME = "PANEL 50 PC OPTIMIZER"
OWNER_ID = "CGpMPtEl0y"
APP_VERSION = "1.0"
APP_SECRET = "37d54a88435972fb714b702b1ddc95371adeb4954fb91ee46a6474def5f2c488"
API_URL = "https://keyauth.win/api/1.3/"


def _hwid() -> str:
    seed = f"{platform.node()}|{platform.machine()}|{platform.processor()}|{os.getenv('USERNAME', '')}"
    return hashlib.sha256(seed.encode("utf-8", "ignore")).hexdigest()


class KeyAuthClient:
    """KeyAuth v1.3 license client for PNL50 PC OPTIMIZER PRO."""

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
            if not data.get("success"):
                return False, data.get("message", "KeyAuth initialization failed")
            self.session_id = data.get("sessionid", "")
            return bool(self.session_id), data.get("message", "Initialized")
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
