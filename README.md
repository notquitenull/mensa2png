# forked from libnewton/mensa2gwallet
This is my adaptation of their work as I want to simply generate a QR-Code image.
I'll be syncing it accross my decives with syncthing (I don't use google wallet).

## Setup (interactive, once)
You'll be asked for: **Issuer ID**, your **AKAFOE e-mail + password**, and the
**2FA code** e-mailed to you. It creates the pass and prints an *Add to Wallet*
link — open it on your phone. The Issuer ID and session tokens are saved in
`tokens/`; credentials are never stored.

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
