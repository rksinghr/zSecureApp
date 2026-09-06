# send_email.py
from django.core.mail import send_mail

def send_registration_otp(email, otp):
    send_mail(
        subject="Your verification code",
        message=f"Your verification code is {otp}.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
