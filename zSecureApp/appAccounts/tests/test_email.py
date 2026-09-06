import uuid
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.core import mail
from .services.send_email import send_registration_otp
from django.urls import reverse

class EmailFormTests(TestCase):

    def test_email_form_accepts_valid_email(self):
        """A valid email address should be accepted."""
        form = EmailForm(
            data={
                "email": "user@example.com"
            }
        )

        self.assertTrue(form.is_valid())

    def test_email_form_rejects_invalid_email(self):
        """An invalid email address should be rejected."""
        form = EmailForm(
            data={
                "email": "not-an-email"
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_form_requires_email(self):
        """Email should be mandatory."""
        form = EmailForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_form_rejects_empty_email(self):
        """An empty email should be rejected."""
        form = EmailForm(
            data={
                "email": ""
            }
        )

        self.assertFalse(form.is_valid())

    def test_email_form_accepts_uppercase_email(self):
        """
        EmailForm should accept uppercase email addresses.
        Normalization is handled later by the application.
        """
        form = EmailForm(
            data={
                "email": "USER@EXAMPLE.COM"
            }
        )

        self.assertTrue(form.is_valid())

    def test_email_form_rejects_email_over_254_characters(self):
        """Email longer than 254 characters should be rejected."""
        form = EmailForm(
            data={
                "email": ("a" * 250) + "@x.com"
            }
        )

        self.assertFalse(form.is_valid())
