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
    """KeyAuth v1.3 username/password authentication."""

    def __init__(self) -> None:
        self.session_id = ""
        self.user_info: dict = {}

    def init(self) -> tuple[bool, str]:
        params = {
            "type": "init",
            "name": APP_NAME,
            "ownerid": OWNER_ID,
            "ver": APP_VERSION,
        }
        try:
            response = requests.get(API_URL, params=params, timeout=12)
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                return False, data.get("message", "KeyAuth initialization failed")
            self.session_id = data.get("sessionid", "")
            return bool(self.session_id), data.get("message", "Initialized")
        except Exception as exc:
            return False, f"Authentication service unavailable: {exc}"

    def login(self, username: str, password: str) -> tuple[bool, str]:
        username = username.strip()
        password = password.strip()
        if not self.session_id:
            return False, "Secure session is not initialized."
        if not username or not password:
            return False, "Username and password are required."

        params = {
            "type": "login",
            "username": username,
            "pass": password,
            "sessionid": self.session_id,
            "name": APP_NAME,
            "ownerid": OWNER_ID,
            "hwid": _hwid(),
        }
        try:
            response = requests.get(API_URL, params=params, timeout=12)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                self.user_info = data.get("info") or {}
                return True, data.get("message", "Logged in!")
            return False, data.get("message", "Invalid username or password.")
        except Exception as exc:
            return False, f"Login failed: {exc}"

    def logout(self) -> tuple[bool, str]:
        if not self.session_id:
            return True, "Logged out."
        try:
            response = requests.get(
                API_URL,
                params={
                    "type": "logout",
                    "sessionid": self.session_id,
                    "name": APP_NAME,
                    "ownerid": OWNER_ID,
                },
                timeout=8,
            )
            data = response.json()
            ok = bool(data.get("success"))
            return ok, data.get("message", "Logged out.")
        except Exception as exc:
            return False, str(exc)
