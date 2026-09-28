# Stack

## Activity Registration and Group Formation System

---

## Technology choices

| Layer | Technology | Notes |
|---|---|---|
| Backend language | Python 3.11+ | |
| Web framework | FastAPI | Async, automatic OpenAPI docs, Pydantic validation |
| Templates | Jinja2 | Server-rendered via `fastapi.templating.Jinja2Templates` |
| Database | PostgreSQL 15+ | Transactions for all-or-nothing group saves |
| ORM | SQLAlchemy 2.x (async) | Use `asyncpg` as the driver |
| Migrations | Alembic | All schema changes go through migration files |
| Password hashing | Passlib + bcrypt | `passlib[bcrypt]` — never store plain text passwords |
| Session management | Starlette sessions (via `itsdangerous`) | Signed, HTTP-only cookie |
| Environment config | python-dotenv | `.env` file for all secrets and config |
| ASGI server | Uvicorn | Local dev and production |
| Frontend | HTML, CSS, JavaScript | No framework |

---

## Why these choices

**FastAPI over Flask** — async support, Pydantic validation built in, automatic OpenAPI docs, active maintenance. Jinja2 templates work identically.

**PostgreSQL over SQLite** — the all-or-nothing group save requires reliable transactions. PostgreSQL also handles the concurrent registration race condition correctly with row-level locking.

**SQLAlchemy async** — integrates with FastAPI's async model. Avoids blocking the event loop on database queries.

**Session cookies over JWT** — server-rendered Jinja pages are simpler and safer with session cookies. JWT tokens only make sense with a separate JS frontend or mobile app.

**No CSS framework** — the design is specific enough (exact hex values, custom status colours, burgundy/cream identity) that a framework would fight the design more than help. All colours are CSS custom properties, making theme switching clean.

---

## Project structure

```
Activity_registration/
├── app/
│   ├── main.py               # FastAPI app, router registration, startup
│   ├── config.py             # Settings loaded from .env
│   ├── database.py           # Async SQLAlchemy engine and session
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── activity.py
│   │   ├── resource.py
│   │   ├── registration.py
│   │   ├── group.py
│   │   └── group_member.py
│   ├── routers/              # FastAPI routers
│   │   ├── auth.py
│   │   ├── student.py
│   │   └── admin.py
│   ├── services/             # Business logic
│   │   ├── auth_service.py
│   │   ├── activity_service.py
│   │   ├── registration_service.py
│   │   └── group_formation.py   # Formation algorithm in its own module
│   ├── schemas/              # Pydantic schemas for forms and responses
│   └── templates/            # Jinja2 templates
│       ├── base.html
│       ├── auth/
│       ├── student/
│       └── admin/
├── static/
│   ├── css/
│   │   └── main.css
│   └── js/
│       └── main.js
├── migrations/               # Alembic migrations
│   ├── env.py
│   └── versions/
├── alembic.ini
├── .env                      # Never committed to git
├── .env.example              # Committed — shows required keys with placeholder values
├── requirements.txt
└── README.md
```

---

## Environment variables

All secrets and configuration are stored in `.env`. This file is never committed to git. A `.env.example` file is committed with placeholder values so new developers know what is required.

```env
# .env.example

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/activity_registration

# Session
SESSION_SECRET_KEY=replace-with-a-long-random-string
SESSION_MAX_AGE_SECONDS=3600

# App
DEBUG=false
```

---

## Dependencies

```
# requirements.txt

fastapi==0.115.0
uvicorn[standard]==0.30.6
jinja2==3.1.4
python-multipart==0.0.9

# Database
sqlalchemy[asyncio]==2.0.35
asyncpg==0.30.0
alembic==1.13.3

# Auth
passlib[bcrypt]==1.7.4
itsdangerous==2.2.0

# Config
python-dotenv==1.0.1
```

Pin all versions. Do not use open ranges (`>=`) in production dependencies.

---

## Local development setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher running locally (or via Docker)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/praghnyau/Activity_registration.git
cd Activity_registration

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the database
createdb activity_registration  # or use psql / pgAdmin

# 5. Set up environment variables
cp .env.example .env
# Edit .env and fill in DATABASE_URL, SESSION_SECRET_KEY

# 6. Run migrations
alembic upgrade head

# 7. Start the development server
uvicorn app.main:app --reload
```

The app runs at `http://localhost:8000`.

FastAPI's automatic docs are available at `http://localhost:8000/docs` in development.

---

## Notes for the backend developer

- The group formation algorithm lives in `app/services/group_formation.py` and is called from the group formation router. Keep the algorithm in its own function so it can be improved later without touching the rest of the app.
- All group saves must use a single database transaction. If any part of the save fails, the entire transaction rolls back. No partial groups should ever be visible.
- Role is read from the database on every request. Never trust the role from the session cookie.
- The `next_url` parameter on login must be validated as an internal path only. An external URL must be rejected to prevent open redirect attacks.
- Form submissions follow Post/Redirect/Get. On success, redirect and flash a message. On failure, re-render the same page with `field_errors`.

---

## Notes for the frontend developer

- All colours are defined as CSS custom properties in one place. A `data-theme` attribute on `<html>` switches between light and dark.
- The theme script that reads `localStorage` and sets `data-theme` must be in `<head>` before any stylesheets, to prevent a flash of the wrong theme.
- Templates receive `can_register`, `can_withdraw`, and `allowed_actions` flags from the backend. Use these flags to show or hide buttons. Do not recalculate eligibility in the template.
- `flashed_messages` is a list passed to every template. The base layout renders these as notification banners.
- Dates are passed as datetime objects. Use a shared Jinja filter to format them consistently.
