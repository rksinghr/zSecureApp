from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ProfileForm
from .models import Profile

@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)

    if request.method == "POST" and form.is_valid():
        form.save()
        request.user.profile_completed = True
        request.user.save(
            update_fields=["profile_completed"]
        )
        return redirect("dashboard")
    return render(request, "appProfiles/profile.html", {"form": form})
