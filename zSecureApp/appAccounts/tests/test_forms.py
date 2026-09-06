import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

from .forms import EmailForm, OTPForm

class OTPFormTests(TestCase):

    def test_otp_form_accepts_valid_six_digit_otp(self):
        """Exactly six numeric digits should be accepted."""
        form = OTPForm(
            data={
                "otp": "123456"
            }
        )

        self.assertTrue(form.is_valid())

    def test_otp_form_accepts_otp_with_leading_zero(self):
        """OTP may legitimately start with zero."""
        form = OTPForm(
            data={
                "otp": "001234"
            }
        )

        self.assertTrue(form.is_valid())

    def test_otp_form_rejects_five_digit_otp(self):
        """OTP shorter than six digits should be rejected."""
        form = OTPForm(
            data={
                "otp": "12345"
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("otp", form.errors)

    def test_otp_form_rejects_seven_digit_otp(self):
        """OTP longer than six digits should be rejected."""
        form = OTPForm(
            data={
                "otp": "1234567"
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("otp", form.errors)

    def test_otp_form_rejects_alphabetic_otp(self):
        """OTP containing letters should be rejected."""
        form = OTPForm(
            data={
                "otp": "ABCDEF"
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Enter a valid verification code.",
            form.errors["otp"]
        )

    def test_otp_form_rejects_alphanumeric_otp(self):
        """OTP containing letters and numbers should be rejected."""
        form = OTPForm(
            data={
                "otp": "12345A"
            }
        )

        self.assertFalse(form.is_valid())

    def test_otp_form_rejects_special_characters(self):
        """OTP containing special characters should be rejected."""
        form = OTPForm(
            data={
                "otp": "12345!"
            }
        )

        self.assertFalse(form.is_valid())

    def test_otp_form_requires_otp(self):
        """OTP should be mandatory."""
        form = OTPForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn("otp", form.errors)

    def test_otp_form_rejects_empty_otp(self):
        """Empty OTP should be rejected."""
        form = OTPForm(
            data={
                "otp": ""
            }
        )

        self.assertFalse(form.is_valid())
