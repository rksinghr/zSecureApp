# views.py
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .forms import EmailForm, OTPForm
from .models import User, OTPChallenge
from .services.send_email import send_registration_otp
from .services.otp import create_otp_challenge, verify_otp

from .services.rate_limit import (
    check_otp_request_allowed
    , get_client_ip
    , OTPRateLimitExceeded
    )

@require_http_methods(["GET", "POST"])
def register(request):
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower() # Don't create account yet.
        ip_address = get_client_ip(request)

        try: check_otp_request_allowed( email=email, ip_address=ip_address, purpose="REGISTER")
        # Do not reveal which specific limit was exceeded. 
        # The response should remain generic to prevent 
        # attackers from learning information about the rate-limit implementation. 
        except OTPRateLimitExceeded: 
            return render( request, "appAccounts/otp_sent.html", )

        challenge, otp = create_otp_challenge(email, "REGISTER")
        send_registration_otp(email, otp)
        request.session["otp_challenge"] = str(challenge.id)
        return redirect("verify-register")
    return render(request, "appAccounts/register.html", {"form": form},)

@require_http_methods(["GET", "POST"])
def verify_registration(request):
    challenge_id = request.session.get("otp_challenge")
    if not challenge_id:
        return redirect("register")
    try:
        challenge = OTPChallenge.objects.get(id=challenge_id, purpose="REGISTER")
    except OTPChallenge.DoesNotExist:
        return redirect("register")
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if verify_otp(challenge, form.cleaned_data["otp"]):
            user, created = User.objects.get_or_create(
                email=challenge.email,
                defaults={
                    "email_verified": True
                }
            )

            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=["email_verified"])

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.pop("otp_challenge", None)
            return redirect("profile")
        form.add_error("otp", "Invalid or expired verification code.")

    return render(request, "appAccounts/verify.html", {"form": form},)

@require_http_methods(["GET", "POST"])
def login_request(request):
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        try:
            user = User.objects.get(email=email, is_active=True, email_verified=True)

        except User.DoesNotExist:
            # Generic response prevents account enumeration.
            return render(request, "appAccounts/otp_sent.html",)

        ip_address = get_client_ip(request)

        try:
            check_otp_request_allowed(
                email=email,
                ip_address=ip_address,
                purpose="LOGIN",
            )

        except OTPRateLimitExceeded:
            # Generic response.
            return render(request, "appAccounts/otp_sent.html")

        challenge, otp = create_otp_challenge(email, "LOGIN")

        send_mail(
            subject="Your login code",
            message=f"Your login code is {otp}.",
            from_email=None,
            recipient_list=[email],
        )

        request.session["otp_challenge"] = str(challenge.id)

        return redirect("verify-login")

    return render(request, "appAccounts/login.html", {"form": form})

@require_http_methods(["GET", "POST"])
def verify_login(request):
    challenge_id = request.session.get("otp_challenge")
    if not challenge_id:
        return redirect("login")
    try:
        challenge = OTPChallenge.objects.get(
            id=challenge_id,
            purpose="LOGIN",
        )
    except OTPChallenge.DoesNotExist:
        request.session.pop("otp_challenge", None)
        return redirect("login")
    form = OTPForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            otp = form.cleaned_data["otp"]
            if verify_otp(challenge, otp):
                try:
                    user = User.objects.get(email=challenge.email, is_active=True, email_verified=True)
                except User.DoesNotExist:
                    request.session.pop("otp_challenge", None)
                    return redirect("login")
                # Authenticate the user
                login(request, user, backend="django.contrib.auth.backends.ModelBackend",)
                # Remove OTP challenge from session
                request.session.pop("otp_challenge", None)
                # IMPORTANT
                if not user.profile_completed:
                    return redirect("profile")
                return redirect("dashboard")
            form.add_error("otp", "Invalid or expired verification code.")
    return render(request, "appAccounts/verify.html", {"form": form},)

def logout_view(request):
    logout(request)
    return redirect("login")

# Check if the user is allowed to request another OTP
# also where to place it??
# if not allow_request(
#     "otp_email",
#     email,
#     limit=5,
#     period=900,
# ):
#     return render(request, "appAccounts/otp_sent.html")

