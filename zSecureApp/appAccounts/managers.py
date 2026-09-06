# managers.py
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)

        # Passwordless account
        user.set_unusable_password()
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        user = self.model(
            email=self.normalize_email(email).lower(),
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            raise ValueError("Superuser password is required")

        user.save(using=self._db)

        return user