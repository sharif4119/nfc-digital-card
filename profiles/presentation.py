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
