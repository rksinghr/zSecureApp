import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

from .services.rate_limit import (
    hash_identifier,
    allow_request,
)

class RateLimitTests(TestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_hash_identifier_is_deterministic(self):
        """The same identifier should always produce the same hash."""
        value = "user@example.com"

        hash_1 = hash_identifier(value)
        hash_2 = hash_identifier(value)

        self.assertEqual(
            hash_1,
            hash_2
        )

    def test_hash_identifier_does_not_return_plain_identifier(self):
        """The identifier should not be stored in plaintext."""
        value = "user@example.com"

        hashed = hash_identifier(value)

        self.assertNotEqual(
            hashed,
            value
        )

    def test_hash_identifier_returns_sha256_hex(self):
        """Identifier hash should be a SHA-256 hex digest."""
        hashed = hash_identifier(
            "user@example.com"
        )

        self.assertEqual(
            len(hashed),
            64
        )

        self.assertTrue(
            all(
                character in "0123456789abcdef"
                for character in hashed
            )
        )

    def test_first_request_is_allowed(self):
        """First request should be allowed."""
        result = allow_request(
            prefix="otp_email",
            identifier="user@example.com",
            limit=5,
            period=900,
        )

        self.assertTrue(result)

    def test_requests_are_allowed_until_limit(self):
        """Requests below the configured limit should be allowed."""
        for _ in range(5):
            result = allow_request(
                prefix="otp_email",
                identifier="user@example.com",
                limit=5,
                period=900,
            )

            self.assertTrue(result)

    def test_request_after_limit_is_rejected(self):
        """Requests after the configured limit should be rejected."""
        for _ in range(5):
            allow_request(
                prefix="otp_email",
                identifier="user@example.com",
                limit=5,
                period=900,
            )

        result = allow_request(
            prefix="otp_email",
            identifier="user@example.com",
            limit=5,
            period=900,
        )

        self.assertFalse(result)

    def test_different_identifiers_have_separate_limits(self):
        """Rate limits should be independent for different identifiers."""
        for _ in range(5):
            allow_request(
                prefix="otp_email",
                identifier="user1@example.com",
                limit=5,
                period=900,
            )

        user1_result = allow_request(
            prefix="otp_email",
            identifier="user1@example.com",
            limit=5,
            period=900,
        )

        user2_result = allow_request(
            prefix="otp_email",
            identifier="user2@example.com",
            limit=5,
            period=900,
        )

        self.assertFalse(user1_result)
        self.assertTrue(user2_result)

    def test_different_prefixes_have_separate_limits(self):
        """Different rate-limit purposes should use separate counters."""
        for _ in range(5):
            allow_request(
                prefix="otp_email",
                identifier="user@example.com",
                limit=5,
                period=900,
            )

        email_result = allow_request(
            prefix="otp_email",
            identifier="user@example.com",
            limit=5,
            period=900,
        )

        login_result = allow_request(
            prefix="otp_login",
            identifier="user@example.com",
            limit=5,
            period=900,
        )

        self.assertFalse(email_result)
        self.assertTrue(login_result)
