from django.shortcuts import get_object_or_404, render

from .models import NFCCard


def public_card_view(request, token):
    card = get_object_or_404(
        NFCCard,
        public_token=token,
        status="ACTIVE",
    )

    profile = card.owner.profile

    return render(
        request,
        "cards/public_card.html",
        {
            "card": card,
            "profile": profile,
        },
    )