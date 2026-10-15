#!/usr/bin/env python
import json
from time import sleep

import qrcode

from akafoe import AkafoeClient, AkafoeError

qr_code_filename = "MensaRabattCode.png"
credentials_filename = "credentials.json"


def login(akafoe: AkafoeClient):
    try:
        with open(credentials_filename, "r") as credentials_file:
            credentials = json.load(credentials_file)
            akafoe.username = credentials["username"]
            akafoe.password = credentials["password"]
    except:
        print(f"Failed to read {credentials_filename} and retrieve Akafö credentials!")
        # hard exit on failiue (if anyone else want's to use this they should probably change this
        exit()

    """
    Login
    2 options: write an email client which waits for that speciffic email and inserts the code automatically,
    and with that expose my RUB login to my RasPi, or at least write a notification service
    which tells me when I need to manually run the login procedure again.

    Third option: abuse the file syncing of syncthing to make me paste the 2fa code into a file in my sync folder,
    which this script then grabs and uses to log in....
    I will likely run into a timeout with this method as I suspect I won't notice the notification in time.
    """

    # this can raise a AkafoeError
    akafoe.login()


def store_qr_code(akafoe: AkafoeClient):
    qr_value = akafoe.get_qr_value()

    qr_code_image = qrcode.make(qr_value)
    qr_code_image.save(qr_code_filename)


if __name__ == "__main__":
    akafoe = AkafoeClient()

    success = False

    if not akafoe.access:
        print("grabbing login")
        login(akafoe)

    for attempts in range(10):
        try:
            print("trying to get qr code")
            store_qr_code(akafoe)
            print("Sucessfully generated discount QR Code")
            success = True
            break
        except AkafoeError as err:
            print(err)  # log error to console
            sleep(10)  # wait 10s and hope the error resolves itself
            login(akafoe)  # assume issue was with login, so log back in as user

    # Notify me of (login) falioure
    if not success:
        import os

        # Remove outdated QR-Code in case of failiure
        os.remove(qr_code_filename)
