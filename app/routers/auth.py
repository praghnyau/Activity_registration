from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import verify_password, is_valid_email_for_login
from app.templating import templates, add_flash, check_csrf

router = APIRouter(tags=["auth"])


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
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"next_url": _safe_next_url(next), "form_errors": None},
    )


@router.post("/login", response_class=HTMLResponse, name="auth.login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    def render_error(general=None, email_err=None, password_err=None):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "next_url": _safe_next_url(next),
                "form_errors": {
                    "general": general,
                    "email": email_err,
                    "email_value": email,
                    "password": password_err,
                },
            },
            status_code=400,
        )

    if not check_csrf(request, csrf_token):
        return render_error(general="That form expired. Reload the page and try again.")
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

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["user_role"] = user.role.value
    request.session["user_name"] = user.name
    request.session["session_version"] = user.session_version
    add_flash(request, f"Welcome back, {user.name.split()[0]}.", "success")

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
