from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, add_field_error_styles, normalize_web_url
from .models import Profile
from .models import BusinessProfile, FeaturedOffering
from .forms import BusinessProfileForm, FeaturedOfferingFormSet, RepresentativeForm
from .presentation import add_safe_offering_links
from orders.models import CardAllocation
from cards.models import CardInquiry, CardVisit
from cards.presentation import business_identity_message, resolve_business_identity
from django.db import transaction
from django.db.models import Count
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import datetime, time, timedelta


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
            messages.success(request, "Your personal profile was saved.")
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
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(
        request,
        "profiles/profile_preview.html",
        {"profile": profile},
    )


@login_required
def business_edit(request):
    business = BusinessProfile.objects.filter(owner=request.user).first()
    has_validation_errors = False
    if request.method == "POST":
        form = BusinessProfileForm(request.POST, request.FILES, instance=business)
        # A temporary unsaved instance lets a new business use the same formset.
        instance = business or BusinessProfile(owner=request.user)
        form_kwargs = {
            "profile_type": form.profile_type,
            "organization_category": form.organization_category,
        }
        offerings = FeaturedOfferingFormSet(
            request.POST, request.FILES, instance=instance, prefix="offerings",
            form_kwargs=form_kwargs,
        )
        form_is_valid = form.is_valid()
        offerings_are_valid = offerings.is_valid()
        for offering_form in offerings.forms:
            add_field_error_styles(offering_form)
        has_validation_errors = not (form_is_valid and offerings_are_valid)
        if form_is_valid and offerings_are_valid:
            with transaction.atomic():
                business = form.save(commit=False)
                business.owner = request.user
                business.save()
                offerings.instance = business
                offerings.save()
            profile_term = "Organization" if business.profile_type == "ORGANIZATION" else "Business"
            messages.success(request, f"Your {profile_term.lower()} profile was saved.")
            if request.POST.get("action") == "preview":
                return redirect("business_profile_preview")
            return redirect("business_cards")
    else:
        form = BusinessProfileForm(instance=business)
        offerings = FeaturedOfferingFormSet(
            instance=business or BusinessProfile(owner=request.user), prefix="offerings",
            form_kwargs={
                "profile_type": form.profile_type,
                "organization_category": form.organization_category,
            },
        )
    is_organization = form.profile_type == "ORGANIZATION"
    return render(request, "profiles/business_edit.html", {
        "form": form, "offerings": offerings, "business": business,
        "has_validation_errors": has_validation_errors,
        "is_organization": is_organization,
        "profile_term": "Organization" if is_organization else "Business",
        "organization_category": form.organization_category,
    })


@login_required
def business_profile_preview(request):
    business = BusinessProfile.objects.filter(owner=request.user).first()
    logo_url = ""
    banner_url = ""
    website_url = ""
    for field_name in ("logo", "banner"):
        if field_name == "banner" and business and business.profile_type != "ORGANIZATION":
            continue
        field = getattr(business, field_name, None) if business else None
        if field:
            try:
                if field.storage.exists(field.name):
                    if field_name == "logo":
                        logo_url = field.url
                    else:
                        banner_url = field.url
            except (OSError, ValueError):
                pass
    if business and business.website:
        try:
            website_url = normalize_web_url(business.website)
        except (ValidationError, ValueError):
            # Old/admin-entered values should never become active unsafe links.
            website_url = ""
    allocations = list(CardAllocation.objects.filter(
        order__user=request.user, order__business_profile=business,
    ).select_related("card", "representative", "order").order_by("order__created_at", "position")) if business else []
    selected_allocation = None
    requested_allocation = request.GET.get("allocation")
    if requested_allocation and requested_allocation != "owner":
        selected_allocation = next((row for row in allocations if str(row.pk) == requested_allocation), None)
        if selected_allocation is None:
            from django.http import Http404
            raise Http404("Card allocation not found.")
    elif requested_allocation != "owner" and business:
        if business.profile_type == "ORGANIZATION" or any(row.order.business_order_type == "MULTIPLE" for row in allocations):
            selected_allocation = next((row for row in allocations if row.order.business_order_type == "MULTIPLE"), None)
            if selected_allocation is None and business.profile_type == "ORGANIZATION":
                selected_allocation = allocations[0] if allocations else None
    selected_order = selected_allocation.order if selected_allocation else None
    selected_card = selected_allocation.card if selected_allocation else None
    selected_representative = selected_allocation.representative if selected_allocation else None
    owner_profile = getattr(request.user, "profile", None)
    business_identity = resolve_business_identity(business, owner_profile, selected_order, selected_representative) if business else None
    identity_message = business_identity_message(business, selected_order) if business and business_identity is None else ""
    # Keep preview content explicitly tied to saved FeaturedOffering rows;
    # the edit view's "offerings" value is a formset, not preview data.
    featured_offerings = (
        FeaturedOffering.objects.filter(business_id=business.pk).order_by("position", "id")
        if business else FeaturedOffering.objects.none()
    )
    featured_offerings = add_safe_offering_links(featured_offerings)
    safe_social_links = {}
    if business:
        for field in ("facebook", "instagram", "linkedin"):
            try:
                url = normalize_web_url(getattr(business, field))
            except (ValidationError, ValueError):
                url = ""
            if url:
                safe_social_links[field] = url
    return render(request, "profiles/business_preview.html", {
        "business": business,
        "is_organization": bool(business and business.profile_type == "ORGANIZATION"),
        "profile_term": "Organization" if business and business.profile_type == "ORGANIZATION" else "Business",
        "logo_available": bool(logo_url), "logo_url": logo_url,
        "banner_url": banner_url, "business_logo_url": logo_url,
        "business_banner_url": banner_url,
        "website_url": website_url,
        "featured_offerings": featured_offerings,
        "business_identity": business_identity, "identity_message": identity_message,
        "allocations": allocations, "selected_allocation": selected_allocation,
        "selected_card": selected_card,
        "business_social_links": safe_social_links,
        "owner_preview_allowed": bool(business and business.profile_type == "SMALL_BUSINESS" and not any(row.order.business_order_type == "MULTIPLE" for row in allocations)),
    })


@login_required
def business_cards(request):
    business = BusinessProfile.objects.filter(owner=request.user).first()
    if business is None:
        return redirect("business_edit")
    start_date = parse_date(request.GET.get("from", ""))
    end_date = parse_date(request.GET.get("to", ""))
    visits = CardVisit.objects.filter(card__business_profile=business)
    inquiries = CardInquiry.objects.filter(card__business_profile=business)
    if start_date:
        start = timezone.make_aware(datetime.combine(start_date, time.min))
        visits = visits.filter(visited_at__gte=start)
        inquiries = inquiries.filter(created_at__gte=start)
    if end_date:
        end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min))
        visits = visits.filter(visited_at__lt=end)
        inquiries = inquiries.filter(created_at__lt=end)
    cards = list(business.cards.select_related("representative").order_by("id"))
    counts = {row["card_id"]: row for row in visits.values("card_id").annotate(total=Count("id"), unique=Count("visitor_hash", distinct=True))}
    inquiry_counts = dict(inquiries.values("card_id").annotate(total=Count("id")).values_list("card_id", "total"))
    card_rows = [{"card": card, "visits": counts.get(card.id, {}).get("total", 0), "unique": counts.get(card.id, {}).get("unique", 0), "inquiries": inquiry_counts.get(card.id, 0)} for card in cards]
    allocations = CardAllocation.objects.filter(order__user=request.user, order__business_profile=business).select_related("card", "representative", "order")
    return render(request, "profiles/business_cards.html", {
        "business": business, "card_rows": card_rows, "allocations": allocations,
        "is_organization": business.profile_type == "ORGANIZATION",
        "profile_term": "Organization" if business.profile_type == "ORGANIZATION" else "Business",
        "total_visits": visits.count(), "unique_visitors": visits.values("visitor_hash").distinct().count(),
        "inquiry_count": inquiries.count(), "inquiries": inquiries.select_related("card")[:50],
        "start_date": start_date, "end_date": end_date,
    })


@login_required
def representative_edit(request, allocation_id):
    allocation = get_object_or_404(
        CardAllocation.objects.select_related("order", "representative", "card"),
        pk=allocation_id, order__user=request.user,
        order__business_profile__owner=request.user,
    )
    if request.method == "POST":
        form = RepresentativeForm(request.POST, request.FILES, instance=allocation.representative)
        if form.is_valid():
            with transaction.atomic():
                representative = form.save(commit=False)
                representative.business = allocation.order.business_profile
                representative.save()
                allocation.representative = representative
                allocation.save(update_fields=["representative"])
                if allocation.card_id:
                    allocation.card.representative = representative
                    allocation.card.save(update_fields=["representative"])
            return redirect("business_cards")
    else:
        form = RepresentativeForm(instance=allocation.representative)
    return render(request, "profiles/representative_edit.html", {"form": form, "allocation": allocation})
