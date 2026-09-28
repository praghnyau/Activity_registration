"""
admin.py — administrator routes.
"""
import uuid
from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services import activity_service as svc
from app.services.auth_service import generate_csrf_token, verify_csrf_token

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _datetimeformat(value, fmt="%d %b %Y, %I:%M %p"):
    if value is None:
        return "—"
    return value.strftime(fmt)

templates.env.filters["datetimeformat"] = _datetimeformat


def _csrf(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return generate_csrf_token(request.session["session_id"])


def _check_csrf(request: Request, token: str) -> bool:
    return verify_csrf_token(token, request.session.get("session_id", ""))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse, name="admin.dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.list_activities_admin(db, page_size=5)
    activities = result["activities"]

    from app.models.activity import ActivityStatus
    from sqlalchemy import select, func
    from app.models.registration import Registration, RegistrationStatus
    from sqlalchemy import and_

    total_result = await db.execute(select(func.count()).select_from(__import__('app.models.activity', fromlist=['Activity']).Activity))
    total_activities = total_result.scalar() or 0

    open_result = await db.execute(
        select(func.count()).where(
            __import__('app.models.activity', fromlist=['Activity']).Activity.status == ActivityStatus.open
        )
    )
    open_count = open_result.scalar() or 0

    reg_result = await db.execute(
        select(func.count()).where(Registration.status == RegistrationStatus.registered)
    )
    total_regs = reg_result.scalar() or 0

    from app.models.activity import Activity
    pending_result = await db.execute(
        select(func.count()).where(Activity.status == ActivityStatus.registration_closed)
    )
    pending_formation = pending_result.scalar() or 0

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": {
            "total_activities": total_activities,
            "open_activities_count": open_count,
            "total_registrations_count": total_regs,
            "pending_group_formation_count": pending_formation,
        },
        "attention_items": [],
        "recent_activities": activities,
    })


# ── Manage Activities ─────────────────────────────────────────────────────────

@router.get("/activities", response_class=HTMLResponse, name="admin.manage_activities")
async def manage_activities(
    request: Request,
    q: str = Query(default=""),
    status: str = Query(default=""),
    page: int = Query(default=1),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.list_activities_admin(db, q=q, status=status, page=page)
    return templates.TemplateResponse("admin/manage_activities.html", {
        "request": request,
        "current_user": current_user,
        "activities": result["activities"],
        "pagination": result["pagination"],
        "filters": {"q": q, "status": status},
        "csrf_token": _csrf(request),
    })


# ── Create / Edit Activity ────────────────────────────────────────────────────

@router.get("/activities/new", response_class=HTMLResponse, name="admin.activity_form")
async def activity_form_get(
    request: Request,
    activity_id: int = Query(default=None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    activity = None
    if activity_id:
        activity = await svc.get_activity_by_id(db, activity_id)

    return templates.TemplateResponse("admin/activity_form.html", {
        "request": request,
        "current_user": current_user,
        "activity": activity,
        "form_errors": None,
        "csrf_token": _csrf(request),
    })


@router.post("/activities/new", response_class=HTMLResponse, name="admin.activity_form_post")
async def activity_form_post(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    data = dict(form)

    def render_form(errors, activity=None):
        return templates.TemplateResponse("admin/activity_form.html", {
            "request": request,
            "current_user": current_user,
            "activity": activity,
            "form_errors": errors,
            "csrf_token": _csrf(request),
        }, status_code=400)

    if not _check_csrf(request, data.get("csrf_token", "")):
        return render_form({"general": "Invalid request. Please try again."})

    errors = svc.validate_activity_form(data)
    if errors:
        errors["title_value"] = data.get("title", "")
        return render_form(errors)

    activity_id = data.get("activity_id")

    if activity_id:
        # Edit existing activity
        activity = await svc.get_activity_by_id(db, int(activity_id))
        if not activity:
            return render_form({"general": "Activity not found."})
        await svc.update_activity(db, activity, data)
        return RedirectResponse(url=f"/admin/activities?updated=1", status_code=303)
    else:
        # Create new activity
        await svc.create_activity(db, data, current_user)
        return RedirectResponse(url="/admin/activities?created=1", status_code=303)


# ── Status actions ────────────────────────────────────────────────────────────

@router.post("/activities/{activity_id}/publish", name="admin.publish_activity")
async def publish_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if not _check_csrf(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/admin/activities", status_code=303)

    activity = await svc.get_activity_by_id(db, activity_id)
    if activity:
        await svc.publish_activity(db, activity)
    return RedirectResponse(url="/admin/activities", status_code=303)


@router.post("/activities/{activity_id}/close-registration", name="admin.close_registration")
async def close_registration(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if not _check_csrf(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/admin/activities", status_code=303)

    activity = await svc.get_activity_by_id(db, activity_id)
    if activity:
        await svc.close_registration(db, activity)
    return RedirectResponse(url="/admin/activities", status_code=303)


@router.post("/activities/{activity_id}/cancel", name="admin.cancel_activity")
async def cancel_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if not _check_csrf(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/admin/activities", status_code=303)

    activity = await svc.get_activity_by_id(db, activity_id)
    if activity:
        await svc.cancel_activity(db, activity)
    return RedirectResponse(url="/admin/activities", status_code=303)


@router.post("/activities/{activity_id}/complete", name="admin.complete_activity")
async def complete_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if not _check_csrf(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/admin/activities", status_code=303)

    activity = await svc.get_activity_by_id(db, activity_id)
    if activity:
        await svc.complete_activity(db, activity)
    return RedirectResponse(url="/admin/activities", status_code=303)


# ── Stub routes ───────────────────────────────────────────────────────────────

@router.get("/group-formation", response_class=HTMLResponse, name="admin.group_formation")
async def group_formation(
    request: Request,
    current_user: User = Depends(require_admin),
):
    return templates.TemplateResponse("admin/group_formation.html", {
        "request": request,
        "current_user": current_user,
        "activity": None,
        "proposed_groups": [],
        "remainder_students": [],
    })


@router.get("/group-history", response_class=HTMLResponse, name="admin.group_history")
async def group_history(
    request: Request,
    current_user: User = Depends(require_admin),
):
    return templates.TemplateResponse("admin/group_history.html", {
        "request": request,
        "current_user": current_user,
        "groups": [],
    })
