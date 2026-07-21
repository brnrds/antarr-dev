# Antarr

Antarr is a Portuguese forestry-management web application built with Django 6
and Wagtail 7.3. It currently combines two products in one project:

- a public institutional website and editorial area managed through Wagtail;
- a tenant-scoped landlord portal for following managed forestry properties.

The portal uses WorkOS AuthKit for sign-in, links external identities to local
Django users, and grants property access only through explicit
`ProcessMembership` records.

## Current functionality

### Public website

- Editable institutional homepage with hero, approach and contact content.
- Wagtail-managed editorial articles with publication date, summary, rich text
  and an optional hero image.
- Database-backed Wagtail search.
- Responsive public templates and static assets.

### Landlord portal

- Overview of a forestry process, progress and recent activity.
- Private documents with type filtering and time-limited download links.
- Parcel photographs and chronological views.
- Intervention history and planned-operation calendar.
- Message threads between landlords and the Antarr team.
- Per-process email notification preferences.
- Recent sensitive-resource access history.
- Multiple members and roles per forestry process.

Documents and photographs currently use a local private-filesystem adapter.
New documents, operations and messages schedule email notifications after the
database transaction commits.

## Project structure

The repository root is also the Django project root.

```text
antarr-dev/
├── manage.py                    # Django command-line entry point
├── pyproject.toml + uv.lock     # Python dependencies and lockfile
├── CONTEXT.md                   # Agreed behavioral test seams and TDD workflow
├── antarr_demo/                 # Project settings, URLs, auth views and shared assets
│   ├── settings/                # Base, development and production settings
│   ├── templates/               # Shared, error and base templates
│   └── static/                  # Shared CSS, JavaScript and images
├── home/                        # Wagtail HomePage and ArticlePage content types
├── portal/                      # Tenant-scoped portal domain and HTTP interface
│   ├── management/commands/     # Demo-data seeding
│   ├── services/                # Notifications and private object storage
│   └── templates/portal/        # Portal screens
└── search/                      # Public Wagtail search view
```

`antarr-demo` is the Python distribution name; `antarr_demo` is the importable
Django project package.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- A WorkOS AuthKit application to exercise portal sign-in

The public site and both administration interfaces can run without WorkOS
credentials. The AuthKit login flow cannot.

## Local setup

```bash
uv sync --dev
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Local development uses SQLite, debug mode, permissive hosts and Django's console
email backend. Machine-specific settings can be added by copying
`antarr_demo/settings/local.py.example` to the gitignored `local.py`.

### Local URLs

| URL | Purpose |
|---|---|
| `http://localhost:8000/` | Public Wagtail site |
| `http://localhost:8000/portal/` | Landlord portal |
| `http://localhost:8000/admin/` | Wagtail content administration |
| `http://localhost:8000/django-admin/` | Portal/process backoffice |
| `http://localhost:8000/search/` | Public content search |
| `http://localhost:8000/auth/login/` | Start AuthKit sign-in |
| `http://localhost:8000/auth/callback/` | AuthKit callback |

## WorkOS AuthKit

Copy `.env.example` to `.env` and provide the AuthKit credentials:

```dotenv
WORKOS_API_KEY=sk_...
WORKOS_CLIENT_ID=client_...
```

Configure the local callback in the WorkOS application as:

```text
http://localhost:8000/auth/callback/
```

The callback creates or updates the matching Django user and stores its local
user ID in the session. It deliberately does **not** grant access to any forestry
process. Staff must create a `ProcessMembership` in the Django backoffice or use
the demo-data command below.

Logout is POST-only and portal sessions use OAuth state validation, session-key
rotation, HTTP-only cookies and SameSite protection.

## Portal demo data

Create an idempotent dataset for the email address used with AuthKit:

```bash
uv run python manage.py seed_portal_demo --email you@example.com
```

The command creates:

- a local landlord user and internal process manager;
- one managed forestry process and membership;
- private demonstration documents and parcel photographs;
- historical interventions and planned operations;
- a sample message thread.

Generated private files are written under `private-media/`, which is gitignored.
Running the command again updates or reuses the same demonstration records.

## Administration model

- Wagtail at `/admin/` owns the public homepage and editorial articles.
- Django admin at `/django-admin/` owns processes, memberships, documents,
  operations, interventions, messages, notification preferences and access logs.
- AuthKit establishes identity; `ProcessMembership` establishes authorization.
- Non-staff portal users see only active processes to which they belong. Staff
  users can inspect all active processes.

## Configuration

Production reads the following environment variables:

| Variable | Required | Purpose |
|---|---:|---|
| `DJANGO_SECRET_KEY` | Yes | Django cryptographic secret |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated allowed hostnames |
| `WORKOS_API_KEY` | For portal login | WorkOS API credential |
| `WORKOS_CLIENT_ID` | For portal login | AuthKit client identifier |
| `DEFAULT_FROM_EMAIL` | No | Notification sender identity |
| `DJANGO_SECURE_SSL_REDIRECT` | No | HTTPS redirect; defaults to `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | No | HSTS duration; defaults to one year |

Settings modules:

| Module | Used by | Purpose |
|---|---|---|
| `antarr_demo.settings.dev` | `manage.py`, tests | Local development defaults |
| `antarr_demo.settings.production` | WSGI and Docker | Hardened production settings |
| `antarr_demo.settings.local` | Optional import | Gitignored machine overrides |

## Development and testing

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

The current suite covers Wagtail rendering, authentication failure and logout
behavior, tenant isolation, portal messaging, private signed downloads, access
history and transactional notification delivery.

Behavioral tests follow the seams documented in [`CONTEXT.md`](CONTEXT.md):
authentication routes, portal routes, private storage, notification-producing
model events and rendered Wagtail pages. New behavior should be developed in
small red → green vertical slices.

## Docker

Build and run the production settings locally:

```bash
docker build -t antarr-demo .
docker run --rm -p 8000:8000 \
  -e DJANGO_SECRET_KEY='replace-with-a-real-secret' \
  -e DJANGO_ALLOWED_HOSTS='localhost' \
  -e WORKOS_API_KEY='sk_...' \
  -e WORKOS_CLIENT_ID='client_...' \
  antarr-demo
```

The container runs migrations at startup and serves the application with
Gunicorn. That is convenient for the demo but should be replaced by a dedicated
release/migration step in a production platform.

## Security and data handling

- Every portal read and mutation is scoped through the authenticated user's
  active process access.
- AuthKit identities are linked to local users without automatically granting
  process membership.
- OAuth callbacks validate one-time state before contacting WorkOS.
- Sensitive files live outside public media storage. Signed links expire after
  15 minutes, reject path traversal and require current process access.
- Document requests, downloads and photograph views create access-log records.
- Production enables HTTPS redirects, HSTS, secure cookies, MIME sniffing
  protection and clickjacking protection.
- Notification email is queued only after a successful database commit and
  respects member and per-process preferences.

## Current production gaps

This repository is a functional application demo, not a complete production
deployment. Before production use:

- replace SQLite with a managed production database and configure Django for it;
- replace `PrivateObjectStorage` with an S3-compatible private bucket adapter;
- configure a real transactional email backend;
- move migrations out of the container startup command;
- provide persistent, independently backed-up database and object storage;
- define monitoring, retention and recovery procedures.

`DATABASE_URL` is shown as a deployment placeholder in `.env.example`, but the
current settings do not parse it automatically; database configuration must be
added explicitly or supplied through `settings/local.py`.

## Technology stack

| Package | Version |
|---|---|
| Python | 3.12+ |
| Django | 6.x |
| Wagtail | 7.3.x |
| WorkOS SDK | 9.1+ |
| pytest | 9.1+ |
| Ruff | 0.15+ |
