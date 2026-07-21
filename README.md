# antarr-demo

A [Wagtail](https://wagtail.org/) CMS site built with Django 6 and Wagtail 7.3.

## Project layout (Django + Wagtail conventions)

This repo follows the [official Wagtail project template](https://docs.wagtail.org/en/stable/reference/project_template.html). The **repository root is the project root** — there is no extra wrapper folder. That is intentional.

```text
antarr-dev/                     ← repo root (also the Django project root)
├── manage.py                   ← CLI entry point (always run commands from here)
├── pyproject.toml + uv.lock    ← Python dependencies (modern replacement for requirements.txt)
├── antarr_demo/                ← Django *project* package (config only, not your content)
│   ├── settings/
│   │   ├── base.py             ← shared settings (most config lives here)
│   │   ├── dev.py              ← local development (DEBUG=True)
│   │   ├── production.py       ← production server settings
│   │   ├── local.py.example    ← copy to local.py for machine-specific secrets
│   │   └── local.py            ← gitignored; secrets and overrides (Wagtail recommended)
│   ├── urls.py                 ← top-level URL routing
│   ├── wsgi.py                 ← WSGI entry (defaults to production settings)
│   └── templates/              ← site-wide templates (404, 500, base)
├── home/                       ← Django *app*: HomePage model + templates + tests
├── search/                     ← Django *app*: search views
└── db.sqlite3                  ← dev database (gitignored)
```

### Naming

| Name | Role |
|------|------|
| `antarr-demo` | Product / package name (`pyproject.toml`) |
| `antarr_demo` | Python package for Django project config (hyphens are invalid in module names) |
| `home`, `search` | Feature apps — add more as the site grows (`blog`, `events`, …) |

### Django vs Wagtail vs Python

- **Python**: dependencies in `pyproject.toml`, lockfile in `uv.lock`, virtualenv in `.venv/`
- **Django**: one *project* package (`antarr_demo/`) wires settings and URLs; *apps* (`home/`) hold models, views, and templates
- **Wagtail**: page types are Django models subclassing `Page`; editors manage them at `/admin/`

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Quick start

```bash
uv sync --dev
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- Site: http://localhost:8000
- Admin: http://localhost:8000/admin/
- Landlord portal: http://localhost:8000/portal/

### Portal demo data

The portal is tenant-scoped through `ProcessMembership`. To create a realistic,
idempotent dataset for a local AuthKit user, run:

```bash
uv run python manage.py seed_portal_demo --email you@example.com
```

Use the same email address to sign into AuthKit. The command creates one managed
property, documents, interventions, planned operations, parcel photographs and a
message thread. It never grants portal access automatically during sign-in.

The institutional homepage and editorial `ArticlePage` content are managed in
Wagtail at `/admin/`; process operations are managed in Django's backoffice at
`/django-admin/`.

## Settings

| Module | Used by | Purpose |
|--------|---------|---------|
| `dev.py` | `manage.py` (default) | Local development |
| `production.py` | `wsgi.py`, Docker | Production servers |
| `local.py` | imported by both | Machine-specific secrets (never commit) |

For production, set `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`, or copy `local.py.example` to `local.py` on the server.

## Development

```bash
uv run pytest                  # tests (WagtailPageTestCase in home/tests.py)
uv run ruff check .            # lint
uv run ruff format .           # format
uv run python manage.py check  # Django system checks
```

## Adding a new content type

Wagtail content types are Django apps with `Page` subclasses:

```bash
uv run python manage.py startapp blog
```

Then:

1. Create a `Page` subclass in `blog/models.py`
2. Register `blog.apps.BlogConfig` in `INSTALLED_APPS` (`antarr_demo/settings/base.py`)
3. Add templates under `blog/templates/blog/`
4. Run `makemigrations` and `migrate`

See the [Wagtail tutorial](https://docs.wagtail.org/en/stable/getting_started/tutorial.html).

## Docker

Set real secrets when running:

```bash
docker build -t antarr-demo .
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=your-secret \
  -e DJANGO_ALLOWED_HOSTS=localhost \
  antarr-demo
```

## Stack

| Package | Version |
|---------|---------|
| Python  | 3.12+   |
| Django  | 6.x     |
| Wagtail | 7.3.x   |

## Security and data handling

- Every portal queryset is filtered through the authenticated user's process
  membership; staff users can access all active processes through the backoffice.
- Sensitive documents live outside the public media directory. Downloads use a
  15-minute signed endpoint and create an `AccessLog` record before access.
- AuthKit identities are linked to Django users at callback time, while process
  access remains an explicit backoffice action.
- Production settings enable HTTPS redirect, HSTS, secure cookies, SameSite
  protection, clickjacking protection and MIME sniffing protection.
- New documents, operations and messages trigger email after the database
  transaction commits, while respecting preferences per user and per process.

For production, replace the local `PrivateObjectStorage` adapter with an
S3-compatible private bucket implementation while retaining the same signed URL
interface. Database and object-storage backups should use separate locations and
an operations-level retention policy; they are intentionally not emulated by the
application process.
