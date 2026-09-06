import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

class RegistrationViewTests(TestCase):

    def test_register_get_returns_200(self):
        """GET /register/ should display the registration page."""
        response = self.client.get(
            reverse("register")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_register_get_does_not_create_user(self):
        """Viewing registration page should not create a user."""
        self.client.get(
            reverse("register")
        )

        self.assertEqual(
            User.objects.count(),
            0
        )

    def test_register_invalid_email_does_not_create_challenge(self):
        """Invalid email should not create an OTP challenge."""
        response = self.client.post(
            reverse("register"),
            {
                "email": "not-an-email"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            OTPChallenge.objects.count(),
            0
        )

        self.assertEqual(
            len(mail.outbox),
            0
        )

    def test_register_valid_email_creates_otp_challenge(self):
        """Valid email should create a registration OTP challenge."""
        response = self.client.post(
            reverse("register"),
            {
                "email": "user@example.com"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertRedirects(
            response,
            reverse("verify-register")
        )

        self.assertEqual(
            OTPChallenge.objects.count(),
            1
        )

        challenge = OTPChallenge.objects.first()

        self.assertEqual(
            challenge.email,
            "user@example.com"
        )

        self.assertEqual(
            challenge.purpose,
            "REGISTER"
        )

    def test_register_valid_email_sends_otp_email(self):
        """Registration should send an OTP email."""
        self.client.post(
            reverse("register"),
            {
                "email": "user@example.com"
            }
        )

        self.assertEqual(
            len(mail.outbox),
            1
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["user@example.com"]
        )

        self.assertEqual(
            email.subject,
            "Your verification code"
        )

    def test_register_does_not_create_user_before_verification(self):
        """
        Registration should not create the User record until
        the OTP is successfully verified.
        """
        self.client.post(
            reverse("register"),
            {
                "email": "user@example.com"
            }
        )

        self.assertEqual(
            User.objects.count(),
            0
        )

    def test_register_stores_challenge_id_in_session(self):
        """Registration should store the OTP challenge ID in session."""
        self.client.post(
            reverse("register"),
            {
                "email": "user@example.com"
            }
        )

        challenge = OTPChallenge.objects.first()

        self.assertEqual(
            self.client.session.get("otp_challenge"),
            str(challenge.id)
        )

    def test_register_normalizes_email(self):
        """Registration should normalize the email address."""
        self.client.post(
            reverse("register"),
            {
                "email": "  USER@EXAMPLE.COM  "
            }
        )

        challenge = OTPChallenge.objects.first()

        self.assertEqual(
            challenge.email,
            "user@example.com"
        )

class RegistrationVerificationViewTests(TestCase):

    def setUp(self):
        self.challenge, self.otp = create_otp_challenge(
            "user@example.com",
            "REGISTER"
        )

        session = self.client.session

        session["otp_challenge"] = str(
            self.challenge.id
        )

        session.save()

    def test_verify_registration_without_session_redirects_to_register(self):
        """Verification without an OTP session should return to registration."""
        session = self.client.session
        session.pop("otp_challenge", None)
        session.save()

        response = self.client.get(
            reverse("verify-register")
        )

        self.assertRedirects(
            response,
            reverse("register")
        )

    def test_verify_registration_get_returns_200(self):
        """Valid OTP challenge should allow the verification page to load."""
        response = self.client.get(
            reverse("verify-register")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_verify_registration_wrong_otp_is_rejected(self):
        """Incorrect OTP should not create a user."""
        wrong_otp = (
            "000000"
            if self.otp != "000000"
            else "111111"
        )

        response = self.client.post(
            reverse("verify-register"),
            {
                "otp": wrong_otp
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            User.objects.count(),
            0
        )

        self.challenge.refresh_from_db()

        self.assertEqual(
            self.challenge.attempts,
            1
        )

        self.assertIsNone(
            self.challenge.consumed_at
        )

    def test_verify_registration_correct_otp_creates_user(self):
        """
        Correct registration OTP should create the user and
        mark email as verified.
        """
        response = self.client.post(
            reverse("verify-register"),
            {
                "otp": self.otp
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        user = User.objects.get(
            email="user@example.com"
        )

        self.assertTrue(
            user.email_verified
        )

    def test_verify_registration_correct_otp_consumes_challenge(self):
        """Successful registration should consume the OTP."""
        self.client.post(
            reverse("verify-register"),
            {
                "otp": self.otp
            }
        )

        self.challenge.refresh_from_db()

        self.assertIsNotNone(
            self.challenge.consumed_at
        )

    def test_verify_registration_correct_otp_removes_session_challenge(self):
        """Successful verification should remove OTP challenge from session."""
        self.client.post(
            reverse("verify-register"),
            {
                "otp": self.otp
            }
        )

        self.assertNotIn(
            "otp_challenge",
            self.client.session
        )

    def test_verify_registration_cannot_reuse_otp(self):
        """The same registration OTP cannot be used twice."""
        first_response = self.client.post(
            reverse("verify-register"),
            {
                "otp": self.otp
            }
        )

        self.assertEqual(
            first_response.status_code,
            302
        )

        # Restore the challenge ID manually to simulate
        # another attempt using the same challenge.
        session = self.client.session
        session["otp_challenge"] = str(
            self.challenge.id
        )
        session.save()

        second_response = self.client.post(
            reverse("verify-register"),
            {
                "otp": self.otp
            }
        )

        self.assertEqual(
            second_response.status_code,
            200
        )

    def test_expired_registration_otp_is_rejected(self):
        """Expired registration OTP should not create a user."""
        self.challenge.expires_at = (
            timezone.now() - timedelta(seconds=1)
        )

        self.challenge.save(
            update_fields=["expires_at"]
        )

        response = self.client.post(
            reverse("verify-register"),
            {
                "otp": self.otp
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            User.objects.count(),
            0
        )

    def test_missing_challenge_redirects_to_register(self):
        """Non-existent challenge should return to registration."""
        session = self.client.session

        session["otp_challenge"] = str(
            uuid.uuid4()
        )

        session.save()

        response = self.client.get(
            reverse("verify-register")
        )

        self.assertRedirects(
            response,
            reverse("register")
        )

class LoginViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com"
        )

        self.user.email_verified = True
        self.user.save(
            update_fields=["email_verified"]
        )

    def test_login_get_returns_200(self):
        """GET /login/ should display login page."""
        response = self.client.get(
            reverse("login")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_login_invalid_email_does_not_create_challenge(self):
        """Invalid email format should not create an OTP challenge."""
        response = self.client.post(
            reverse("login"),
            {
                "email": "not-an-email"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            OTPChallenge.objects.count(),
            0
        )

    def test_login_nonexistent_user_returns_generic_response(self):
        """
        Non-existent users should receive a generic response
        instead of an account-enumeration response.
        """
        response = self.client.post(
            reverse("login"),
            {
                "email": "doesnotexist@example.com"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            OTPChallenge.objects.count(),
            0
        )

        self.assertEqual(
            len(mail.outbox),
            0
        )

    def test_login_existing_user_creates_challenge(self):
        """Existing active user should receive a login OTP."""
        response = self.client.post(
            reverse("login"),
            {
                "email": "user@example.com"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertRedirects(
            response,
            reverse("verify-login")
        )

        challenge = OTPChallenge.objects.get(
            email="user@example.com",
            purpose="LOGIN"
        )

        self.assertIsNotNone(
            challenge
        )

    def test_login_existing_user_sends_email(self):
        """Existing user should receive login OTP by email."""
        self.client.post(
            reverse("login"),
            {
                "email": "user@example.com"
            }
        )

        self.assertEqual(
            len(mail.outbox),
            1
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["user@example.com"]
        )

        self.assertEqual(
            email.subject,
            "Your login code"
        )

    def test_login_stores_challenge_in_session(self):
        """Login should store OTP challenge ID in session."""
        self.client.post(
            reverse("login"),
            {
                "email": "user@example.com"
            }
        )

        challenge = OTPChallenge.objects.get(
            email="user@example.com",
            purpose="LOGIN"
        )

        self.assertEqual(
            self.client.session.get("otp_challenge"),
            str(challenge.id)
        )

    def test_inactive_user_does_not_receive_login_otp(self):
        """Inactive users should not receive login OTP."""
        self.user.is_active = False
        self.user.save(
            update_fields=["is_active"]
        )

        response = self.client.post(
            reverse("login"),
            {
                "email": "user@example.com"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            OTPChallenge.objects.count(),
            0
        )

        self.assertEqual(
            len(mail.outbox),
            0
        )

class LoginVerificationViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com"
        )

        self.user.email_verified = True
        self.user.profile_completed = True
        self.user.save(
            update_fields=[
                "email_verified",
                "profile_completed",
            ]
        )

        self.challenge, self.otp = create_otp_challenge(
            "user@example.com",
            "LOGIN"
        )

        session = self.client.session

        session["otp_challenge"] = str(
            self.challenge.id
        )

        session.save()

    def test_verify_login_get_returns_200(self):
        """Valid login challenge should display verification page."""
        response = self.client.get(
            reverse("verify-login")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_verify_login_without_session_redirects_to_login(self):
        """Login verification without challenge should return to login."""
        session = self.client.session

        session.pop(
            "otp_challenge",
            None
        )

        session.save()

        response = self.client.get(
            reverse("verify-login")
        )

        self.assertRedirects(
            response,
            reverse("login")
        )

    def test_verify_login_wrong_otp_is_rejected(self):
        """Incorrect login OTP should not authenticate the user."""
        wrong_otp = (
            "000000"
            if self.otp != "000000"
            else "111111"
        )

        response = self.client.post(
            reverse("verify-login"),
            {
                "otp": wrong_otp
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertFalse(
            self.client.session.get("_auth_user_id")
        )

    def test_verify_login_correct_otp_authenticates_user(self):
        """Correct OTP should authenticate the user."""
        response = self.client.post(
            reverse("verify-login"),
            {
                "otp": self.otp
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertEqual(
            str(self.client.session["_auth_user_id"]),
            str(self.user.id)
        )

    def test_verify_login_correct_otp_consumes_challenge(self):
        """Successful login should consume the OTP challenge."""
        self.client.post(
            reverse("verify-login"),
            {
                "otp": self.otp
            }
        )

        self.challenge.refresh_from_db()

        self.assertIsNotNone(
            self.challenge.consumed_at
        )

    def test_verify_login_removes_challenge_from_session(self):
        """Successful login should remove OTP challenge from session."""
        self.client.post(
            reverse("verify-login"),
            {
                "otp": self.otp
            }
        )

        self.assertNotIn(
            "otp_challenge",
            self.client.session
        )

    def test_expired_login_otp_is_rejected(self):
        """Expired login OTP should not authenticate the user."""
        self.challenge.expires_at = (
            timezone.now() - timedelta(seconds=1)
        )

        self.challenge.save(
            update_fields=["expires_at"]
        )

        response = self.client.post(
            reverse("verify-login"),
            {
                "otp": self.otp
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session
        )

    def test_invalid_challenge_redirects_to_login(self):
        """Missing database challenge should return to login."""
        session = self.client.session

        session["otp_challenge"] = str(
            uuid.uuid4()
        )

        session.save()

        response = self.client.get(
            reverse("verify-login")
        )

        self.assertRedirects(
            response,
            reverse("login")
        )

        self.assertNotIn(
            "otp_challenge",
            self.client.session
        )
