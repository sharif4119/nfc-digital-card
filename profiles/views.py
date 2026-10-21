from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm
from .models import Profile
from .models import BusinessProfile
from .forms import BusinessProfileForm, FeaturedOfferingFormSet, RepresentativeForm
from orders.models import CardAllocation
from cards.models import CardInquiry, CardVisit
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


@login_required
def business_edit(request):
    business = BusinessProfile.objects.filter(owner=request.user).first()
    if request.method == "POST":
        form = BusinessProfileForm(request.POST, request.FILES, instance=business)
        # A temporary unsaved instance lets a new business use the same formset.
        instance = business or BusinessProfile(owner=request.user)
        offerings = FeaturedOfferingFormSet(request.POST, request.FILES, instance=instance, prefix="offerings")
        if form.is_valid() and offerings.is_valid():
            with transaction.atomic():
                business = form.save(commit=False)
                business.owner = request.user
                business.save()
                offerings.instance = business
                offerings.save()
            return redirect("business_cards")
    else:
        form = BusinessProfileForm(instance=business)
        offerings = FeaturedOfferingFormSet(instance=business or BusinessProfile(owner=request.user), prefix="offerings")
    return render(request, "profiles/business_edit.html", {"form": form, "offerings": offerings, "business": business})


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
        form = RepresentativeForm(request.POST, instance=allocation.representative)
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

    return render(
        request,
        "profiles/profile_preview.html",
        {
            "profile": profile,
        },
    )
