"""Resolve the person-first identity shown on business card profiles."""


def _image_url(field):
    if not field:
        return ""
    try:
        if field.storage.exists(field.name):
            return field.url
    except (OSError, ValueError):
        pass
    return ""


def resolve_business_identity(business, owner_profile=None, order=None, representative=None):
    """Return only the identity and contact fields explicitly eligible to be public.

    The existing show_owner_identity setting controls the public summary.
    Owner contact details are never inherited from legacy sharing flags. Multiple
    cards use only the representative assigned to that card; Organization Single
    cards prefer an assigned representative and otherwise use the owner profile.
    """
    if representative and representative.business_id != business.pk:
        representative = None

    if not business.show_owner_identity:
        return None

    is_organization = business.profile_type == "ORGANIZATION"
    order_type = getattr(order, "business_order_type", "") if order else ""
    requires_representative = order_type == "MULTIPLE" or (
        is_organization and order_type not in ("", "SINGLE")
    )
    if representative and representative.name and (is_organization or requires_representative):
        return {
            "kind": "representative", "name": representative.name,
            "designation": representative.designation, "bio": representative.bio,
            "photo_url": _image_url(representative.photo),
            "phone": representative.phone if representative.phone_public else "",
            "email": representative.email if representative.email_public else "",
            "whatsapp": "", "website": "", "address": "",
            "facebook": "", "instagram": "", "linkedin": "", "github": "",
        }

    if requires_representative:
        return None
    if owner_profile and owner_profile.full_name:
        return {
            "kind": "owner", "name": owner_profile.full_name,
            "designation": owner_profile.job_title, "bio": owner_profile.bio,
            "photo_url": _image_url(owner_profile.profile_picture),
            # The business-level option controls the compact public summary.
            # Full owner details are exposed only by the authorized person route.
            "phone": "", "email": "", "whatsapp": "", "website": "",
            "address": "", "facebook": "", "instagram": "",
            "linkedin": "", "github": "",
        }
    return None


def business_identity_message(business, order=None):
    order_type = getattr(order, "business_order_type", "") if order else ""
    if not business.show_owner_identity:
        return "Personal or representative information is hidden by your profile visibility setting."
    if order_type == "MULTIPLE" or (
        business.profile_type == "ORGANIZATION" and order_type not in ("", "SINGLE")
    ):
        return "Assign a representative to this card to include their details in the preview."
    if business.profile_type == "ORGANIZATION":
        return "Add your full name to your Personal Profile or assign a representative for this card."
    return "Add your full name to your Personal Profile to complete this business card."
