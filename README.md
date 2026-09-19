# NFC Digital Business Card System

A Django application for customer profiles, NFC card ordering, administrator card assignment, public digital cards, QR codes, and vCard downloads.

## Local development

1. Create and activate a virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust the local values.
4. Run `python manage.py migrate`.
5. Start Django with `python manage.py runserver`.

Payment integration is intentionally paused, and payment URLs are not currently enabled.

## First demo deployment on Render

This setup intentionally uses SQLite and local media storage for the first university/demo deployment.

1. Push the project to a GitHub repository.
2. In Render, create a new **Web Service** and connect the GitHub repository.
3. Select the Python runtime and the Free instance type.
4. Set the build command to:

   ```text
   ./build.sh
   ```

5. Set the start command to:

   ```text
   gunicorn config.wsgi:application
   ```

6. Add these environment variables in Render:

   - `SECRET_KEY`: required; generate a new random value in Render.
   - `DEBUG`: required; set it to `False`.
   - `ALLOWED_HOSTS`: optional for the generated Render domain because Render supplies `RENDER_EXTERNAL_HOSTNAME`; add comma-separated custom domains here later if needed.
   - `CSRF_TRUSTED_ORIGINS`: optional; add comma-separated HTTPS origins for custom domains later if needed.

   Do not add SSLCOMMERZ credentials yet. Payment integration remains paused.

7. Deploy the service. The build script installs dependencies, collects static files, and applies migrations.
8. After deployment, use the Render Shell to run `python manage.py createsuperuser`, if shell access is available for the selected service. Because this demo uses ephemeral SQLite, that account is temporary.
9. Test registration, login, products, ordering, admin card assignment, the public `/c/<token>/` URL, QR images, and vCard downloads.

Render automatically provides `RENDER` and `RENDER_EXTERNAL_HOSTNAME`; they do not need to be added manually.

### Demo storage limitations

Render Free web services use an ephemeral filesystem. Consequently:

- the SQLite database can be reset after an idle spin-down, restart, or redeploy;
- accounts, profiles, products, orders, cards, and the demo superuser can disappear;
- uploaded profile and product images can disappear;
- each build runs migrations to create a fresh database when necessary.

These limitations are accepted only for this first university/demo deployment. A durable deployment should use PostgreSQL and external media storage.
