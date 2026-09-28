"""
templating.py — shared Jinja2 setup for every router.

Centralises the pieces that were previously duplicated in each router:
- one Jinja2 environment with the shared `datetimeformat` filter
- CSRF token generation and verification
- flash messages that survive a Post/Redirect/Get
- the global variables required by docs/template-contract.md section 1

Routers import `templates`, `add_flash`, and `csrf_token` from here instead of
building their own.
"""
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.services.auth_service import generate_csrf_token, verify_csrf_token

IST = ZoneInfo("Asia/Kolkata")

FLASH_SESSION_KEY = "_flashes"


# ── Shared date filter ────────────────────────────────────────────────────────

def datetimeformat(value, fmt="%d %b %Y, %I:%M %p") -> str:
    """Single date format used by every template (template-contract.md rule 5)."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.astimezone(IST).strftime(fmt)
    return str(value)


# ── CSRF ──────────────────────────────────────────────────────────────────────

def csrf_token(request: Request) -> str:
    """Return this session's CSRF token, creating the session id if needed."""
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return generate_csrf_token(request.session["session_id"])


def check_csrf(request: Request, token: str) -> bool:
    return verify_csrf_token(token, request.session.get("session_id", ""))


# ── Flash messages ────────────────────────────────────────────────────────────

def add_flash(request: Request, text: str, category: str = "info") -> None:
    """Queue a message for the next rendered page.

    Stored in the session cookie so it survives the redirect that follows a
    form submission (Post/Redirect/Get).
    """
    flashes = request.session.get(FLASH_SESSION_KEY, [])
    flashes.append({"category": category, "text": text})
    request.session[FLASH_SESSION_KEY] = flashes


def consume_flashes(request: Request) -> list[dict]:
    """Read and clear queued messages. Called once per rendered page."""
    return list(request.session.pop(FLASH_SESSION_KEY, []))


# ── Global template variables ─────────────────────────────────────────────────

def page_globals(request: Request | None) -> dict:
    """
    The globals required on every page by template-contract.md section 1.

    A route that already supplied a value keeps it — these are defaults only.
    `current_user` is left to the route, since resolving it needs a database
    session; the login page genuinely has none.
    """
    return {
        "flashed_messages": consume_flashes(request) if request is not None else [],
        "csrf_token": csrf_token(request) if request is not None else "",
        "active_nav": "",
        "page_error": None,
    }


def _split_args(args: tuple) -> tuple[Request | None, str, dict]:
    """
    Normalise both TemplateResponse call styles to (request, name, context).

    Supports the modern (request, name, context) form and the legacy
    (name, {"request": request, ...}) form still used across the routers.
    """
    if len(args) >= 3 and isinstance(args[0], Request):
        return args[0], args[1], dict(args[2] or {})
    name, context = args[0], args[1]
    context = dict(context or {})
    request = context.get("request")
    return request, name, context


class AppTemplates(Jinja2Templates):
    """Jinja2Templates that injects the contract's global variables."""

    def TemplateResponse(self, *args, **kwargs):  # noqa: N802 - matches base class
        request, name, context = _split_args(args)
        for key, value in page_globals(request).items():
            context.setdefault(key, value)

        if request is None:
            context.pop("request", None)
            return super().TemplateResponse(name, context, **kwargs)
        return super().TemplateResponse(request, name, context, **kwargs)


templates = AppTemplates(directory="app/templates")
templates.env.filters["datetimeformat"] = datetimeformat
