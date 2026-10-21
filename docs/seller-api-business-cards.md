# NexTap seller API: personal and business cards

This extends the existing token-authenticated staff API. Send `Authorization: Token <seller_token>` after `POST /api/seller/login/`. The login request still uses the staff username and password. Existing routes and the `assigned_card` field remain available.

## Order responses

`GET /api/seller/orders/` and `GET /api/seller/orders/<order_id>/` now include these additional fields:

```json
{
  "id": 42,
  "card_category": "BUSINESS",
  "business_order_type": "MULTIPLE",
  "quantity": 2,
  "prepared_count": 1,
  "assigned_card": {
    "id": 61,
    "card_uid": "NXT-000061",
    "public_url": "https://nextap.pythonanywhere.com/c/EXAMPLE_TOKEN/",
    "print_pdf_url": "https://nextap.pythonanywhere.com/api/seller/cards/61/print/",
    "status": "ASSIGNED",
    "card_category": "BUSINESS",
    "representative": {"id": 5, "name": "Rahim", "designation": "Manager", "phone": "", "email": ""}
  },
  "allocations": [
    {"id": 93, "position": 1, "representative": {"id": 5, "name": "Rahim", "designation": "Manager", "phone": "", "email": ""}, "card": {"id": 61, "status": "ASSIGNED", "public_url": "https://nextap.pythonanywhere.com/c/EXAMPLE_TOKEN/"}},
    {"id": 94, "position": 2, "representative": null, "card": null}
  ]
}
```

The example abbreviates the existing order and card fields. The real response still contains all legacy fields, including `username`, delivery details, product name, price, payment status, order status and timestamps. `price` is the saved total for the order. `quantity` is the number of physical cards. `prepared_count` counts allocations with a card. `assigned_card` is the first prepared card for compatibility; for multiple-card orders use `allocations` as the source of truth.

`card_category` is `PERSONAL` or `BUSINESS`. `business_order_type` is empty for personal and historical orders, `SINGLE` or `MULTIPLE` for new business orders. A card's `representative` can be `null` until the buyer enters the details on the website. Sellers cannot change business content or representative data through this API. New multiple-card web orders currently allow 2 to 25 cards per order.

## Preparing each physical card

`POST /api/seller/orders/<order_id>/allocations/<allocation_id>/prepare/` takes no body. Read allocation IDs from the order response. It creates one unique NFC card for that allocation and returns the updated order object (HTTP 200). Repeating the request returns the same card. Only staff tokens can call it. The card starts at `ASSIGNED`, owned by the purchaser; `programmed_at`, `programmed_by`, and `activated_at` are null.

For existing one-card workflows, `POST /api/seller/orders/<order_id>/prepare-card/` remains available. It returns the existing `assigned_card` on retry. `POST /api/seller/orders/<order_id>/assign-card/` remains the manual single-card fallback. Bulk orders must use their allocation IDs.

The server generates `card_uid`, `public_token`, `public_url` and `print_pdf_url`. The Android app must use the returned `public_url` for NFC writing; it must never construct a URL or UID. Do not treat order status `CARD_ASSIGNED` as all bulk cards complete; compare `prepared_count` with `quantity` and inspect every allocation.

## Printing, programming and activation

- `GET /api/seller/cards/<card_id>/` returns card detail with category, representative and print URL when printable.
- `GET /api/seller/cards/<card_id>/print/` returns `application/pdf`, two pages (front and back), with `Content-Disposition: attachment; filename="NexTap-<card_uid>-front-back.pdf"`. Staff token required. It works for `ASSIGNED`, `PROGRAMMED` and `ACTIVE` and does not change status. New orders print a labelled offline vCard QR containing the exact canonical public profile URL. Historical orders keep the original online URL QR artwork.
- `POST /api/seller/cards/<card_id>/programmed/` changes one `ASSIGNED` card to `PROGRAMMED`.
- `POST /api/seller/cards/<card_id>/activate/` changes one `PROGRAMMED` card to `ACTIVE`.

These transitions happen per card. Only `ACTIVE` cards expose `/c/<public_token>/`. Printing can happen before or after programming; it is optional. Printed offline contact content is a snapshot and must be reprinted if business or representative details change. The online profile uses live database values.

## Deployment and stock configuration

Set `PUBLIC_BASE_URL=https://nextap.pythonanywhere.com` in production so all NFC, QR and PDF links use the canonical domain. Configure a product's category and price in Django admin. Personal and Business artwork differs, but every print uses the centrally configured CR80 stock size (85.60 × 53.98 mm at 300 DPI). Historical dimension columns are retained as legacy data and are ignored by new orders and print generation. Verify printed output with the actual card stock and phones before fulfillment.

Run `python manage.py prune_card_activity` daily (for example, a scheduled task). It removes anonymous visit records after 90 days and inquiries after 180 days. Back up the database and persistent uploaded media before deployment, then apply migrations in order. No payment gateway changes are part of this feature.
