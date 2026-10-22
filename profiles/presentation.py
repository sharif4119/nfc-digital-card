"""Small presentation helpers shared by private and public business profiles."""

from django.core.exceptions import ValidationError

from .forms import normalize_web_url


def add_safe_offering_links(offerings):
    """Attach a normalized, safe URL for templates without mutating database rows."""
    for offering in offerings:
        try:
            offering.safe_external_url = normalize_web_url(offering.external_url)
        except (ValidationError, ValueError):
            offering.safe_external_url = ""
    return offerings


def personal_profile_presentation(profile):
    """Return safe link targets and an available stored photo URL for a profile."""
    social_links = {}
    for field in ("facebook", "instagram", "linkedin", "github"):
        try:
            url = normalize_web_url(getattr(profile, field))
        except (ValidationError, ValueError):
            url = ""
        if url:
            social_links[field] = url

    try:
        website_url = normalize_web_url(profile.website)
    except (ValidationError, ValueError):
        website_url = ""

    picture_url = ""
    if profile.profile_picture:
        try:
            if profile.profile_picture.storage.exists(profile.profile_picture.name):
                picture_url = profile.profile_picture.url
        except (OSError, ValueError):
            pass

    allowed_phone_characters = set("+()- .0123456789")

    def normalized_number(raw_value):
        raw_value = raw_value.strip()
        if not raw_value or not set(raw_value).issubset(allowed_phone_characters):
            return "", False
        compact = "".join(character for character in raw_value if character not in " -().")
        has_plus = compact.startswith("+")
        digits = compact[1:] if has_plus else compact
        if not digits.isascii() or not digits.isdigit() or not 10 <= len(digits) <= 15:
            return "", False
        return digits, has_plus

    digits, _ = normalized_number(profile.whatsapp)
    whatsapp_number = ""
    if digits:
        # Bangladesh local mobiles are stored in several legacy formats.
        # Convert 01XXXXXXXXX to the international 8801XXXXXXXXX form.
        whatsapp_number = f"880{digits[1:]}" if len(digits) == 11 and digits.startswith("01") else digits

    phone_url, has_plus = normalized_number(profile.phone)
    if phone_url and has_plus:
        phone_url = "+" + phone_url

    return {
        "profile_picture_url": picture_url,
        "website_url": website_url,
        "social_links": social_links,
        "whatsapp_number": whatsapp_number,
        "phone_url": phone_url,
    }
