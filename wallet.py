"""AKAFOE Mensa QR -> Google Wallet generic pass (single-user demo).

  python wallet.py setup   # ask issuer id, create pass, print Add-to-Wallet link
  python wallet.py patch   # refresh barcode with today's QR
  python wallet.py run     # refresh now, then daily at 05:00 (container default)
"""

import datetime
import json
import os
import sys
import time

from google.auth import crypt, jwt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import akafoe

TOKENS = akafoe.TOKENS
KEY_FILE = os.path.join(TOKENS, "service-account.json")
CONFIG_FILE = os.path.join(TOKENS, "config.json")
SCOPES = ["https://www.googleapis.com/auth/wallet_object.issuer"]
SETUP_FILES = (KEY_FILE, CONFIG_FILE, akafoe.TOKEN_FILE)
SETUP_WAIT_SECONDS = 20


def _issuer_id(setup=False):
    try:
        cfg = json.load(open(CONFIG_FILE))
    except (OSError, ValueError):
        cfg = {}
    iid = cfg.get("issuer_id")
    if not iid and setup:
        iid = input("Google Wallet Issuer ID: ").strip()
        if not iid:
            raise SystemExit("issuer id required")
        os.makedirs(TOKENS, exist_ok=True)
        json.dump({**cfg, "issuer_id": iid}, open(CONFIG_FILE, "w"), indent=2)
    if not iid:
        raise SystemExit("no issuer id; run: python wallet.py setup")
    return iid


def _wallet():
    if not os.path.exists(KEY_FILE):
        raise SystemExit(f"missing service account key: {KEY_FILE}")
    creds = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
    return creds, build("walletobjects", "v1", credentials=creds)


def _ids(issuer):
    return f"{issuer}.akafoe_mensa", f"{issuer}.akafoe_mensa_me"


def _exists(request):
    try:
        request.execute()
        return True
    except HttpError as e:
        if e.status_code == 404:
            return False
        raise


def patch(client, oid, value):
    client.genericobject().patch(
        resourceId=oid, body={"barcode": {"type": "QR_CODE", "value": value}}
    ).execute()


def ensure_pass(client, cid, oid, value):
    if not _exists(client.genericclass().get(resourceId=cid)):
        client.genericclass().insert(body={"id": cid}).execute()
    if _exists(client.genericobject().get(resourceId=oid)):
        return patch(client, oid, value)
    client.genericobject().insert(body={
        "id": oid,
        "classId": cid,
        "state": "ACTIVE",
        "cardTitle": {"defaultValue": {"language": "de", "value": "AKAFOE"}},
        "header": {"defaultValue": {"language": "de", "value": "Mensa-Ausweis"}},
        "hexBackgroundColor": "#1a73e8",
        "barcode": {"type": "QR_CODE", "value": value},
    }).execute()


def save_link(creds, cid, oid):
    claims = {
        "iss": creds.service_account_email,
        "aud": "google",
        "typ": "savetowallet",
        "payload": {"genericObjects": [{"id": oid, "classId": cid}]},
    }
    signer = crypt.RSASigner.from_service_account_file(KEY_FILE)
    return "https://pay.google.com/gp/v/save/" + jwt.encode(signer, claims).decode()


def do_patch():
    creds, client = _wallet()
    cid, oid = _ids(_issuer_id())
    patch(client, oid, akafoe.fetch_qr_value())
    print(f"{datetime.date.today()}: barcode updated")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "setup":
        issuer = _issuer_id(setup=True)
        creds, client = _wallet()
        cid, oid = _ids(issuer)
        ensure_pass(client, cid, oid, akafoe.fetch_qr_value())
        print("Add to Wallet (open on your phone):\n" + save_link(creds, cid, oid))
    elif cmd == "patch":
        do_patch()
    elif cmd == "run":
        while True:
            missing = [p for p in SETUP_FILES if not os.path.exists(p)]
            if missing:
                print(f"{datetime.datetime.now():%F %T} waiting for setup files: {', '.join(missing)}", file=sys.stderr)
                time.sleep(SETUP_WAIT_SECONDS)
                continue
            try:
                do_patch()
            except SystemExit as e:
                print(f"{datetime.datetime.now():%F %T} setup incomplete: {e}", file=sys.stderr)
                time.sleep(SETUP_WAIT_SECONDS)
                continue
            except Exception as e:
                print(f"{datetime.datetime.now():%F %T} patch failed: {e}", file=sys.stderr)
            now = datetime.datetime.now()
            nxt = now.replace(hour=5, minute=0, second=0, microsecond=0)
            if nxt <= now:
                nxt += datetime.timedelta(days=1)
            time.sleep((nxt - now).total_seconds())
    else:
        raise SystemExit("usage: wallet.py [setup|patch|run]")


if __name__ == "__main__":
    main()
