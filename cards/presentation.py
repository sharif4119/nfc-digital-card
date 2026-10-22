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

    Organization and multiple-card identities always come from that card's
    representative. Small-business single cards may use the owner's profile,
    but only when the owner has opted in to that identity.
    """
    if representative and representative.business_id != business.pk:
        representative = None

    is_organization = business.profile_type == "ORGANIZATION"
    order_type = getattr(order, "business_order_type", "") if order else ""
    requires_representative = is_organization or order_type == "MULTIPLE"
    if not requires_representative:
        if business.show_owner_identity and owner_profile and owner_profile.full_name:
            return {
                "kind": "owner", "name": owner_profile.full_name,
                "designation": owner_profile.job_title, "bio": owner_profile.bio,
                "photo_url": _image_url(owner_profile.profile_picture),
                "phone": owner_profile.phone if business.share_owner_phone else "",
                "email": owner_profile.email if business.share_owner_email else "",
                "whatsapp": owner_profile.whatsapp if business.share_owner_whatsapp else "",
                "website": owner_profile.website if business.share_owner_website else "",
                "address": owner_profile.address if business.share_owner_address else "",
                "facebook": owner_profile.facebook if business.share_owner_social else "",
                "instagram": owner_profile.instagram if business.share_owner_social else "",
                "linkedin": owner_profile.linkedin if business.share_owner_social else "",
                "github": owner_profile.github if business.share_owner_social else "",
            }
        return None

    if representative and representative.name:
        return {
            "kind": "representative", "name": representative.name,
            "designation": representative.designation, "bio": representative.bio,
            "photo_url": _image_url(representative.photo),
            "phone": representative.phone if representative.phone_public else "",
            "email": representative.email if representative.email_public else "",
            "whatsapp": "", "website": "", "address": "",
            "facebook": "", "instagram": "", "linkedin": "", "github": "",
        }
    return None


def business_identity_message(business, order=None):
    order_type = getattr(order, "business_order_type", "") if order else ""
    if business.profile_type == "ORGANIZATION" or order_type == "MULTIPLE":
        return "Representative details will appear after a person is assigned to this card."
    if not business.show_owner_identity:
        return "To show your identity on Business Single cards, enable owner identity in Business Profile settings."
    return "Add your full name to your Personal Profile to complete this business card."
