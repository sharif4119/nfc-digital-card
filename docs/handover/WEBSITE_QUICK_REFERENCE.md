# NexTap Website / Backend — Quick Reference

## If You Receive This Project Today

1. Open repository `E:\nfc-card-system`; preserve the existing modified/untracked worktree.
2. Use Python 3.14 (listed in `.python-version`) and install `requirements.txt` in a virtual environment.
3. Copy `.env.example` to local `.env`; set local-only values and never commit secrets.
4. Run `python manage.py migrate`, `python manage.py createsuperuser`, then `python manage.py runserver`.
5. Read `config/settings.py`, `config/urls.py`, models, order flow, card views, seller API, and relevant tests.
6. Run `python manage.py check`, `python manage.py test`, and `python manage.py makemigrations --check --dry-run` before changing code.
7. For API checks use a staff token and `Authorization: Token <token>`; do not paste real tokens into docs or Git.
8. For deployment inspect the actual PythonAnywhere WSGI file, venv, DB/media paths, environment, logs and backups before running migration commands.

## Project at a glance

| Topic | Current implementation |
|---|---|
| Purpose | Manage digital profiles and customer orders for reusable NFC cards. |
| Stack | Python 3.14, Django 6.1.1, DRF 3.18.1, SQLite, server-rendered templates, Bootstrap, Pillow/qrcode, WhiteNoise. |
| Main apps | accounts, profiles, products, orders, cards, seller_api, payments (paused), core. |
| User model | Built-in Django User; Profile is one-to-one. |
| Key data | Profile, BusinessProfile, BusinessRepresentative, FeaturedOffering, Product, Order, CardAllocation, NFCCard, CardVisit, CardInquiry, Payment. |
| Hosting | User-stated PythonAnywhere; live configuration/state NOT CONFIRMED. README still has old Render guide. |
| Root routes | Admin, website apps, `/api/seller/`; payment URLs excluded. |
| Tests | `python manage.py test`: 159 passed, 0 failed, 0 skipped in inspected working tree. |

## Main developer files

| Need to change | Start here |
|---|---|
| Environment/security | `config/settings.py`, `config/urls.py` |
| Registration/login | `accounts/forms.py`, `accounts/backends.py`, `accounts/views.py` |
| Personal/business profile | `profiles/models.py`, `forms.py`, `views.py`, `presentation.py` |
| Public NFC/profile and contact | `cards/models.py`, `views.py`, `presentation.py`, `contact.py` |
| Catalogue/order | `products/models.py`, `orders/models.py`, `orders/forms.py`, `orders/views.py` |
| Seller app API | `seller_api/urls.py`, `views.py`, `serializers.py` |
| Print PDF | `seller_api/print_design.py` |
| Browser UI | `templates/`, `static/css/`, `static/js/` |
| Regression checks | app test modules and `cards/test_*.py` |
| Seller integration guide | `docs/seller-api-business-cards.md` |

## Seller API essentials

Base prefix: `/api/seller/`.

1. `POST /login/` with staff `username` and `password` → token.
2. Send `Authorization: Token <token>` on subsequent calls.
3. Read orders: `GET /orders/`; order detail: `GET /orders/<order_id>/`.
4. Single card: `POST /orders/<order_id>/prepare-card/` (idempotent).
5. Multi-card: prepare each allocation at `POST /orders/<order_id>/allocations/<allocation_id>/prepare/`.
6. Consume server response `card_uid`, `public_token`, `public_url`. Never generate these values in Android.
7. Record programming: `POST /cards/<card_id>/programmed/`; activation: `POST /cards/<card_id>/activate/`.
8. Card detail: `GET /cards/<card_id>/`; print PDF: `GET /cards/<card_id>/print/`.

Non-login endpoints require staff. `assigned_card` preserves single-card response compatibility; multiple cards use `allocations` and `prepared_count`. NFC write/readback is app-side and NOT CONFIRMED by this repository.

## Card lifecycle

| State | Meaning | Public page | PDF |
|---|---|---|---|
| UNASSIGNED | Stock | No | No |
| ASSIGNED | Linked to customer/order | No | Yes |
| PROGRAMMED | Seller recorded programming | No | Yes |
| ACTIVE | Activated; token lookup allowed if profile exists | Yes | Yes |
| INACTIVE | Disabled | No | No |

Transitions in seller API: ASSIGNED → PROGRAMMED → ACTIVE. No dedicated INACTIVE reactivation route is present.

## Key distinction

- NFC should store the exact backend-generated public URL as an NDEF URI. Actual Android writer code is outside repository.
- Printed QR encodes a vCard 3.0 snapshot plus that card’s canonical URL.
- Updating profile data changes live page without changing URL/tag. Printed contact data must be reprinted to update the snapshot.
- Public card lookup requires ACTIVE status.

## Local commands

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```

On Windows PowerShell with repository venv, use `venv\Scripts\python.exe manage.py ...`.

## Known limitations / do not assume

- Customer registration bypasses configured password validators; settings and signup behavior disagree.
- PythonAnywhere production paths, current data, WSGI config, backups, media persistence and live health were not inspected.
- README’s deployment section is stale Render documentation.
- Payment code exists but payment routes are disabled.
- Local SQLite/media are not automatically safe for production persistence.
- No Android source exists here to verify NDEF writing, rewrite, or hardware state handling.
- Do not replace production DB with local `db.sqlite3`; preserve public tokens and media.

## Repository handover state

- Branch: `codex/personal-business-cards`
- HEAD: `9ae51a7ded995c2da95bde906582991249060c95`
- Worktree: existing modified/untracked files were present during handover; this documentation adds only `docs/handover/` files.
- No migration drift detected locally; production migration state is unknown.
