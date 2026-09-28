from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_student
from app.models.user import User

router = APIRouter(prefix="/student", tags=["student"])
templates = Jinja2Templates(directory="app/templates")


def _datetimeformat(value, fmt="%d %b %Y, %I:%M %p"):
    if value is None:
        return "—"
    return value.strftime(fmt)

templates.env.filters["datetimeformat"] = _datetimeformat


@router.get("/dashboard", response_class=HTMLResponse, name="student.dashboard")
async def dashboard(request: Request, current_user: User = Depends(require_student), db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("student/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": {"available_count": 0, "registered_count": 0, "groups_formed_count": 0},
        "attention_items": [],
        "upcoming_activities": [],
    })


@router.get("/activities", response_class=HTMLResponse, name="student.activities")
async def activities(request: Request, current_user: User = Depends(require_student)):
    return templates.TemplateResponse("student/activities.html", {
        "request": request, "current_user": current_user, "activities": [], "search_query": "",
    })


@router.get("/activities/{activity_id}", response_class=HTMLResponse, name="student.activity_detail")
async def activity_detail(activity_id: int, request: Request, current_user: User = Depends(require_student)):
    return templates.TemplateResponse("student/activity_detail.html", {
        "request": request, "current_user": current_user, "activity": None,
    })


@router.get("/my-registrations", response_class=HTMLResponse, name="student.my_registrations")
async def my_registrations(request: Request, current_user: User = Depends(require_student)):
    return templates.TemplateResponse("student/my_registrations.html", {
        "request": request, "current_user": current_user, "registrations": [],
    })


@router.get("/my-groups", response_class=HTMLResponse, name="student.my_groups")
async def my_groups(request: Request, current_user: User = Depends(require_student)):
    return templates.TemplateResponse("student/my_groups.html", {
        "request": request, "current_user": current_user, "groups": [],
    })


@router.get("/closed-activities", response_class=HTMLResponse, name="student.closed_activities")
async def closed_activities(request: Request, current_user: User = Depends(require_student)):
    return templates.TemplateResponse("student/closed_activities.html", {
        "request": request, "current_user": current_user, "activities": [],
    })


@router.get("/profile", response_class=HTMLResponse, name="student.profile")
async def profile(request: Request, current_user: User = Depends(require_student)):
    return templates.TemplateResponse("student/profile.html", {
        "request": request, "current_user": current_user, "form_errors": None,
    })
