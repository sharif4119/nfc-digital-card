from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm
from .models import Profile


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
    )

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():
            form.save()
            return redirect("profile_preview")

    else:
        form = ProfileForm(
            instance=profile,
        )

    return render(
        request,
        "profiles/edit_profile.html",
        {
            "form": form,
        },
    )


@login_required
def profile_preview(request):
    profile = get_object_or_404(
        Profile,
        user=request.user,
    )

    return render(
        request,
        "profiles/profile_preview.html",
        {
            "profile": profile,
        },
    )