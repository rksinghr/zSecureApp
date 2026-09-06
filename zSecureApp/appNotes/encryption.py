import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

def get_key():
    key = base64.urlsafe_b64decode(settings.DATA_ENCRYPTION_KEY)
    if len(key) != 32:
        raise ValueError("DATA_ENCRYPTION_KEY must decode to 32 bytes.")
    return key

def encrypt_text(plaintext):
    aesgcm = AESGCM(get_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "ciphertext":
            base64.urlsafe_b64encode(
                ciphertext
            ).decode(),

        "nonce":
            base64.urlsafe_b64encode(
                nonce
            ).decode(),
    }

def decrypt_text(ciphertext, nonce):
    aesgcm = AESGCM(get_key())
    ciphertext = base64.urlsafe_b64decode(ciphertext)
    nonce = base64.urlsafe_b64decode(nonce)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    return plaintext.decode("utf-8")