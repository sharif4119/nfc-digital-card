"""vCard 3.0 used by downloads, offline QR and print artwork."""

from .presentation import resolve_business_identity


def escape(value):
    return (str(value or "").replace("\\", "\\\\").replace("\r\n", "\n")
            .replace("\r", "\n").replace("\n", "\\n")
            .replace(";", "\\;").replace(",", "\\,"))


def _fold(line):
    pieces = []
    current = ""
    for character in line:
        if len((current + character).encode("utf-8")) > 75:
            pieces.append(current)
            current = " " + character
        else:
            current += character
    pieces.append(current)
    return "\r\n".join(pieces)


def _personal_vcard_lines(profile, *, offline=False):
    lines = ["N:;" + escape(profile.public_name) + ";;;", "FN:" + escape(profile.public_name)]
    if profile.company and not offline:
        lines.append("ORG:" + escape(profile.company))
    if profile.job_title and not offline:
        lines.append("TITLE:" + escape(profile.job_title))
    if profile.phone:
        lines.append("TEL:" + escape(profile.phone))
    if profile.whatsapp:
        lines.append("TEL;TYPE=CELL:" + escape(profile.whatsapp))
    if profile.email:
        lines.append("EMAIL:" + escape(profile.email))
    if profile.website and not offline:
        lines.append("URL:" + escape(profile.website))
    if profile.bio:
        lines.append("NOTE:" + escape(profile.bio[:120] if offline else profile.bio))
    if profile.address and not offline:
        lines.append("ADR:;;" + escape(profile.address) + ";;;;")
    if not offline:
        for social_name in ("facebook", "instagram", "linkedin", "github"):
            value = getattr(profile, social_name, "")
            if value:
                lines.append("X-SOCIALPROFILE;TYPE=" + social_name.upper() + ":" + escape(value))
    return lines


def build_profile_vcard(profile, *, profile_url=""):
    """Build a personal contact vCard for an authenticated owner preview."""
    lines = ["BEGIN:VCARD", "VERSION:3.0", *_personal_vcard_lines(profile)]
    if profile_url:
        lines.append("URL:" + escape(profile_url))
    lines.append("END:VCARD")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def build_public_identity_vcard(identity, *, profile_url=""):
    """Build a contact only from fields already permitted by business privacy rules."""
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        "N:;" + escape(identity.get("name")) + ";;;",
        "FN:" + escape(identity.get("name")),
    ]
    if identity.get("designation"):
        lines.append("TITLE:" + escape(identity["designation"]))
    if identity.get("bio"):
        lines.append("NOTE:" + escape(identity["bio"]))
    if identity.get("phone"):
        lines.append("TEL:" + escape(identity["phone"]))
    if identity.get("email"):
        lines.append("EMAIL:" + escape(identity["email"]))
    if identity.get("whatsapp"):
        lines.append("TEL;TYPE=CELL:" + escape(identity["whatsapp"]))
    if identity.get("website"):
        lines.append("URL:" + escape(identity["website"]))
    if identity.get("address"):
        lines.append("ADR:;;" + escape(identity["address"]) + ";;;;")
    for social_name in ("facebook", "instagram", "linkedin", "github"):
        if identity.get(social_name):
            lines.append(
                "X-SOCIALPROFILE;TYPE=" + social_name.upper() + ":" + escape(identity[social_name])
            )
    if profile_url:
        lines.append("URL:" + escape(profile_url))
    lines.append("END:VCARD")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def build_vcard(card, *, offline=False):
    business = card.business_profile
    representative = card.representative
    lines = ["BEGIN:VCARD", "VERSION:3.0"]
    if business:
        allocation = getattr(card, "allocation", None)
        order = allocation.order if allocation else getattr(card, "assigned_order", None)
        representative = (allocation.representative if allocation and allocation.representative_id
                          else representative)
        identity = resolve_business_identity(
            business, getattr(card.owner, "profile", None), order, representative
        )
        contact_name = identity["name"] if identity else business.name
        lines.append("N:;" + escape(contact_name) + ";;;")
        lines.append("FN:" + escape(contact_name))
        lines.append("ORG:" + escape(business.name))
        if identity and identity["designation"]:
            lines.append("TITLE:" + escape(identity["designation"]))
        if identity and identity["bio"] and not offline:
            lines.append("NOTE:" + escape(identity["bio"][:120] if offline else identity["bio"]))
        public_contact_values = set()

        def add_public_contact(prefix, value):
            if value and value.strip() not in public_contact_values:
                public_contact_values.add(value.strip())
                lines.append(prefix + escape(value.strip()))

        if identity and identity["phone"]:
            add_public_contact("TEL;TYPE=WORK:", identity["phone"])
        if identity and identity["email"]:
            add_public_contact("EMAIL;TYPE=WORK:", identity["email"])
        if identity and identity["whatsapp"]:
            add_public_contact("TEL;TYPE=CELL:", identity["whatsapp"])
        if business.whatsapp:
            add_public_contact("TEL;TYPE=WORK:", business.whatsapp)
        if business.phone:
            add_public_contact("TEL;TYPE=WORK:", business.phone)
        if business.email:
            add_public_contact("EMAIL;TYPE=WORK:", business.email)
        if business.website:
            add_public_contact("URL:", business.website)
        if identity and identity["website"] and identity["website"] != business.website:
            add_public_contact("URL;TYPE=HOME:", identity["website"])
        if identity:
            for social_name in ("facebook", "instagram", "linkedin", "github"):
                if identity[social_name]:
                    lines.append("X-SOCIALPROFILE;TYPE=" + social_name.upper() + ":" + escape(identity[social_name]))
        if business.description and not offline:
            lines.append("NOTE:" + escape(business.description[:120] if offline else business.description))
        if business.address and (not offline or len(business.address) <= 120):
            lines.append("ADR;TYPE=WORK:;;" + escape(business.address[:120] if offline else business.address) + ";;;;")
        if identity and identity["address"] and identity["address"] != business.address:
            lines.append("ADR;TYPE=HOME:;;" + escape(identity["address"][:120] if offline else identity["address"]) + ";;;;")
    else:
        profile = card.owner.profile
        lines.extend(_personal_vcard_lines(profile, offline=offline))
    lines.append("URL:" + escape(card.public_url))
    lines.append("END:VCARD")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
