import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

from .services.otp import (
    generate_otp,
    otp_digest,
    create_otp_challenge,
    verify_otp,
)

class OTPChallengeModelTests(TestCase):

    def test_otp_challenge_can_be_created(self):
        """An OTP challenge should be created successfully."""
        expires_at = timezone.now() + timedelta(minutes=10)

        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="REGISTER",
            otp_digest="a" * 64,
            expires_at=expires_at,
        )

        self.assertIsNotNone(challenge.id)
        self.assertIsInstance(challenge.id, uuid.UUID)

    def test_otp_challenge_id_is_uuid(self):
        """OTP challenge primary key should be a UUID."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="REGISTER",
            otp_digest="a" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertIsInstance(challenge.id, uuid.UUID)

    def test_otp_attempts_defaults_to_zero(self):
        """OTP attempts should start at zero."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="REGISTER",
            otp_digest="a" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertEqual(challenge.attempts, 0)

    def test_otp_max_attempts_defaults_to_five(self):
        """OTP should allow five attempts by default."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="REGISTER",
            otp_digest="a" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertEqual(challenge.max_attempts, 5)

    def test_consumed_at_defaults_to_none(self):
        """A newly created OTP should not be consumed."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="REGISTER",
            otp_digest="a" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertIsNone(challenge.consumed_at)

    def test_created_at_is_set(self):
        """created_at should be automatically populated."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="LOGIN",
            otp_digest="b" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertIsNotNone(challenge.created_at)

    def test_register_purpose_is_valid(self):
        """REGISTER should be a valid OTP purpose."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="REGISTER",
            otp_digest="a" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertEqual(challenge.purpose, "REGISTER")

    def test_login_purpose_is_valid(self):
        """LOGIN should be a valid OTP purpose."""
        challenge = OTPChallenge.objects.create(
            email="user@example.com",
            purpose="LOGIN",
            otp_digest="a" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        self.assertEqual(challenge.purpose, "LOGIN")

@override_settings(OTP_PEPPER="test-secret-pepper")
class OTPServiceTests(TestCase):

    def test_generate_otp_returns_six_digits(self):
        """Generated OTP should always contain exactly six digits."""
        otp = generate_otp()

        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_generate_otp_preserves_leading_zeroes(self):
        """
        OTP generation should return a six-character string even
        when the generated number starts with zeroes.
        """
        with patch(
            "appAccounts.services.otp.secrets.randbelow",
            return_value=123
        ):
            otp = generate_otp()

        self.assertEqual(otp, "000123")
        self.assertEqual(len(otp), 6)

    def test_otp_digest_is_deterministic(self):
        """The same challenge and OTP should produce the same digest."""
        challenge_id = uuid.uuid4()
        otp = "123456"

        digest_1 = otp_digest(challenge_id, otp)
        digest_2 = otp_digest(challenge_id, otp)

        self.assertEqual(digest_1, digest_2)

    def test_otp_digest_is_sha256_hex(self):
        """OTP digest should be a 64-character hexadecimal SHA-256 digest."""
        challenge_id = uuid.uuid4()

        digest = otp_digest(
            challenge_id,
            "123456"
        )

        self.assertEqual(len(digest), 64)
        self.assertTrue(
            all(
                character in "0123456789abcdef"
                for character in digest
            )
        )

    def test_different_otps_produce_different_digests(self):
        """Different OTPs should produce different digests."""
        challenge_id = uuid.uuid4()

        digest_1 = otp_digest(
            challenge_id,
            "123456"
        )

        digest_2 = otp_digest(
            challenge_id,
            "654321"
        )

        self.assertNotEqual(digest_1, digest_2)

    def test_different_challenges_produce_different_digests(self):
        """The same OTP should hash differently for different challenges."""
        challenge_id_1 = uuid.uuid4()
        challenge_id_2 = uuid.uuid4()

        digest_1 = otp_digest(
            challenge_id_1,
            "123456"
        )

        digest_2 = otp_digest(
            challenge_id_2,
            "123456"
        )

        self.assertNotEqual(digest_1, digest_2)

    def test_create_otp_challenge_creates_database_record(self):
        """create_otp_challenge should create an OTPChallenge."""
        challenge, otp = create_otp_challenge(
            "USER@EXAMPLE.COM",
            "REGISTER"
        )

        self.assertIsNotNone(challenge)
        self.assertIsNotNone(otp)

        self.assertEqual(
            challenge.email,
            "user@example.com"
        )

        self.assertEqual(
            challenge.purpose,
            "REGISTER"
        )

        self.assertEqual(
            len(otp),
            6
        )

        self.assertTrue(
            otp.isdigit()
        )

        self.assertEqual(
            OTPChallenge.objects.count(),
            1
        )

    def test_create_otp_challenge_normalizes_email(self):
        """OTP challenge email should be normalized."""
        challenge, otp = create_otp_challenge(
            "  USER@EXAMPLE.COM  ",
            "REGISTER"
        )

        self.assertEqual(
            challenge.email,
            "user@example.com"
        )

    def test_create_otp_challenge_does_not_store_plain_otp(self):
        """
        Plain OTP must never be stored in otp_digest.
        """
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        self.assertNotEqual(
            challenge.otp_digest,
            otp
        )

        self.assertEqual(
            challenge.otp_digest,
            otp_digest(challenge.id, otp)
        )

    def test_create_otp_challenge_sets_expiry(self):
        """OTP challenge should expire approximately five minutes later."""
        before = timezone.now()

        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        after = timezone.now()

        minimum_expiry = (
            before + timedelta(minutes=5)
        )

        maximum_expiry = (
            after + timedelta(minutes=5)
        )

        self.assertGreaterEqual(
            challenge.expires_at,
            minimum_expiry
        )

        self.assertLessEqual(
            challenge.expires_at,
            maximum_expiry
        )

    def test_create_otp_challenge_starts_with_zero_attempts(self):
        """New OTP challenges should start with zero attempts."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        self.assertEqual(
            challenge.attempts,
            0
        )

    def test_create_otp_challenge_starts_unconsumed(self):
        """New OTP challenges should not be consumed."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        self.assertIsNone(
            challenge.consumed_at
        )

    def test_new_challenge_invalidates_previous_unconsumed_challenge(self):
        """
        Creating a new OTP for the same email and purpose should
        delete the previous unconsumed challenge.
        """
        first_challenge, first_otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        second_challenge, second_otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        self.assertEqual(
            OTPChallenge.objects.filter(
                email="user@example.com",
                purpose="REGISTER"
            ).count(),
            1
        )

        self.assertFalse(
            OTPChallenge.objects.filter(
                id=first_challenge.id
            ).exists()
        )

        self.assertTrue(
            OTPChallenge.objects.filter(
                id=second_challenge.id
            ).exists()
        )

    def test_login_and_register_challenges_are_separate(self):
        """
        A REGISTER challenge should not be deleted when a LOGIN
        challenge is created for the same email.
        """
        register_challenge, register_otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        login_challenge, login_otp = create_otp_challenge(
            "user@example.com",
            "LOGIN"
        )

        self.assertTrue(
            OTPChallenge.objects.filter(
                id=register_challenge.id
            ).exists()
        )

        self.assertTrue(
            OTPChallenge.objects.filter(
                id=login_challenge.id
            ).exists()
        )

    def test_verify_otp_accepts_correct_otp(self):
        """Correct OTP should be accepted."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        result = verify_otp(
            challenge,
            otp
        )

        self.assertTrue(result)

        challenge.refresh_from_db()

        self.assertEqual(
            challenge.attempts,
            1
        )

        self.assertIsNotNone(
            challenge.consumed_at
        )

    def test_verify_otp_rejects_incorrect_otp(self):
        """Incorrect OTP should be rejected."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        result = verify_otp(
            challenge,
            "000000" if otp != "000000" else "111111"
        )

        self.assertFalse(result)

        challenge.refresh_from_db()

        self.assertEqual(
            challenge.attempts,
            1
        )

        self.assertIsNone(
            challenge.consumed_at
        )

    def test_invalid_otp_increments_attempt_count(self):
        """Each invalid OTP attempt should increase attempts."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        verify_otp(
            challenge,
            "000000" if otp != "000000" else "111111"
        )

        challenge.refresh_from_db()

        self.assertEqual(
            challenge.attempts,
            1
        )

    def test_correct_otp_consumes_challenge(self):
        """A successfully verified OTP should be marked consumed."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        verify_otp(
            challenge,
            otp
        )

        challenge.refresh_from_db()

        self.assertIsNotNone(
            challenge.consumed_at
        )

    def test_consumed_otp_cannot_be_used_again(self):
        """A consumed OTP must never be accepted again."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        first_result = verify_otp(
            challenge,
            otp
        )

        second_result = verify_otp(
            challenge,
            otp
        )

        self.assertTrue(first_result)
        self.assertFalse(second_result)

    def test_expired_otp_is_rejected(self):
        """An expired OTP should not be accepted."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        challenge.expires_at = (
            timezone.now() - timedelta(seconds=1)
        )
        challenge.save(
            update_fields=["expires_at"]
        )

        result = verify_otp(
            challenge,
            otp
        )

        self.assertFalse(result)

        challenge.refresh_from_db()

        self.assertEqual(
            challenge.attempts,
            0
        )

    def test_max_attempts_prevents_verification(self):
        """OTP should not be verified after maximum attempts."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        challenge.attempts = challenge.max_attempts
        challenge.save(
            update_fields=["attempts"]
        )

        result = verify_otp(
            challenge,
            otp
        )

        self.assertFalse(result)

        challenge.refresh_from_db()

        self.assertEqual(
            challenge.attempts,
            challenge.max_attempts
        )

        self.assertIsNone(
            challenge.consumed_at
        )

    def test_failed_attempts_can_continue_until_max_attempts(self):
        """Invalid attempts should be allowed up to max_attempts."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        wrong_otp = (
            "000000"
            if otp != "000000"
            else "111111"
        )

        for expected_attempts in range(
            1,
            challenge.max_attempts + 1
        ):
            result = verify_otp(
                challenge,
                wrong_otp
            )

            self.assertFalse(result)

            challenge.refresh_from_db()

            self.assertEqual(
                challenge.attempts,
                expected_attempts
            )

    def test_wrong_otp_does_not_consume_challenge(self):
        """Invalid OTP must not mark challenge as consumed."""
        challenge, otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        wrong_otp = (
            "000000"
            if otp != "000000"
            else "111111"
        )

        verify_otp(
            challenge,
            wrong_otp
        )

        challenge.refresh_from_db()

        self.assertIsNone(
            challenge.consumed_at
        )
