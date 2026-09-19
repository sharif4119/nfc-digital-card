import io

import qrcode
from django.http import HttpResponse
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


def card_qr_view(request, token):
    card = get_object_or_404(
        NFCCard,
        public_token=token,
        status="ACTIVE",
    )

    public_url = request.build_absolute_uri(
        f"/c/{card.public_token}/"
    )

    qr = qrcode.make(public_url)

    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

    return response


def download_vcard(request, token):
    card = get_object_or_404(
        NFCCard,
        public_token=token,
        status="ACTIVE",
    )

    profile = card.owner.profile

    vcard = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{profile.full_name}",
    ]

    if profile.company:
        vcard.append(f"ORG:{profile.company}")

    if profile.job_title:
        vcard.append(f"TITLE:{profile.job_title}")

    if profile.phone:
        vcard.append(f"TEL:{profile.phone}")

    if profile.email:
        vcard.append(f"EMAIL:{profile.email}")

    if profile.website:
        vcard.append(f"URL:{profile.website}")

    if profile.address:
        vcard.append(f"ADR:;;{profile.address};;;;")

    vcard.append("END:VCARD")

    response = HttpResponse(
        "\r\n".join(vcard),
        content_type="text/vcard",
    )

    filename = (
        profile.full_name.replace(" ", "_")
        if profile.full_name
        else card.owner.username
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="{filename}.vcf"'

    return response