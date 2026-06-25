# AKAFOE Mensa → Google Wallet (Smartphone, Smartwatch, etc.)

Keeps a Google Wallet pass updated with your AKAFOE Study*life* Mensa QR (the
daily MensaCard number). Single-user demo: one pass, viewable only by your own
Google account.

```
akafoe.py   Study*life* API client (login + fetch QR)
wallet.py   Google Wallet sync (setup / patch / run)
tokens/     secrets + cached session (gitignored)
```

## Prerequisites

1. **Google Wallet issuer** — get your Issuer ID from the
   [Google Wallet & Pay Console](https://pay.google.com/business/console)
   (*Google Wallet API*). Demo access is enough for your own device.
   1. Fill in some company name, company type: "trader"
   2. Go to "Google Wallet API", start with "Build you first pass"
   3. Copy the Issuer ID shown at the top of the page, we need it later.
2. **Service account** — in [Google Cloud](https://console.cloud.google.com):
   1. Create a new project (or use an existing one).
   2. Search for and enable the **Google Wallet API**
   3. Go to credentials → Create credentials → Service account, and create a new service account. Give it any name. Stick with default settings.
   4. Open the new service account, go to *Keys*, and create a new key. Choose JSON format. Download the JSON file and save it as `tokens/service-account.json`.
   5. Go back to the Wallet console (*Google Wallet API → Users*) and grant that service account email (`something...@....iam.gserviceaccount.com `) developer access.
   6. Add the same Google account you use on your phone as a user there too.

## Setup (interactive, once)

```bash
mkdir -p tokens                 # then drop service-account.json inside
docker compose up -d            # waits until setup has created the token files
docker compose exec wallet python wallet.py setup
```

You'll be asked for: **Issuer ID**, your **AKAFOE e-mail + password**, and the
**2FA code** e-mailed to you. It creates the pass and prints an *Add to Wallet*
link — open it on your phone. The Issuer ID and session tokens are saved in
`tokens/`; credentials are never stored.

## Run (daily refresh at 05:00)

```bash
docker compose up -d
```

Refreshes the barcode on start and every day at 05:00 (the QR is valid until
23:59; canteens are closed overnight, so the morning refresh is in time).

## Without Docker

```bash
python -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python wallet.py setup     # then: patch (once) or run (daemon)
```

## Notes

- Tokens eventually expire; if `run` logs a login error, re-run `setup`
  interactively (refresh / remember-device are not supported server-side).
- Keep `tokens/` private — it holds the service-account key and session tokens.


## Legal
LICENSE: MIT
This project is not affiliated with AKAFOE or Google. It is a personal project for educational purposes only. Use at your own risk.
