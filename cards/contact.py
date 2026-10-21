"""vCard 3.0 used by downloads, offline QR and print artwork."""


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


def build_vcard(card, *, offline=False):
    business = card.business_profile
    representative = card.representative
    lines = ["BEGIN:VCARD", "VERSION:3.0"]
    if business:
        contact_name = representative.name if representative else business.name
        lines.append("N:;" + escape(contact_name) + ";;;")
        lines.append("FN:" + escape(contact_name))
        lines.append("ORG:" + escape(business.name))
        if representative and representative.designation:
            lines.append("TITLE:" + escape(representative.designation))
        if representative and representative.phone:
            lines.append("TEL;TYPE=WORK:" + escape(representative.phone))
        if representative and representative.email:
            lines.append("EMAIL;TYPE=WORK:" + escape(representative.email))
        if business.phone:
            lines.append("TEL;TYPE=WORK:" + escape(business.phone))
        if business.email:
            lines.append("EMAIL;TYPE=WORK:" + escape(business.email))
        if business.website:
            lines.append("URL:" + escape(business.website))
        if business.description:
            lines.append("NOTE:" + escape(business.description[:120] if offline else business.description))
        if business.address and not offline:
            lines.append("ADR;TYPE=WORK:;;" + escape(business.address) + ";;;;")
    else:
        profile = card.owner.profile
        lines.append("N:;" + escape(profile.public_name) + ";;;")
        lines.append("FN:" + escape(profile.public_name))
        if profile.company and not offline:
            lines.append("ORG:" + escape(profile.company))
        if profile.job_title and not offline:
            lines.append("TITLE:" + escape(profile.job_title))
        if profile.phone:
            lines.append("TEL:" + escape(profile.phone))
        if profile.email:
            lines.append("EMAIL:" + escape(profile.email))
        if profile.website and not offline:
            lines.append("URL:" + escape(profile.website))
        if profile.bio:
            lines.append("NOTE:" + escape(profile.bio[:120] if offline else profile.bio))
        if profile.address and not offline:
            lines.append("ADR:;;" + escape(profile.address) + ";;;;")
    lines.append("URL:" + escape(card.public_url))
    lines.append("END:VCARD")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
