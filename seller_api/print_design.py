import io

import qrcode
from PIL import Image, ImageDraw, ImageFont

from cards.contact import build_vcard
from orders.models import CardAllocation


PRINT_DPI = 300
CR80_SIZE_MM = (85.60, 53.98)
CR80_WIDTH_MM, CR80_HEIGHT_MM = CR80_SIZE_MM
CR80_SIZE = (
    round(CR80_WIDTH_MM / 25.4 * PRINT_DPI),
    round(CR80_HEIGHT_MM / 25.4 * PRINT_DPI),
)


def _font(size, bold=False):
    font_name = (
        "DejaVuSans-Bold.ttf"
        if bold
        else "DejaVuSans.ttf"
    )

    try:
        return ImageFont.truetype(font_name, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _draw_nfc_mark(draw, center, color):
    center_x, center_y = center

    for offset in (0, 30, 60):
        bounds = (
            center_x - 100 - offset,
            center_y - 100 - offset,
            center_x + 100 + offset,
            center_y + 100 + offset,
        )
        draw.arc(
            bounds,
            start=-55,
            end=55,
            fill=color,
            width=12,
        )

    draw.ellipse(
        (
            center_x - 9,
            center_y - 9,
            center_x + 9,
            center_y + 9,
        ),
        fill=color,
    )


def build_card_print_images(public_url):
    card = public_url if hasattr(public_url, "public_token") else None
    allocation = None
    if card:
        allocation = CardAllocation.objects.select_related("order__product").filter(card=card).first()
        public_url = card.public_url
    new_print = bool(card and allocation and allocation.order.offline_contact_print)
    width, height = CR80_SIZE
    navy = "#07111f"
    cyan = "#16d9ff"
    blue = "#287cff"
    white = "#ffffff"
    muted = "#b6c7dc"

    front = Image.new("RGB", CR80_SIZE, navy)
    front_draw = ImageDraw.Draw(front)
    front_draw.rounded_rectangle(
        (42, 42, width - 42, height - 42),
        radius=42,
        outline="#1e3955",
        width=3,
    )
    front_draw.ellipse(
        (width - 410, -290, width + 210, 330),
        fill="#0a2e52",
    )
    front_draw.text(
        (82, 92),
        "NexTap",
        fill=white,
        font=_font(68, bold=True),
    )
    front_draw.rectangle((82, 178, 238, 190), fill=cyan)
    if not new_print:
        front_draw.text(
            (82, 232),
            "Tap once. Share everything.",
            fill=muted,
            font=_font(31),
        )
    front_draw.text(
        (82, height - 112),
        "NFC DIGITAL BUSINESS CARD",
        fill=cyan,
        font=_font(23, bold=True),
    )
    _draw_nfc_mark(
        front_draw,
        (width - 210, height // 2 + 80) if new_print else (width - 225, height // 2 + 28),
        cyan,
    )
    if new_print:
        if card.business_profile:
            business = card.business_profile
            name_x = 178 if business.logo else 82
            if business.logo:
                try:
                    logo = Image.open(business.logo).convert("RGB")
                    logo.thumbnail((76, 76))
                    front.paste(logo, (82, 218))
                except (OSError, ValueError):
                    pass
            front_draw.text((name_x, 220), business.name[:23], fill=white, font=_font(34, bold=True))
            if card.representative:
                front_draw.text((name_x, 278), card.representative.name[:25], fill=cyan, font=_font(27, bold=True))
                front_draw.text((name_x, 319), card.representative.designation[:35], fill=muted, font=_font(22))
        else:
            profile = card.owner.profile
            front_draw.text((82, 225), profile.public_name[:23], fill=white, font=_font(34, bold=True))
            front_draw.text((82, 278), profile.job_title[:35], fill=muted, font=_font(23))

    back = Image.new("RGB", CR80_SIZE, white)
    back_draw = ImageDraw.Draw(back)
    back_draw.rectangle((0, 0, width, 94), fill=navy)
    back_draw.text(
        (52, 24),
        "NexTap",
        fill=white,
        font=_font(38, bold=True),
    )

    offline = new_print
    qr_value = build_vcard(card, offline=True) if offline else public_url
    qr = qrcode.make(qr_value).convert("RGB")
    qr_size = 430 if offline else 390
    qr = qr.resize(
        (qr_size, qr_size),
        Image.Resampling.NEAREST,
    )
    qr_x = 62
    qr_y = 142
    back_draw.rounded_rectangle(
        (
            qr_x - 18,
            qr_y - 18,
            qr_x + qr_size + 18,
            qr_y + qr_size + 18,
        ),
        radius=28,
        fill=white,
        outline="#d8e3ef",
        width=3,
    )
    back.paste(qr, (qr_x, qr_y))

    copy_x = 520
    back_draw.text(
        (copy_x, 180),
        "OFFLINE CONTACT QR" if offline else "SCAN TO CONNECT",
        fill=blue,
        font=_font(25, bold=True),
    )
    back_draw.text(
        (copy_x, 235),
        "Save contact offline.\nOpen profile later." if offline else "Your digital profile,\nready in one tap.",
        fill=navy,
        font=_font(34, bold=True),
        spacing=10,
    )
    back_draw.text(
        (copy_x, 360),
        "Contact snapshot at print time." if offline else "No app required.",
        fill="#4b6075",
        font=_font(25),
    )
    back_draw.rectangle(
        (copy_x, 420, width - 74, 428),
        fill=cyan,
    )
    back_draw.text(
        (copy_x, 463),
        "nextap.pythonanywhere.com",
        fill=navy,
        font=_font(21),
    )

    return front, back


def build_card_print_pdf(public_url):
    front, back = build_card_print_images(public_url)
    output = io.BytesIO()
    front.save(
        output,
        format="PDF",
        save_all=True,
        append_images=[back],
        resolution=PRINT_DPI,
        title="NexTap CR80 Card Print Design",
    )
    return output.getvalue()
