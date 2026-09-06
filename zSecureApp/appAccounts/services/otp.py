# otp.py
import hashlib
import hmac
import secrets

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from appAccounts.models import OTPChallenge

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5


def generate_otp():
    number = secrets.randbelow(10 ** OTP_LENGTH)

    return f"{number:0{OTP_LENGTH}d}"

def otp_digest(challenge_id, otp):
    message = f"{challenge_id}:{otp}".encode()

    return hmac.new(
        settings.OTP_PEPPER.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

def create_otp_challenge(email, purpose):

    email = email.lower().strip()

    OTPChallenge.objects.filter(
        email=email,
        purpose=purpose,
        consumed_at__isnull=True
    ).delete()

    challenge = OTPChallenge.objects.create(
        email=email,
        purpose=purpose,
        otp_digest="TEMP",
        expires_at=timezone.now()
        + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )

    otp = generate_otp()

    challenge.otp_digest = otp_digest(
        challenge.id,
        otp
    )

    challenge.save(
        update_fields=["otp_digest"]
    )

    return challenge, otp

def verify_otp(challenge, otp):

    if challenge.consumed_at:
        return False

    if challenge.expires_at < timezone.now():
        return False

    if challenge.attempts >= challenge.max_attempts:
        return False

    challenge.attempts += 1

    supplied_digest = otp_digest(
        challenge.id,
        otp
    )

    valid = hmac.compare_digest(
        supplied_digest,
        challenge.otp_digest
    )

    if valid:
        challenge.consumed_at = timezone.now()

    challenge.save(
        update_fields=[
            "attempts",
            "consumed_at"
        ]
    )

    return valid

