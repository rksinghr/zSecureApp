import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

from .models import User, OTPChallenge

class UserModelTests(TestCase):

    def test_user_can_be_created_with_email(self):
        """A user should be created successfully using email."""
        user = User.objects.create_user(
            email="TestUser@Example.COM",
            password="StrongPassword123!"
        )

        self.assertIsNotNone(user.id)
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, "testuser@example.com")
        self.assertFalse(user.email_verified)
        self.assertFalse(user.profile_completed)

    def test_user_id_is_uuid(self):
        """User primary key should be a UUID."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        self.assertIsInstance(user.id, uuid.UUID)

    def test_email_is_normalized_to_lowercase(self):
        """Email should be converted to lowercase when saved."""
        user = User.objects.create_user(
            email="USER@EXAMPLE.COM",
            password="StrongPassword123!"
        )

        self.assertEqual(user.email, "user@example.com")

    def test_email_is_stripped_of_whitespace(self):
        """Leading/trailing whitespace should be removed from email."""
        user = User.objects.create_user(
            email="  user@example.com  ",
            password="StrongPassword123!"
        )

        self.assertEqual(user.email, "user@example.com")

    def test_email_is_unique(self):
        """Two users should not be able to use the same email."""
        User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        with self.assertRaises(Exception):
            User.objects.create_user(
                email="user@example.com",
                password="AnotherPassword123!"
            )

    def test_email_verified_defaults_to_false(self):
        """New users should not be email verified by default."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        self.assertFalse(user.email_verified)

    def test_profile_completed_defaults_to_false(self):
        """New users should not have a completed profile by default."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        self.assertFalse(user.profile_completed)

    def test_created_at_is_set(self):
        """created_at should be automatically populated."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        self.assertIsNotNone(user.created_at)

    def test_updated_at_is_set(self):
        """updated_at should be automatically populated."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        self.assertIsNotNone(user.updated_at)

    def test_updated_at_changes_when_user_is_updated(self):
        """updated_at should change when the user is saved."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        original_updated_at = user.updated_at

        user.email_verified = True
        user.save()

        user.refresh_from_db()

        self.assertGreaterEqual(
            user.updated_at,
            original_updated_at
        )

    def test_user_string_representation(self):
        """__str__ should return the user's email."""
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!"
        )

        self.assertEqual(str(user), "user@example.com")
