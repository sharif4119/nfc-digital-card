# NexTap Website and Django Backend — Project Handover

## 1. Status and scope

This document describes the repository inspected on 2 November 2026. It covers the Django website/backend only. The Android seller application source is not present here, so app-side behavior (including actual NDEF writing, verification, retries, and device permissions) is **NOT CONFIRMED**.

| Item | Observed value |
|---|---|
| Repository | `sharif4119/nfc-digital-card` (as identified in project brief) |
| Local path | `E:\nfc-card-system` |
| Branch | `codex/personal-business-cards` |
| HEAD | `9ae51a7ded995c2da95bde906582991249060c95` |
| Working tree | Modified and untracked changes are present; do not reset or overwrite them. |
| Recent work | Includes organization single-card identity, customer-facing order numbering, and profile/contact changes. Use `git log -5 --oneline` for the current local history. |

The worktree contains pending changes in `accounts/views.py`, `cards/contact.py`, `cards/presentation.py`, card tests/views, order tests/URLs/views, `payments/views.py`, `profiles/views.py`, customer templates, and a new `orders/presentation.py`. These were preserved. The test run below validates this working tree, not only the checked-in HEAD. No application code, migrations, database contents, or deployment settings were changed for this handover.

## 2. What NexTap does

NexTap links a physical NFC card to a server-hosted digital profile. A customer can register, maintain personal and/or business information, select a product, and create an order. A staff seller uses a token-authenticated API to inspect orders, prepare card records, retrieve the backend-generated public URL, record programming/activation transitions, and download print artwork. A visitor taps the card to open the current public profile or scans the printed QR to import a contact snapshot.

The tag and the printed QR carry different information:

- **NFC NDEF URI:** Android is expected to write the exact `public_url` returned by the API. That URL contains the card’s persistent public token. The backend does not include Android source, so the actual NDEF writer and tag verification are **NOT CONFIRMED** here.
- **Printed QR:** `seller_api/print_design.py` creates a QR containing a vCard 3.0 snapshot from `cards/contact.py`. The generated vCard includes contact fields permitted by the current card/business privacy rules and the same card’s canonical `card.public_url`.
- **Live page:** `GET /c/<token>/` resolves the token and reads profile/business data from the database. Editing the database profile changes the live page without changing the tag. The printed vCard is a snapshot and must be reprinted to reflect changed contact fields.

An internet connection is required to resolve the live URL. Import behavior after scanning the vCard depends on the visitor’s device/browser; the server returns a `.vcf` file and does not force a particular Contacts app to open.

## 3. Architecture and request flow

The project is a conventional Django monolith with server-rendered templates and a Django REST Framework seller API. SQLite is configured for all environments by `config/settings.py`. There is no custom user model: Django’s built-in `auth.User` is used, with a one-to-one `profiles.Profile` for visible customer/account details. DRF token authentication is globally configured; seller endpoints require staff status.

Typical browser request: browser → root `config/urls.py` → app URL pattern → view → form/model validation and ORM operations → template context → Django template → HTML response. A seller API request follows the same URL/view/ORM path, then serializes JSON (or returns binary PDF). Django sessions and CSRF middleware support browser authentication/forms; API token requests use the `Authorization: Token …` header.

### Project structure and important files

| File/folder | Responsibility and important entry points | Why it matters |
|---|---|---|
| `manage.py` | Django command entry point | Checks, migrations, tests, runserver, createsuperuser. |
| `config/settings.py` | Installed apps, SQLite, templates, static/media roots, security, REST settings, env parsing | Main runtime/deployment configuration. |
| `config/urls.py` | Includes admin, core, accounts, profiles, cards, products, orders, seller API | Root route map. Payment URLs are deliberately not included. It currently serves media through Django’s `static.serve` route regardless of DEBUG; production should use an explicit media-serving strategy. |
| `config/wsgi.py`, `config/asgi.py` | Django WSGI/ASGI application exports | PythonAnywhere WSGI configuration should point at `config.wsgi.application`; the actual hosted WSGI file is not in this repo. |
| `accounts/forms.py`, `backends.py`, `views.py`, `urls.py` | Registration, email/username login, dashboard | Customer identity and session flow. Registration stores an auto-generated internal username and a visible display username. |
| `profiles/models.py`, `forms.py`, `presentation.py`, `views.py`, `signals.py` | Personal/business profiles, representatives, offerings, safe links, profile editing/previews, analytics/inquiries dashboard | Business profile behavior and the profile-to-user relation live here. |
| `cards/models.py` | `NFCCard`, `CardVisit`, `CardInquiry`; token and UID generation | NFC lifecycle and public-card data records. |
| `cards/views.py`, `presentation.py`, `contact.py`, `urls.py` | Active public-card lookup, public profile and person pages, QR and vCard endpoints, inquiry handling, visibility resolver | Public exposure and privacy decisions. |
| `products/models.py`, `views.py`, `urls.py`, `admin.py` | Product categories/catalogue | Products and their separate personal/business prices. Legacy dimensions remain in the database but are not part of the customer UI; print size is centralized. |
| `orders/models.py`, `forms.py`, `views.py`, `presentation.py`, `admin.py` | Order creation/history/details, per-order allocations and admin card assignment | The order is the commercial request; `CardAllocation` models each physical-card slot. Customer order numbers are account-local presentation references; internal PKs remain for admin/API. |
| `seller_api/urls.py`, `views.py`, `serializers.py`, `print_design.py` | Staff endpoints, serializers, on-demand print PDF generation | Android seller integration boundary and status operations. |
| `payments/` | `Payment` record and partial SSLCommerz sandbox views/URLs | Paused code. `payments.urls` is not included by `config/urls.py`; do not present payment as a live customer capability. |
| `templates/` | Browser UI for core, registration, profile, public card, products, orders, and dormant payment responses | Server-rendered presentation layer. |
| `static/css`, `static/js` | Styling and local browser scripts | Served from `/static/`; production collection target is `staticfiles/`. |
| `media/` | Local uploaded images | Product/profile/business images. This directory exists locally, but persistent hosted media configuration is not confirmed. |
| `docs/seller-api-business-cards.md` | Existing seller API integration notes | Useful starting point; check it against current route/serializer source before relying on details. |
| `build.sh`, `README.md` | Old Render-oriented build/deployment notes | README describes a prior Render demo and is stale for the stated PythonAnywhere deployment. |
| `requirements.txt`, `.python-version`, `.env.example` | Pinned package versions, Python version marker, safe configuration names | Local setup baseline. `.env.example` is illustrative; never commit `.env`. |
| `*/migrations/` | Historical schema changes | Keep existing migration history; do not edit/delete old migrations to make a fresh schema look simpler. |
| `*/tests.py`, `cards/test_*.py`, `orders/tests.py`, `seller_api/tests.py` | Regression tests | The full suite is the best local behavior check. |
| `db.sqlite3`, `*.bak`, `.env`, `venv/`, `media/` | Local data/secrets/environment artifacts | Must not be committed, replaced, or copied over production. Their content was not inspected for this document. |

### Recommended reading order for a new developer

1. `config/settings.py` and `config/urls.py`
2. `profiles/models.py`, `cards/models.py`, `products/models.py`, `orders/models.py`
3. `accounts/forms.py` and `accounts/backends.py`
4. `orders/forms.py` and `orders/views.py`
5. `cards/presentation.py`, `cards/contact.py`, and `cards/views.py`
6. `seller_api/urls.py`, `seller_api/views.py`, `seller_api/serializers.py`
7. `seller_api/print_design.py`
8. Relevant tests, then corresponding templates
9. Existing seller guide and deployment notes, checking each against source

## 4. Data model and relationships

| Model | Main relationship/purpose |
|---|---|
| Django `User` | Built-in account, authentication and staff flag. `Profile` and `BusinessProfile` are each one-to-one with the owner. |
| `Profile` | One-to-one with User; display username, login email, personal identity/contact fields and profile picture. A `Lower(login_email)` conditional unique constraint protects populated login emails case-insensitively. |
| `BusinessProfile` | One-to-one owner; profile type (`SMALL_BUSINESS`/`ORGANIZATION`), organization subtype, company contacts and `show_owner_identity`. Existing legacy share-owner booleans are retained. |
| `BusinessRepresentative` | Many representatives per BusinessProfile; identity and phone/email public flags. |
| `FeaturedOffering` | Many offerings per BusinessProfile with name, description, optional price/image/link and display position. |
| `Product` | Catalogue record, personal/business category, price, availability and image. Legacy width/height columns remain nullable. |
| `Order` | User and product foreign keys, snapshot total price and customer delivery fields, quantity/type/category, optional business profile and compatibility `assigned_card` one-to-one link. Legacy dimension columns remain nullable. |
| `CardAllocation` | One row per physical card position in an order; unique `(order, position)`, optional one-to-one NFC card, optional representative. This supports multiple business cards and per-card identity. |
| `NFCCard` | Unique internal UID and public token; optional owner, business profile, representative, state and lifecycle timestamps/programmer. |
| `CardVisit` | Visit event for a card with pseudonymous hash and timestamp. |
| `CardInquiry` | Visitor inquiry associated with a card; includes name/contact/message and hashed source value. |
| `Payment` | One-to-one with Order and sandbox transaction state, but its routes are disabled at the root URL level. |

Important deletion behavior: profiles/business records generally follow owner deletion; products use `PROTECT` from orders; business profiles are protected by historical orders; card owner/business/representative links can be set null; an order’s `assigned_card` is set null if a card is deleted; allocations cascade from order and their card reference is set null. Confirm exact migration SQL before any production data cleanup.

Migrations present: profiles `0001`–`0005`; cards `0001`–`0004`; products `0001`–`0002`; orders `0001`–`0006`; payments `0001`. The order migration `0004_backfill_card_allocations.py` is especially significant: it backfills allocation records from existing orders. No migration drift was reported by `makemigrations --check --dry-run` on the inspected tree. Production applied migration state has not been inspected.

## 5. Customer workflows

### Authentication and dashboard

`accounts.RegisterForm` subclasses Django `UserCreationForm`, accepts a visible display username and email, generates a unique internal `customer_<uuidhex>` username, and saves visible/login identity onto the signal-created profile. Email checks are case-insensitive in the form and database constraint for `Profile.login_email`; registration catches `IntegrityError` and returns a field error. Login uses `EmailOrUsernameBackend` (legacy username first, then email `iexact`) and Django sessions. Staff retain their internal username login. The dashboard is `login_required` and reads the user’s cards/profile/orders plus card visits and inquiries.

**Password-validation caveat:** settings list Django’s minimum-eight-character and common-password validators, but `RegisterForm.validate_password_for_user()` returns without invoking them; its help text currently promises any non-empty password. Password confirmation and Django’s password hashing still apply through `UserCreationForm`. Thus an eight-character minimum is **not enforced by customer registration code** even though it appears in global settings. This needs an explicit product/security decision; this documentation task did not change it.

### Personal profile

`profiles.ProfileForm` edits the signed-in user’s saved personal fields and photo. The private preview renders the current database values. An authenticated vCard endpoint is available at `/profile/contact/` (`download_profile_vcard`). A personal public card reads its owner’s current profile when an active card token is visited. Personal profile contact sharing should be understood separately from business owner/representative visibility rules.

### Products and orders

`products.views.product_list` only displays available products and separates Personal and Business categories; detail lookup also requires availability. Price is not submitted as authoritative customer data: `orders.views.create_order` reads `product.price`, assigns the user/product/category/business profile, snapshots `price = product.price * quantity`, sets status fields, saves the order in a transaction, and bulk-creates positions 1 through quantity.

For business products, the form supports `SINGLE` (quantity one) and `MULTIPLE` (2–25). Personal products have quantity hidden and default to one. An owned business profile is required for business-card orders. Payment remains `UNPAID`; the customer is told seller handles payment/confirmation. There is no active checkout gateway in the root URL configuration.

Customer order history shows account-local “My Order N” references via `orders/presentation.py`, while order PKs continue internally and in the seller API/admin. Current references are calculated chronologically from order creation time/PK; they can shift if older records are deleted or backdated. Every allocation’s card position starts from 1 within its own order.

### Business and organization identity behavior

`show_owner_identity` is the opt-in controlling whether a personal/representative summary may appear. `cards.presentation.resolve_business_identity()` performs card-specific selection; an inactive/unavailable assigned identity results in no public identity section. Representative phone/email are only returned when their public flags allow them. The code’s actual cases:

| Card scenario | Resolver behavior when visibility ON | When OFF |
|---|---|---|
| Small Business Single | Owner’s personal profile when it has a full name; representative does not replace owner for this order type. | Business-only display. |
| Small Business Multiple | Requires the representative assigned to that allocation; never substitutes purchaser. | Business-only display. |
| Organization Single | Assigned representative takes precedence if available; otherwise owner’s personal profile may be used. | Organization-only display. |
| Organization Multiple | Uses only the allocation/card representative; never purchaser fallback. | Organization-only display. |

Private preview is `/profile/business/preview/`, owner-only through `login_required`. Its selector uses `CardAllocation.position` and customer order labels when multiple orders need differentiation. `/profile/business/cards/` is the owner’s business card/analytics/inquiry dashboard. The editor saves the BusinessProfile and FeaturedOffering formset transactionally; it has a preview action. Public business content includes only saved offering rows, business contacts/social links, safe normalized URLs and applicable identity.

### Visitor inquiry

For active business cards the public card view accepts an inquiry form with visitor name, generic contact information and message; purpose is not currently a separate required input in the view (legacy `interest` is saved empty). The form has a honeypot (`website_check`), Django CSRF middleware applies to POST, and `cards.views.public_card_view` throttles to three inquiries per card/source hash per hour. It stores a SHA-256 keyed source hash rather than raw IP/user-agent. Legacy contact parsing may map recognizable email/phone into legacy columns. Signed-in business owner views inquiries and visit analytics in `business_cards`. This is application-level throttling, not distributed abuse protection; shared IP/device fingerprints and multi-worker rate enforcement are limitations.

## 6. Public cards, tokens, and contact

`NFCCard.public_token` is generated with `secrets.token_urlsafe(9)` and unique in the database; it is distinct from `card_uid` (inventory/admin identifier) and numeric database PK. `card.public_url` uses `PUBLIC_BASE_URL + /c/<token>/`. `PUBLIC_BASE_URL` defaults to `https://nextap.pythonanywhere.com` in `config/settings.py`.

`cards.views._visible_card()` looks up the token and requires `status="ACTIVE"`, an owner, and either a business profile or owner profile. Therefore `UNASSIGNED`, `ASSIGNED`, `PROGRAMMED`, `INACTIVE`, missing owner/profile are not publicly rendered. Public card views retrieve current stored profile/business/representative data, track GET visits and expose vCard/QR actions. Business representatives use the allocation/card-specific representative; a multiple-card profile does not infer the buyer as representative.

`cards/contact.py` creates vCard 3.0 text, performs escaping and 75-octet UTF-8 line folding. Business offline contact includes business name/official data, permitted owner/representative fields, authorized work contacts and canonical profile URL. A printed QR is offline snapshot information; public profile URL remains dynamic. The contact endpoints include `/c/<token>/contact/`, `/c/<token>/offline-qr/`, `/c/<token>/qr/`, `/c/<token>/person/`, and `/c/<token>/person/contact/`.

## 7. NFC lifecycle and seller API

The backend states are `UNASSIGNED`, `ASSIGNED`, `PROGRAMMED`, `ACTIVE`, `INACTIVE`. The seller app obtains a staff token at `POST /api/seller/login/`. All other seller routes use DRF `IsAdminUser`; DRF globally requires token authentication for authenticated APIs.

| State | Backend meaning/transition | Public profile | PDF endpoint |
|---|---|---|---|
| UNASSIGNED | Stock card, generally no owner; card is available in seller API only when owner null. | No | No |
| ASSIGNED | Bound to customer/order; created by prepare endpoint or manual assignment. | No | Yes |
| PROGRAMMED | Seller API records successful programming timestamp and staff user from ASSIGNED. | No | Yes |
| ACTIVE | Seller API transitions only from PROGRAMMED and sets activation time. | Yes, if owner/profile valid | Yes |
| INACTIVE | Non-public/inactive record. No dedicated activate-from-INACTIVE route is present. | No | No |

`NFCCard.create_with_generated_uid()` creates a temporary unique value, scans existing `NXT-######` values and assigns the next sequence, preserving manually entered UIDs with other formats. The model’s public token default is independently generated. UID race protection is practical but sequence allocation is not a separately serialized global counter; database uniqueness remains the final safeguard.

### Actual seller routes (prefix `/api/seller/`)

All except login require an authenticated staff user; requests should send `Authorization: Token <token>`.

| Method/path | Behavior / response |
|---|---|
| `POST /login/` | JSON `{username,password}`; staff gets `{token,username}`; invalid credentials 401, non-staff 403. |
| `GET /dashboard/` | Counts pending orders and available/assigned/programmed/active cards. |
| `GET /orders/` | JSON array serialized orders, newest first. |
| `GET /orders/<order_id>/` | Order detail JSON using internal order ID. |
| `POST /orders/<order_id>/prepare-card/` | One-card compatibility flow; transaction, idempotent assigned-card response, creates `ASSIGNED` card, owner/profile/order/allocation relations; rejects non-one quantity and conflicting customer card. |
| `POST /orders/<order_id>/assign-card/` | Manual single-card fallback with body `card_id`; requires unassigned unowned card. |
| `POST /orders/<order_id>/allocations/<allocation_id>/prepare/` | Prepare an individual physical slot for multi-card workflows; returns updated order. |
| `GET /cards/available/` | Unassigned cards with no owner. |
| `GET /cards/<card_id>/` | Card detail JSON; includes `print_pdf_url` only for ASSIGNED/PROGRAMMED/ACTIVE. |
| `GET /cards/<card_id>/print/` | On-demand front/back two-page PDF, `application/pdf`, attachment name `NexTap-<UID>-front-back.pdf`; supports ASSIGNED/PROGRAMMED/ACTIVE, no lifecycle change. |
| `POST /cards/<card_id>/programmed/` | Only ASSIGNED → PROGRAMMED; sets `programmed_at`, `programmed_by`. |
| `POST /cards/<card_id>/activate/` | Only PROGRAMMED → ACTIVE; sets `activated_at`. |

Order JSON preserves actual `id` for Android compatibility. `assigned_card` remains for the one-card integration; multi-card orders must use `allocations` (`id`, `position`, representative, card) and compare `prepared_count` against `quantity`. The API source does not include pagination or a separate card rewrite/verify endpoint. Rewrite flow in Android is **NOT CONFIRMED**; a seller may retrieve card `public_url` from order/card JSON, but no dedicated read-only refresh path beyond these detail endpoints exists.

### Print generation

`seller_api/print_design.py` generates both images and PDF on demand (not from temporary uploaded media). It sets 300 DPI and CR80 dimensions 85.60 × 53.98 mm, rasterized to 1011 × 638 pixels. Front artwork varies for personal versus business cards and shows the applicable person/business information; back artwork contains the vCard QR plus scan/tap guidance. `build_card_print_pdf()` produces a two-page PDF. For a card object, QR payload is `build_vcard(card, offline=True)`; the vCard embeds exact `card.public_url`. The API is staff-only and status-limited. Print is optional and does not change status. Font fallback uses Pillow’s default if DejaVu fonts cannot be loaded. Test asserts PDF dimensions and QR content; physical printer alignment/bleed/color is not verified.

## 8. Security, privacy, and limitations

Implemented controls include Django password hashing, session authentication, `login_required` owner views, owner-scoped order queries, CSRF middleware for browser POSTs, seller DRF token authentication plus staff-only permission, unique random public tokens, active-only public page access, `PUBLIC_BASE_URL` canonical links, safe HTTP(S) URL normalization for rendered external links, several upload size validations, security middleware, secure cookies/redirect when DEBUG is false, content-type nosniff, and frame denial.

Limitations/findings from current source:

1. Customer registration skips Django’s configured password validators; see password caveat above.
2. `ALLOWED_HOSTS` has no default host values. Production must configure it explicitly. `DEBUG` defaults true unless `RENDER` is true or DEBUG is set, which is unsafe as an implicit production default.
3. Root URL config serves media through Django’s static `serve` view even outside DEBUG. Production uploaded media access/storage and privacy policy need explicit review.
4. Local media and SQLite are filesystem-bound. PythonAnywhere persistence/backup behavior must be verified before deploy.
5. Global `CSRF_COOKIE_HTTPONLY=False` is intentional default (browser JS may need access); CSRF middleware still protects unsafe browser requests. CORS is not configured in the inspected settings; Android native HTTP is not subject to browser CORS in the same way.
6. Seller token lifecycle/rotation and brute-force throttling for login are not implemented in this source.
7. Local default SECRET_KEY is deliberately insecure and must never be used in production. Secret values were not inspected or copied.
8. Legacy owner-share fields and dimension fields remain in schema. Avoid deleting them without data/migration analysis.
9. `payments/` contains partial SSLCommerz sandbox code, but its URL set is not included in root URLs. It is paused; no live payment path is exposed through configured routes.
10. The README’s Render deployment instructions conflict with the stated PythonAnywhere deployment. No live host configuration, database, media backup, current PythonAnywhere environment, actual WSGI file, or web-server logs were available in this repository. Live status is **NOT CONFIRMED**.

## 9. Local setup and verification

`.python-version` specifies Python 3.14; `requirements.txt` pins Django 6.1.1, DRF 3.18.1, Pillow, qrcode, python-dotenv, requests, Gunicorn and WhiteNoise. The inspected Windows environment has `venv/`.

PowerShell from repository root:

```powershell
py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with local-only values; never paste real secrets into Git.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. For local tests use `python manage.py check`, `python manage.py test`, and `python manage.py makemigrations --check --dry-run`. The environment used for this handover ran these commands successfully (exact results in §11). Tests use Django’s test database; they do not validate or migrate production.

Common problems: wrong Python version or interpreter; missing packages; absent/incorrect allowed host for non-local host; missing migrations; absent uploaded file; stale `staticfiles` after production collection; SQLite file permissions/locking; missing `PUBLIC_BASE_URL`; a test failure due to filesystem image/font dependencies. Never point a local run at production DB or overwrite a production SQLite file.

## 10. PythonAnywhere deployment handover

The following is a safe **procedure template**, not confirmation that these commands match the live account. The directory `/home/NexTap/nfc-card-system` and site `nextap.pythonanywhere.com` came from the project brief; actual account path, virtualenv, database, media directory, WSGI source, and migration state are **NOT CONFIRMED**. Inspect the PythonAnywhere Web tab and files before executing any command. Back up production DB and uploaded media to a separate timestamped location first; do not copy local `db.sqlite3` over production.

1. Record actual website source directory, virtualenv path, WSGI file, SQLite path, media root, current git branch/commit, environment variables and applied migrations.
2. Confirm tested GitHub branch/commit and fetch it. Preserve local/production modifications; review diff before checkout/pull.
3. Create restorable copies of production SQLite DB and media and verify file sizes/readability. Preserve every existing `NFCCard.public_token` and `PUBLIC_BASE_URL`.
4. Activate the actual PythonAnywhere virtualenv and install the pinned requirements only if needed.
5. Set production `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_BASE_URL=https://nextap.pythonanywhere.com`, and `EMAIL_*` as applicable in secure environment configuration. Do not put secrets in Git.
6. Verify DB target and migrations before executing `python manage.py migrate`. Review migration plan against production, never run against a local copy accidentally.
7. Run `python manage.py collectstatic --noinput`; verify the Web tab static mapping points to `staticfiles/`. Configure durable, access-appropriate media storage; do not assume ephemeral/local media behavior is acceptable.
8. Confirm WSGI points to the intended checkout and `config.wsgi.application`, set environment/settings, reload from PythonAnywhere Web tab, inspect error log.
9. Smoke-test login/admin, catalogue, an existing order, seller API token access, a known legacy public token, static images and uploaded media. Do not create or activate a real customer card just for a smoke test.

Useful commands after verifying paths (replace placeholders, do not paste secrets):

```bash
cd /home/NexTap/nfc-card-system
source /path/to/verified/virtualenv/bin/activate
git status --short --branch
git fetch origin
git log -1 --oneline origin/codex/personal-business-cards
python manage.py showmigrations
python manage.py migrate --plan
python manage.py migrate
python manage.py collectstatic --noinput
```

No production deployment, backup, or live-site request was performed for this handover. Do not claim the site is healthy based on local tests.

### Maintenance procedure

- Model change: edit model, add migration, review generated migration and data operations, test from a database copy, then apply to production only after backup.
- API change: preserve old response fields/IDs when Android depends on them; update serializer/view tests and `docs/seller-api-business-cards.md`.
- Template/static change: preserve URL names/context, run tests, collect static on deploy.
- PDF change: verify both card categories, vCard QR payload, page count, mm/inch output and physical print sample.
- Lifecycle change: define allowed source/target states, staff permission, idempotence/concurrency, public visibility and tests together.
- Before deploy: clean working tree review, test full branch, migration plan, backup, deploy one verified commit, smoke test, monitor logs.

## 11. Test and verification results

Executed against the current uncommitted working tree with the repository virtual environment:

| Command | Result |
|---|---|
| `.\venv\Scripts\python.exe manage.py check` | Passed: no issues (0 silenced). |
| `.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run` | Passed: no changes detected. |
| `git diff --check` | Passed; Git printed line-ending conversion warnings for changed files, not whitespace errors. |
| `.\venv\Scripts\python.exe manage.py test` | Passed: 159 tests discovered and run, 159 passed, 0 failed, 0 skipped, 165.379 seconds. Test database created and destroyed by Django. |

Test organization by source: `accounts/tests.py` covers registration/login behavior; `profiles/tests.py` covers profile/business form and ownership behavior; `cards/tests.py`, `cards/test_business_flow.py`, and `cards/test_combined_business_profile.py` cover card/public/profile flows; `orders/tests.py` covers orders/allocations/ownership; `products/tests.py` covers catalogue; `seller_api/tests.py` covers staff API, lifecycle, serialization, and print; `payments/tests.py` tests dormant payment helpers/views. `core/tests.py` covers home/core behavior.

## 12. Source-to-result workflow traces

| Workflow | Trace |
|---|---|
| Register/login | `/accounts/register/` or login URL → `accounts.views.register_view` / `NexTapLoginView` → `RegisterForm` / `EmailOrUsernameBackend` → `User` + signal-created `Profile` → session login and dashboard redirect. |
| Update personal profile | `/profile/edit/` → `profiles.views.edit_profile` → `ProfileForm` → save Profile → `/profile/preview/` reads same saved row. |
| Customer places order | product detail → `/order/<product_id>/` → `orders.views.create_order` → `OrderForm` checks input → server sets user/product/price/status → transaction saves Order and `CardAllocation` rows → redirects to account-local order detail. |
| Seller prepares card | Android seller request → `POST /api/seller/orders/<id>/prepare-card/` or allocation prepare → DRF token auth/staff permission → transaction locks order/allocation → `NFCCard.create_with_generated_uid()` → set owner/status/profile and attach relation → serializer returns UID/token/URL. |
| Seller marks programmed/active | POST `/cards/<id>/programmed/` requires ASSIGNED → set timestamp/programmer; POST `/activate/` requires PROGRAMMED → set activation timestamp → response serializes updated card. |
| NFC URL retrieval/rewrite | Seller reads `public_url` from order/card serializer; app source is absent. Backend route for writing/rewrite is **NOT CONFIRMED**; NFC chip must use exact returned URL according to project protocol. |
| Visitor opens profile | `/c/<token>/` → `cards.views.public_card_view` → `_visible_card()` filters ACTIVE/token and validates owner/profile → presentation resolver and saved models → template; GET creates visit event. |
| Inquiry | POST public business page → CSRF middleware + honeypot/form → source-hash throttle → `CardInquiry` row → redirect with success flag → owner sees it on business dashboard. |
| vCard | `/c/<token>/contact/` or person contact → active-card lookup → `cards.contact.build_vcard()` or `build_public_identity_vcard()` → vCard 3.0 response/attachment. |
| PDF | authenticated staff GET `/api/seller/cards/<id>/print/` → status-filtered card lookup → `build_card_print_pdf()` → images/QR/vCard created in memory → PDF attachment; no lifecycle status mutation. |

## 13. Unverified and follow-up items

- Inspect actual PythonAnywhere Web/Files/Environment/Logs and production migration state; not available to repository inspection.
- Confirm backup and restore procedure for production SQLite plus uploaded media.
- Update stale Render-first README after deployment owner confirms target procedure.
- Confirm Android app version/source contract and physical NFC NDEF write, verify, and rewrite behavior outside this repository.
- Decide/fix customer password validator policy; settings and registration form currently disagree.
- Review media serving/storage privacy and seller token rotation/rate limits before broader production use.
- Test printed cards on the actual stock/printer; test suite only verifies generated files and dimensions.
