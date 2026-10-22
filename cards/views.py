import hashlib
import io
from datetime import timedelta

import qrcode
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .contact import build_vcard
from .forms import CardInquiryForm
from .models import CardInquiry, CardVisit, NFCCard
from .presentation import business_identity_message, resolve_business_identity
from profiles.forms import normalize_web_url
from profiles.models import FeaturedOffering
from profiles.presentation import add_safe_offering_links


def _visible_card(token):
    card = get_object_or_404(
        NFCCard.objects.select_related(
            "owner__profile", "business_profile", "representative",
            "allocation__order", "allocation__representative", "assigned_order",
        ),
        public_token=token, status="ACTIVE",
    )
    if not card.owner or (not card.business_profile and not hasattr(card.owner, "profile")):
        raise Http404("Profile not found.")
    return card


def _visitor_hash(request):
    source = f"{request.META.get('REMOTE_ADDR', '')}|{request.META.get('HTTP_USER_AGENT', '')}"
    return hashlib.sha256(f"{settings.SECRET_KEY}|{source}".encode()).hexdigest()


def public_card_view(request, token):
    card = _visible_card(token)
    form = None
    if card.business_profile:
        form = CardInquiryForm(request.POST or None)
        if request.method == "POST":
            recent = CardInquiry.objects.filter(
                card=card, source_hash=_visitor_hash(request),
                created_at__gte=timezone.now() - timedelta(hours=1),
            ).count()
            if recent >= 3:
                form.add_error(None, "Please try again later.")
            elif form.is_valid():
                inquiry = form.save(commit=False)
                inquiry.card = card
                inquiry.source_hash = _visitor_hash(request)
                inquiry.save()
                return redirect(f"{request.path}?sent=1")
    if request.method == "GET":
        CardVisit.objects.create(card=card, visitor_hash=_visitor_hash(request))
    business = card.business_profile
    identity = None
    identity_message = ""
    website_url = ""
    logo_url = ""
    banner_url = ""
    social_links = {}
    featured_offerings = FeaturedOffering.objects.none()
    if business:
        allocation = getattr(card, "allocation", None)
        order = allocation.order if allocation else getattr(card, "assigned_order", None)
        representative = (allocation.representative if allocation and allocation.representative_id
                          else card.representative)
        identity = resolve_business_identity(business, getattr(card.owner, "profile", None), order, representative)
        identity_message = business_identity_message(business, order) if identity is None else ""
        for field, value in (("website", business.website), ("facebook", business.facebook),
                             ("instagram", business.instagram), ("linkedin", business.linkedin)):
            try:
                normalized = normalize_web_url(value)
            except (ValidationError, ValueError):
                normalized = ""
            if normalized:
                if field == "website":
                    website_url = normalized
                else:
                    social_links[field] = normalized
        if business.logo:
            try:
                if business.logo.storage.exists(business.logo.name):
                    logo_url = business.logo.url
            except (OSError, ValueError):
                pass
        if business.profile_type == "ORGANIZATION" and business.banner:
            try:
                if business.banner.storage.exists(business.banner.name):
                    banner_url = business.banner.url
            except (OSError, ValueError):
                pass
        featured_offerings = FeaturedOffering.objects.filter(business=business).order_by("position", "id")
        featured_offerings = add_safe_offering_links(featured_offerings)
    return render(request, "cards/public_card.html", {
        "card": card, "profile": getattr(card.owner, "profile", None),
        "business": business, "representative": card.representative,
        "business_identity": identity, "identity_message": identity_message,
        "website_url": website_url, "business_logo_url": logo_url,
        "business_banner_url": banner_url, "business_social_links": social_links,
        "featured_offerings": featured_offerings,
        "inquiry_form": form, "inquiry_sent": request.GET.get("sent") == "1",
    })


def card_qr_view(request, token):
    card = _visible_card(token)
    qr = qrcode.make(card.public_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


def offline_contact_qr(request, token):
    card = _visible_card(token)
    qr = qrcode.make(build_vcard(card, offline=True), error_correction=qrcode.constants.ERROR_CORRECT_M)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


def download_vcard(request, token):
    card = _visible_card(token)
    name = card.business_profile.name if card.business_profile else card.owner.profile.public_name
    response = HttpResponse(build_vcard(card), content_type="text/vcard; charset=utf-8")
    safe_name = "".join(character for character in name if character.isalnum() or character in " -_").strip().replace(" ", "_")[:60] or "NexTap_Contact"
    response["Content-Disposition"] = f'attachment; filename="{safe_name}.vcf"'
    return response
