import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

class UserManagerTests(TestCase):

    def test_create_user_requires_email(self):
        """create_user should reject a missing email."""
        with self.assertRaisesMessage(
            ValueError,
            "Email address is required"
        ):
            User.objects.create_user(
                email=None
            )

    def test_create_user_creates_passwordless_user(self):
        """Regular users should have an unusable password."""
        user = User.objects.create_user(
            email="user@example.com",
            password="SomePassword123!"
        )

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.has_usable_password() is False)

    def test_create_user_normalizes_email(self):
        """create_user should normalize email to lowercase."""
        user = User.objects.create_user(
            email="  USER@EXAMPLE.COM  "
        )

        self.assertEqual(
            user.email,
            "user@example.com"
        )

    def test_create_user_does_not_use_password(self):
        """
        Password supplied to create_user should not be usable
        because the application is passwordless.
        """
        user = User.objects.create_user(
            email="user@example.com",
            password="SomePassword123!"
        )

        self.assertFalse(
            user.check_password("SomePassword123!")
        )

        self.assertFalse(
            user.has_usable_password()
        )

    def test_create_user_can_accept_extra_fields(self):
        """create_user should accept additional User fields."""
        user = User.objects.create_user(
            email="user@example.com",
            email_verified=True
        )

        self.assertTrue(user.email_verified)

    def test_create_user_defaults_email_verified_to_false(self):
        """New users should not be email verified."""
        user = User.objects.create_user(
            email="user@example.com"
        )

        self.assertFalse(user.email_verified)

    def test_create_user_defaults_profile_completed_to_false(self):
        """New users should not have a completed profile."""
        user = User.objects.create_user(
            email="user@example.com"
        )

        self.assertFalse(user.profile_completed)

    def test_create_superuser_requires_password(self):
        """Superuser creation should require a password."""
        with self.assertRaisesMessage(
            ValueError,
            "Superuser password is required"
        ):
            User.objects.create_superuser(
                email="admin@example.com"
            )

    def test_create_superuser_creates_admin(self):
        """create_superuser should create a staff and superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!"
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_normalizes_email(self):
        """Superuser email should be normalized."""
        user = User.objects.create_superuser(
            email="  ADMIN@EXAMPLE.COM  ",
            password="AdminPassword123!"
        )

        self.assertEqual(
            user.email,
            "admin@example.com"
        )

    def test_create_superuser_password_is_set(self):
        """Superuser should have a usable password."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!"
        )

        self.assertTrue(user.has_usable_password())
        self.assertTrue(
            user.check_password("AdminPassword123!")
        )

    def test_create_superuser_rejects_duplicate_email(self):
        """A duplicate email should not create another superuser."""
        User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!"
        )

        with self.assertRaises(Exception):
            User.objects.create_superuser(
                email="admin@example.com",
                password="AnotherPassword123!"
            )

    def test_create_superuser_allows_extra_fields(self):
        """create_superuser should accept additional User fields."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!",
            email_verified=True,
            profile_completed=True
        )

        self.assertTrue(user.email_verified)
        self.assertTrue(user.profile_completed)
