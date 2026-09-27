from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render

from .forms import (
    EmailOrUsernameAuthenticationForm,
    RegisterForm,
)


class NexTapLoginView(LoginView):
    authentication_form = EmailOrUsernameAuthenticationForm
    template_name = "registration/login.html"


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
            except IntegrityError:
                form.add_error(
                    "email",
                    "An account with this email already exists.",
                )
            else:
                login(request, user)
                return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


@login_required
def dashboard_view(request):
    card = getattr(
        request.user,
        "nfc_card",
        None,
    )

    profile = getattr(
        request.user,
        "profile",
        None,
    )

    recent_orders = request.user.orders.order_by(
        "-created_at"
    )[:3]

    return render(
        request,
        "accounts/dashboard.html",
        {
            "card": card,
            "profile": profile,
            "recent_orders": recent_orders,
        },
    )
