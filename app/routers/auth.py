from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import verify_password, generate_csrf_token, verify_csrf_token, is_valid_email_for_login

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def _get_or_create_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]


def _safe_next_url(next_url: str | None) -> str | None:
    if not next_url:
        return None
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return None


@router.get("/login", response_class=HTMLResponse, name="auth.login_page")
async def login_page(request: Request, next: str | None = None):
    if request.session.get("user_id"):
        role = request.session.get("user_role")
        if role == UserRole.administrator:
            return RedirectResponse(url="/admin/dashboard", status_code=302)
        return RedirectResponse(url="/student/dashboard", status_code=302)
    session_id = _get_or_create_session_id(request)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "csrf_token": generate_csrf_token(session_id),
        "next_url": _safe_next_url(next),
        "form_errors": None,
    })


@router.post("/login", response_class=HTMLResponse, name="auth.login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    session_id = _get_or_create_session_id(request)

    def render_error(general=None, email_err=None, password_err=None):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "csrf_token": generate_csrf_token(session_id),
            "next_url": _safe_next_url(next),
            "form_errors": {"general": general, "email": email_err, "email_value": email, "password": password_err},
        }, status_code=400)

    if not verify_csrf_token(csrf_token, session_id):
        return render_error(general="Invalid request. Please try again.")
    if not email or not email.strip():
        return render_error(email_err="Email is required.")
    if not password:
        return render_error(password_err="Password is required.")
    valid, email_err = is_valid_email_for_login(email)
    if not valid:
        return render_error(email_err=email_err)

    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return render_error(general="Incorrect email or password.")

    request.session["user_id"] = user.id
    request.session["user_role"] = user.role.value
    request.session["user_name"] = user.name

    safe_next = _safe_next_url(next)
    if safe_next:
        return RedirectResponse(url=safe_next, status_code=303)
    if user.role == UserRole.administrator:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/student/dashboard", status_code=303)


@router.post("/logout", name="auth.logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
