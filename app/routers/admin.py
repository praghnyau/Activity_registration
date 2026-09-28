from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _datetimeformat(value, fmt="%d %b %Y, %I:%M %p"):
    if value is None:
        return "—"
    return value.strftime(fmt)

templates.env.filters["datetimeformat"] = _datetimeformat


@router.get("/dashboard", response_class=HTMLResponse, name="admin.dashboard")
async def dashboard(request: Request, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": {"total_activities": 0, "open_activities_count": 0, "total_registrations_count": 0, "pending_group_formation_count": 0},
        "attention_items": [],
        "recent_activities": [],
    })


@router.get("/activities", response_class=HTMLResponse, name="admin.manage_activities")
async def manage_activities(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/manage_activities.html", {
        "request": request, "current_user": current_user, "activities": [],
    })


@router.get("/activities/new", response_class=HTMLResponse, name="admin.activity_form")
async def activity_form(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/activity_form.html", {
        "request": request, "current_user": current_user, "activity": None, "form_errors": None,
    })


@router.get("/group-formation", response_class=HTMLResponse, name="admin.group_formation")
async def group_formation(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/group_formation.html", {
        "request": request, "current_user": current_user, "activity": None,
        "proposed_groups": [], "remainder_students": [],
    })


@router.get("/group-history", response_class=HTMLResponse, name="admin.group_history")
async def group_history(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/group_history.html", {
        "request": request, "current_user": current_user, "groups": [],
    })
