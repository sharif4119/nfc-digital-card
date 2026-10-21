from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render

from .forms import (
    EmailOrUsernameAuthenticationForm,
    RegisterForm,
)
from cards.models import CardVisit, CardInquiry
from django.db.models import Count


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
    cards = request.user.nfc_cards.order_by("-created_at")
    card = cards.filter(status="ACTIVE").first() or cards.first()

    profile = getattr(
        request.user,
        "profile",
        None,
    )

    recent_orders = request.user.orders.order_by(
        "-created_at"
    )[:3]
    visit_summary = CardVisit.objects.filter(card__owner=request.user).aggregate(
        total=Count("id"), estimated_unique=Count("visitor_hash", distinct=True)
    )

    return render(
        request,
        "accounts/dashboard.html",
        {
            "card": card,
            "profile": profile,
            "recent_orders": recent_orders,
            "cards": cards,
            "business_profile": getattr(request.user, "business_profile", None),
            "visit_summary": visit_summary,
            "inquiry_count": CardInquiry.objects.filter(card__owner=request.user).count(),
        },
    )
