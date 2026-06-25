"""Log in to the akafoe Study*life* API and fetch the Mensa QR value.

  POST /api/sanctum/token                 {email, password, device_name}
  POST /api/2fa/verify                    {code, remember_device, device_name}
  GET  /api/student-verification/qr-code  Authorization: Bearer <token>

Credentials are prompted interactively and never stored; only the resulting
session tokens are cached in tokens/akafoe.json.
"""

from __future__ import annotations

import getpass
import json
import os
import sys

import requests

BASE = "https://akafoe.studylife.org"
DEVICE = "gwallet-staging"
TOKENS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens")
TOKEN_FILE = os.path.join(TOKENS, "akafoe.json")


class AkafoeError(RuntimeError):
    pass


def _first(d, *keys):
    """First non-empty value among keys, also looking into data/user envelopes."""
    if isinstance(d, dict):
        for k in keys:
            if d.get(k):
                return d[k]
        for env in ("data", "user", "result"):
            if isinstance(d.get(env), dict) and (v := _first(d[env], *keys)):
                return v
    return None


def _qr_value(obj):
    """Recursively find the QR barcode string (the MensaCard number)."""
    if isinstance(obj, str):
        return obj or None
    if isinstance(obj, dict):
        for k in ("card_number", "cardNumber", "qr_code", "qrCode", "value", "payload", "content", "code"):
            if isinstance(obj.get(k), str) and obj[k]:
                return obj[k]
        for v in obj.values():
            if isinstance(v, (dict, list)) and (r := _qr_value(v)):
                return r
    if isinstance(obj, list):
        for v in obj:
            if r := _qr_value(v):
                return r
    return None


def _prompt(label, secret=False):
    if not sys.stdin.isatty():
        raise AkafoeError(f"{label} required but no interactive terminal (run setup)")
    val = (getpass.getpass(f"{label}: ") if secret else input(f"{label}: ")).strip()
    if not val:
        raise AkafoeError(f"no {label} entered")
    return val


class AkafoeClient:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/json"
        self.access = self.refresh_token = self.remember = None
        self.username = self.password = None
        self._load()

    # token cache -------------------------------------------------------------

    def _load(self):
        try:
            with open(TOKEN_FILE) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self.access = d.get("access_token")
        self.refresh_token = d.get("refresh_token")
        self.remember = d.get("remember_device_token")

    def _save(self):
        os.makedirs(TOKENS, exist_ok=True)
        tmp = TOKEN_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(
                {
                    "access_token": self.access,
                    "refresh_token": self.refresh_token,
                    "remember_device_token": self.remember,
                },
                f,
                indent=2,
            )
        os.chmod(tmp, 0o600)
        os.replace(tmp, TOKEN_FILE)

    def _store(self, body):
        if rem := _first(body, "remember_device_token", "rememberDeviceToken"):
            self.remember = rem
        tok = _first(body, "access_token", "accessToken", "token")
        if tok:
            self.access = tok
            self.refresh_token = _first(body, "refresh_token", "refreshToken") or self.refresh_token
        if tok or rem:
            self._save()
        return bool(tok)

    # auth --------------------------------------------------------------------

    def _post(self, path, **body):
        r = self.s.post(BASE + path, json=body, timeout=20)
        if not r.ok:
            raise AkafoeError(f"POST {path} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    def login(self):
        self.username = self.username or _prompt("AKAFOE e-mail")
        self.password = self.password or _prompt("AKAFOE password", secret=True)
        body = self._post(
            "/api/sanctum/token",
            email=self.username,
            password=self.password,
            device_name=DEVICE,
        )
        if self._store(body):
            return self
        if _first(body, "requires_2fa", "two_factor"):
            tmp = _first(body, "temp_token", "tempToken")
            body = self._post(
                "/api/2fa/verify",
                code=_prompt("2FA code (e-mailed)"),
                remember_device=True,
                device_name=DEVICE,
                **({"temp_token": tmp} if tmp else {}),
            )
            if self._store(body):
                return self
            raise AkafoeError("2FA verify returned no access token")
        raise AkafoeError("login returned neither a token nor requires_2fa")

    # api ---------------------------------------------------------------------

    def get_qr_code(self):
        if not self.access:
            self.login()
        url = BASE + "/api/student-verification/qr-code"
        r = self.s.get(url, headers={"Authorization": f"Bearer {self.access}"}, timeout=20)
        if r.status_code == 401:
            self.access = None
            self.login()
            r = self.s.get(url, headers={"Authorization": f"Bearer {self.access}"}, timeout=20)
        if not r.ok:
            raise AkafoeError(f"GET qr-code -> {r.status_code}: {r.text[:200]}")
        return r.json()

    def get_qr_value(self):
        if v := _qr_value(self.get_qr_code()):
            return v
        raise AkafoeError("no QR value in response")


def fetch_qr_value():
    return AkafoeClient().get_qr_value()


if __name__ == "__main__":
    try:
        print(fetch_qr_value())
    except AkafoeError as e:
        raise SystemExit(f"error: {e}")
