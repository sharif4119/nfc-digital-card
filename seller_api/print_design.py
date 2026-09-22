import io

import qrcode
from PIL import Image, ImageDraw, ImageFont


PRINT_DPI = 300
CR80_WIDTH_MM = 85.60
CR80_HEIGHT_MM = 53.98
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
        (width - 225, height // 2 + 28),
        cyan,
    )

    back = Image.new("RGB", CR80_SIZE, white)
    back_draw = ImageDraw.Draw(back)
    back_draw.rectangle((0, 0, width, 94), fill=navy)
    back_draw.text(
        (52, 24),
        "NexTap",
        fill=white,
        font=_font(38, bold=True),
    )

    qr = qrcode.make(public_url).convert("RGB")
    qr_size = 390
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
        "SCAN TO CONNECT",
        fill=blue,
        font=_font(25, bold=True),
    )
    back_draw.text(
        (copy_x, 235),
        "Your digital profile,\nready in one tap.",
        fill=navy,
        font=_font(34, bold=True),
        spacing=10,
    )
    back_draw.text(
        (copy_x, 360),
        "No app required.",
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
