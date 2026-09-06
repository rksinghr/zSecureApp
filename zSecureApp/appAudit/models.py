from django.db import models

class SecurityAuditEvent(models.Model):

    EVENT_TYPES = (
        ("LOGIN_SUCCESS", "Login success"),
        ("LOGIN_FAILURE", "Login failure"),
        ("OTP_REQUEST", "OTP request"),
        ("PROFILE_UPDATE", "Profile update"),
        ("NOTE_CREATE", "Note create"),
        ("NOTE_UPDATE", "Note update"),
        ("LOGOUT", "Logout"),
    )

    user_id = models.UUIDField(null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)