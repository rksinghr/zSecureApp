from django.shortcuts import redirect
from django.urls import reverse

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.user.is_authenticated and not request.user.profile_completed:
            allowed_paths = {
                reverse("profile"),
                reverse("logout"),
                reverse("verify-login"),
            }
            if request.path not in allowed_paths:
                return redirect("profile")
        return self.get_response(request)
