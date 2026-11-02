# NexTap Website and Backend — Viva Preparation

Use these answers as spoken explanations. Android source is not in this repository, so avoid claiming that physical NDEF writing or rewrite behavior was verified here.

## Short explanations

**30 seconds:** NexTap is a Django website and seller API for managing NFC digital business cards. Customers create profiles and orders. Staff prepare and activate card records through a protected API. The tag is intended to contain a backend-generated public URL, while printed QR artwork contains a vCard contact snapshot and that URL. Visitors can open current profile data online or save the snapshot.

**1 minute:** Traditional paper cards become outdated when contact details change. NexTap stores profiles in Django and associates each physical card with a persistent random public token. Customers manage personal and business information and order products. Business orders can contain individual allocations with a representative per card. Staff use a token-authenticated API to prepare cards and receive the server-generated UID and URL. Only ACTIVE cards expose public pages. The printable PDF has two sides; its QR uses vCard 3.0 data, while the NFC URI is the live profile URL. Payment routes are currently disabled.

**3 minutes:** The project is a Django monolith with server-rendered templates and a Django REST Framework seller API. Django’s built-in User handles authentication, and Profile stores visible customer data. BusinessProfile, BusinessRepresentative, and FeaturedOffering model organization content. Product and Order represent the catalogue and purchases. Each CardAllocation is one physical-card slot and can reference its NFC card and representative.

When a customer orders, the server validates fields, reads the price from the Product row, snapshots the total, saves Order in a transaction, and creates allocation positions. Staff authenticate at the seller login endpoint and send an API token. Preparing a card creates an NFCCard with generated UID and public token, attaches it to the customer/order and returns its public URL. Status endpoints enforce the expected prior state. Public lookup requires ACTIVE status.

The NFC and QR payloads differ. The Android seller app should write the returned URL as an NDEF URI; Android source is absent, so physical writing is not verified by this repository. The printed QR contains a vCard 3.0 snapshot built using current privacy rules and the same profile URL. Online profile changes therefore do not require a new NFC URL, but the printed contact snapshot must be regenerated to include changed details. Local verification passed 159 tests; PythonAnywhere production state still needs separate verification.

## Demonstration script (5–7 minutes)

Prepare test customer/staff accounts, an available product, and a test NFC tag. Do not use production customer data. Hardware steps depend on the separate Android app.

| Time | Action | Expected result and source | What to say |
|---|---|---|---|
| 0:00–0:35 | Register or sign in | Session login, dashboard from accounts.views | “Django sessions protect customer pages.” |
| 0:35–1:00 | Open Cards and a product | Available Product list/detail | “Availability and prices come from backend data.” |
| 1:00–1:30 | Submit Personal or Business order | Order plus allocation rows from orders.views.create_order | “The server calculates the price; it does not trust a browser price.” |
| 1:30–2:05 | Edit and preview profile | Profile/BusinessProfile and saved offerings | “Public pages read current saved records.” |
| 2:05–2:35 | Seller login, list orders | POST seller login, then GET seller orders | “The API requires token auth and staff permission.” |
| 2:35–3:10 | Prepare card/allocation | NFCCard created, assigned, UID/token/URL returned | “The backend generates UID and URL; Android consumes them.” |
| 3:10–3:45 | Write NFC URI in Android | Write returned public_url, then read it back (app-side behavior not confirmed here) | “The tag stores a URL, not the profile database record.” |
| 3:45–4:10 | Mark programmed, then activate | ASSIGNED → PROGRAMMED → ACTIVE endpoints | “Each endpoint checks the prior state; ACTIVE permits public access.” |
| 4:10–4:45 | Open public profile | Token lookup, active-only view, visit record | “Profile fields are live database data.” |
| 4:45–5:15 | Scan QR or use Save Contact | vCard 3.0 contact import plus URL | “This QR is a contact snapshot, unlike the NFC URI.” |
| 5:15–5:45 | Download print PDF | Two-page CR80 PDF; status unchanged | “Printing is optional and independent of activation.” |
| 5:45–6:00 | Explain rewrite | Current URL available from card/order detail | “After profile edits, the URL remains valid; physical rewrite/readback is app-side and not confirmed here.” |

### Demo troubleshooting

- No product: check is_available and category in admin.
- Business order rejected: create the customer’s BusinessProfile first.
- API 401: send Authorization: Token plus the actual staff token.
- API 403: token user must be staff.
- Prepare conflict: customer may already have a non-INACTIVE personal card; multi-card uses allocation preparation.
- Public URL 404: check token, owner/profile, and ACTIVE status.
- Missing image: media may be absent in the demo filesystem.
- PDF error: verify Pillow/qrcode dependencies and printable card status.
- No tag/device: show the API response and clearly state that it does not prove NDEF writing.

## Question bank

Every entry includes an answer, source trace, likely follow-up, and follow-up answer.

### A. Project introduction and scope

1. **What problem does NexTap solve?** It creates a reusable digital identity linked to a physical card. Trace: Profile, BusinessProfile, public_card_view. Follow-up: What remains physical? Answer: NFC card and print.
2. **Why are paper cards limited?** Printed details become stale. Trace: profile models/public view. Follow-up: Does printed QR update? Answer: No, it is a snapshot.
3. **Who uses the system?** Customers, staff sellers, and public visitors. Trace: accounts, seller_api, cards. Follow-up: Who uses the seller API? Answer: Staff.
4. **What is the backend’s role?** It is source of truth for records, card IDs, tokens, URLs, and lifecycle. Trace: models and seller views. Follow-up: Does Android create URLs? Answer: No.
5. **What is the project scope here?** Website/backend only; Android code is absent. Follow-up: What remains unverified? Answer: NDEF writing, tag verification, retry.
6. **Is payment live?** No; payments routes are not included at root. Trace: config.urls. Follow-up: Does partial code exist? Answer: Yes, isolated in payments.
7. **Is production deployment verified?** No; only local checks were run. Follow-up: First deployment action? Answer: Verify backup and actual PythonAnywhere configuration.
8. **Why document limitations?** To separate evidence from assumptions. Follow-up: Example? Answer: Serializer URL is verifiable; physical tag write is not.

### B. Architecture, Python and Django

9. **Why Django?** It supplies ORM, auth, forms, admin, sessions, CSRF and templates. Trace: settings/apps. Follow-up: Tradeoff? Answer: A monolith is straightforward now but may need scaling work later.
10. **Describe the architecture.** Django pages and DRF API share a database and models. Trace: config.urls and seller_api. Follow-up: Is the website a SPA? Answer: No, templates render HTML server-side.
11. **What is request flow?** URL resolver → view → validation/ORM → template or serializer → response. Trace: config.urls. Follow-up: Root route file? Answer: config/urls.py.
12. **What is a Django app?** A module grouping related domain code. Follow-up: Example? Answer: orders owns order behavior.
13. **What does ORM mean?** Object-relational mapping translates model operations into database queries. Follow-up: Benefit? Answer: Structured database work and migrations.
14. **What is a migration?** Versioned schema change applied in dependency order. Trace: app migrations. Follow-up: Delete historical migrations? Answer: No.
15. **Why templates?** They render server-provided context as HTML. Trace: templates and browser views. Follow-up: Default output protection? Answer: Django autoescapes normal variables.
16. **Where are settings?** config/settings.py. Follow-up: What important values? Answer: DB, static/media, security, REST auth and environment parsing.
17. **What is WSGI?** Python web-server interface for synchronous Django deployment. Trace: config/wsgi.py. Follow-up: Is hosted WSGI file inspected? Answer: No.

### C. DRF and Android integration

18. **Why REST API?** The separate seller client needs HTTP/JSON operations. Trace: seller_api views and serializers. Follow-up: Does it replace HTML? Answer: No.
19. **How does seller login work?** POST username/password, authenticate, require staff, return DRF token. Trace: seller_login. Follow-up: What if nonstaff? Answer: 403.
20. **How is token sent?** Authorization: Token <token>. Trace: DRF TokenAuthentication. Follow-up: What if missing? Answer: 401.
21. **What does serializer do?** Converts model fields to JSON. Trace: seller_api/serializers.py. Follow-up: Nested card? Answer: assigned_card and allocations.
22. **How does Android obtain the URL?** Read public_url returned by card/order serializer. Follow-up: May it construct URL? Answer: No.
23. **What supports old one-card workflow?** prepare-card route and assigned_card field. Follow-up: Multiple cards? Answer: Read allocations and prepare each.
24. **How are multiple allocations represented?** Position, representative, card, and allocation ID. Follow-up: Is assigned_card enough? Answer: No; it is compatibility/first-card data.
25. **Is seller list paginated?** No pagination is configured in inspected route. Follow-up: Scaling concern? Answer: Add pagination and query tuning.
26. **Is NFC rewrite verified?** No Android source is available. Follow-up: How to validate? Answer: Inspect app and test write/readback with a tag.

### D. Database and model design

27. **Why use built-in User?** Preserves existing user IDs and Django admin/auth. Trace: no AUTH_USER_MODEL; Profile one-to-one. Follow-up: Visible username? Answer: Profile.display_username.
28. **How is Profile linked?** One-to-one with User. Follow-up: Why? Answer: One account has one personal profile.
29. **How is business content represented?** BusinessProfile owns multiple representatives and offerings. Follow-up: Ordering offerings? Answer: Position, then ID.
30. **What is CardAllocation?** A physical card slot under an Order. Follow-up: Why not quantity only? Answer: Each physical card needs its own card and representative.
31. **Why store order price?** It snapshots purchase price. Trace: create_order. Follow-up: Product price changes later? Answer: Existing total remains.
32. **Why retain dimension columns?** Historical data compatibility; printer uses central CR80 size. Follow-up: Remove later? Answer: Only after data/migration analysis.
33. **What uniqueness prevents duplicate slot positions?** Unique constraint on order and position. Trace: CardAllocation.Meta. Follow-up: Duplicate card? Answer: One-to-one card relation also constrains it.
34. **What protects historical product references?** Order.product uses PROTECT. Follow-up: Why? Answer: Preserve order history.
35. **Where are migration histories?** Each app’s migrations folder. Follow-up: Production migration state confirmed? Answer: No.

### E. Authentication, security and validation

36. **How does customer login work?** Backend checks username then case-insensitive email. Trace: EmailOrUsernameBackend. Follow-up: Staff compatibility? Answer: Existing username works first.
37. **Can display names repeat?** Yes; separate Profile display_username. Follow-up: What stays unique? Answer: Internal username and login email.
38. **How is email uniqueness checked?** Form plus Lower(login_email) database constraint and IntegrityError handling. Follow-up: Why two levels? Answer: User feedback plus race-safe constraint.
39. **What password issue exists?** Registration overrides password validation and does not call validators. Trace: RegisterForm.validate_password_for_user. Follow-up: Is it still hashed? Answer: Yes, Django hashes through UserCreationForm.
40. **How are customer pages protected?** login_required and user-scoped queries. Follow-up: Order example? Answer: Query filters user=request.user.
41. **How is seller authorization protected?** Token authentication and IsAdminUser. Follow-up: Is any authenticated user enough? Answer: No.
42. **How are public inactive cards blocked?** _visible_card filters ACTIVE. Follow-up: Response? Answer: 404.
43. **How are external links validated?** normalize_web_url permits HTTP/HTTPS and rejects unsafe schemes. Follow-up: Does this prove the site is safe? Answer: No, only URL syntax/scheme is checked.
44. **How is CSRF addressed?** Django CSRF middleware protects browser form POSTs. Follow-up: API auth? Answer: Token auth for seller API.
45. **How are inquiries throttled?** Honeypot and three per card/source hash per hour. Follow-up: Distributed limiter? Answer: No.
46. **What protects representative contact fields?** phone_public/email_public plus identity visibility. Follow-up: Are they always public? Answer: No.
47. **Is CORS configured?** No CORS settings/package found. Follow-up: Native Android? Answer: Browser CORS is distinct; native app still needs TLS/API security.
48. **What is a key deployment risk?** Insecure default SECRET_KEY and DEBUG default behavior. Follow-up: Production action? Answer: Set strong secret, DEBUG false, host/origin allowlists.

### F. Profiles and ordering

49. **What is stored in Profile?** Identity, work, contact/social fields and picture. Follow-up: Is it always public? Answer: Public access depends on active card and profile type/privacy.
50. **How does preview work?** Authenticated view reads saved profile. Trace: profile_preview. Follow-up: Public route? Answer: No.
51. **How are unavailable products blocked?** List, detail and order lookup filter availability. Follow-up: Crafted order POST? Answer: Product lookup still fails.
52. **Who calculates price?** Server uses Product.price and quantity. Follow-up: Trust submitted price? Answer: No.
53. **What is Business Single?** One business card; owner identity may appear when setting is enabled. Follow-up: What is Multiple? Answer: Several cards with per-card reps.
54. **What does Business Multiple require for identity?** Assigned allocation representative. Follow-up: Purchaser fallback? Answer: Never.
55. **What is Organization Single identity behavior?** Representative if assigned, otherwise owner profile may be used when visibility is enabled. Follow-up: When disabled? Answer: Organization-only.
56. **What is Organization Multiple behavior?** Uses that allocation’s representative only. Follow-up: Missing rep? Answer: Omit identity rather than showing purchaser.
57. **What happens at order creation?** Save order and allocate positions transactionally. Follow-up: Card created immediately? Answer: No; seller prepares later.
58. **Can user view another order?** Owner-scoped lookup prevents it. Follow-up: Response? Answer: 404.
59. **What is My Order numbering?** Account-local chronological label. Follow-up: Permanent? Answer: Can shift after delete/backdate.
60. **How do card numbers start?** Each order allocation positions begin at 1. Follow-up: Distinguish repeated Card 1? Answer: Use My Order label/date.

### G. Public profiles and inquiries

61. **Where do offerings come from?** Saved FeaturedOffering rows. Follow-up: Empty case? Answer: Template shows empty state.
62. **Is business preview public?** No, login-protected and owner-scoped. Follow-up: Need active NFC? Answer: No.
63. **What does show_owner_identity control?** Whether identity resolver can return person summary. Follow-up: Missing person? Answer: Resolver yields no identity.
64. **How does representative assignment work?** Allocation points to BusinessRepresentative; card carries the relation after preparation. Follow-up: Can wrong business representative leak? Answer: Resolver validates business ownership.
65. **What does inquiry store?** Name, generic contact, message, card and timestamp/source hash. Follow-up: Who can view? Answer: Owner dashboard.
66. **Does inquiry require consent checkbox?** Current flow sets legacy consent false and uses explanatory notice. Follow-up: Is affirmative consent stored? Answer: No.
67. **How are visits counted?** CardVisit events, distinct visitor hashes as estimated unique count. Follow-up: Are unique counts exact humans? Answer: No.
68. **What is a limitation of source hash?** Pseudonymous fingerprint can conflate or split visitors. Follow-up: Is it raw IP storage? Answer: No raw address field is stored in model.

### H. Tokens, lifecycle, NFC and print

69. **Why separate card UID and public token?** UID is internal stock identifier; token is public route key. Follow-up: Does route use PK? Answer: No.
70. **How is public token made?** secrets.token_urlsafe(9) with unique DB field. Follow-up: Is it personally meaningful? Answer: No.
71. **How is NXT UID made?** Create helper scans NXT sequence and assigns next number. Follow-up: Manual formats? Answer: Remain valid.
72. **What does ASSIGNED mean?** Card linked to owner/order, not public. Follow-up: Printable? Answer: Yes.
73. **What does PROGRAMMED mean?** API recorded programming time/staff after ASSIGNED. Follow-up: Public? Answer: No.
74. **What does ACTIVE mean?** Activated and eligible for public lookup. Follow-up: Transition source? Answer: PROGRAMMED.
75. **What does INACTIVE mean?** Not publicly viewable or printable. Follow-up: Reactivate endpoint? Answer: No dedicated INACTIVE transition.
76. **What is written to NFC?** Intended NDEF URI is the returned public URL; Android implementation is absent. Follow-up: Profile data on tag? Answer: No.
77. **Why no rewrite after profile edit?** Stable URL resolves to updated server record. Follow-up: What should be regenerated? Answer: Printed vCard snapshot.
78. **What if NFC writing fails?** Backend has no hardware confirmation; app should verify before marking programmed. Follow-up: Is this app behavior verified? Answer: No.
79. **How is PDF generated?** Pillow front/back images saved to in-memory PDF. Trace: seller_api.print_design. Follow-up: Stored permanently? Answer: No.
80. **What is CR80 output size?** 85.60×53.98 mm, 300 DPI, 1011×638 px. Follow-up: Printer tested? Answer: Not by automated tests.
81. **What does print QR contain?** vCard 3.0 snapshot with card URL. Follow-up: Same as NFC? Answer: No.
82. **Can PDF print before activation?** Yes for ASSIGNED/PROGRAMMED/ACTIVE. Follow-up: Does printing change status? Answer: No.
83. **What vCard features exist?** VERSION 3.0, escaping and UTF-8 line folding. Follow-up: Universal certification? Answer: No, not certified across all contact apps.

### I. Deployment, tests and examiner challenges

84. **Why SQLite?** It is current configured DB and simple for development. Follow-up: Scale suitability? Answer: Needs review as concurrency/load grows.
85. **What Python version is listed?** 3.14 in .python-version. Follow-up: Django pin? Answer: 6.1.1 in requirements.
86. **What must be verified on PythonAnywhere?** Actual paths, venv, WSGI, DB/media, env and migration state. Follow-up: Is it verified? Answer: No.
87. **What does collectstatic do?** Copies static app assets into STATIC_ROOT. Follow-up: User uploads? Answer: Separate media handling.
88. **What tests passed?** 159 run, all passed, none skipped. Follow-up: Command? Answer: python manage.py test.
89. **Why is it more than NFC demo?** It includes accounts, orders, profile content, API permissions, data relationships, lifecycle and tests. Follow-up: Is hardware integration proven? Answer: Not in this repo.
90. **Can product price edits change existing orders?** No, order saves price snapshot. Follow-up: Where? Answer: create_order sets price.
91. **Difference between 401 and 403?** 401 unauthenticated; 403 authenticated but unauthorized. Follow-up: Example? Answer: Customer token is 403 at staff view.
92. **Why use transaction in card preparation?** Groups card/order/allocation writes. Follow-up: Does it solve every race? Answer: No; DB constraints and backend-specific locking matter.
93. **What if a personal customer already has a card?** Prepare rejects another non-INACTIVE card. Follow-up: Why allow business? Answer: Business orders can contain representatives/multiple physical cards.
94. **Difference between order and card status?** Order tracks fulfillment; card tracks physical card lifecycle. Follow-up: Example? Answer: CARD_ASSIGNED order can have ASSIGNED card.
95. **What deployment facts are unknown?** Live site, WSGI, backups, production migration/media state. Follow-up: Evidence needed? Answer: PythonAnywhere config, logs and restore test.
96. **What before schema changes?** Backup, inspect data/migration, test copy and migration plan. Follow-up: Copy local DB to prod? Answer: Never.
97. **How add API field safely?** Serializer plus tests/docs and Android compatibility review. Follow-up: Why preserve old fields? Answer: Existing clients depend on contract.
98. **Does API write NFC?** No; it manages server record/status and returns URL. Follow-up: Who writes tag? Answer: Android client.
99. **Does random token replace privacy controls?** No; public ACTIVE pages still intentionally disclose approved fields. Follow-up: What to avoid? Answer: Never serialize private details by default.
100. **What can you claim as individual contribution?** Only work supported by your actual commits and implementation. Follow-up: How demonstrate it? Answer: Trace a commit/file/test honestly.

## Defense checklist

- Distinguish NFC URL from QR vCard snapshot.
- State ACTIVE-only public access and staff-only API.
- Explain business identity rules by order type.
- Acknowledge registration password-validator inconsistency.
- Quote the 159-test local result, not live deployment verification.
- Do not claim payment, Android rewrite, or production backup is complete.
