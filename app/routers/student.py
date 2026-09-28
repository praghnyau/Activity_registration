"""
student.py — student-facing routes.
"""
import uuid
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import require_student
from app.models.user import User
from app.models.activity import ActivityStatus
from app.models.registration import Registration, RegistrationStatus
from app.services import activity_service as svc
from app.services.auth_service import generate_csrf_token

router = APIRouter(prefix="/student", tags=["student"])
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


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse, name="student.dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, and_

    # Count open activities
    from app.models.activity import Activity
    open_result = await db.execute(
        select(func.count()).where(
            Activity.status.in_([ActivityStatus.open, ActivityStatus.full])
        )
    )
    available_count = open_result.scalar() or 0

    # Count active registrations for this student
    reg_result = await db.execute(
        select(func.count()).where(
            and_(
                Registration.student_id == current_user.id,
                Registration.status == RegistrationStatus.registered,
            )
        )
    )
    registered_count = reg_result.scalar() or 0

    # Count finalised groups for this student
    from app.models.group_member import GroupMember
    from app.models.group import Group, GroupStatus
    groups_result = await db.execute(
        select(func.count()).join(
            Group, Group.id == GroupMember.group_id
        ).where(
            and_(
                GroupMember.student_id == current_user.id,
                Group.status == GroupStatus.finalised,
            )
        )
    )
    groups_formed_count = groups_result.scalar() or 0

    # Upcoming open activities (top 6)
    upcoming_result = await db.execute(
        select(Activity)
        .where(Activity.status.in_([ActivityStatus.open, ActivityStatus.full]))
        .order_by(Activity.starts_at.asc())
        .limit(6)
    )
    upcoming = upcoming_result.scalars().all()
    for a in upcoming:
        a.registered_count = await svc.get_registration_count(db, a.id)
        a.display_status = a.status.value

    return templates.TemplateResponse("student/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": {
            "available_count": available_count,
            "registered_count": registered_count,
            "groups_formed_count": groups_formed_count,
        },
        "attention_items": [],
        "upcoming_activities": upcoming,
    })


# ── Available Activities ──────────────────────────────────────────────────────

@router.get("/activities", response_class=HTMLResponse, name="student.activities")
async def activities(
    request: Request,
    q: str = Query(default=""),
    date_from: str = Query(default=""),
    availability: str = Query(default=""),
    page: int = Query(default=1),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.list_activities_student(
        db, q=q, date_from=date_from, availability=availability, page=page
    )
    return templates.TemplateResponse("student/activities.html", {
        "request": request,
        "current_user": current_user,
        "activities": result["activities"],
        "pagination": result["pagination"],
        "filters": {"q": q, "date_from": date_from, "availability": availability},
    })


# ── Activity Detail ───────────────────────────────────────────────────────────

@router.get("/activities/{activity_id}", response_class=HTMLResponse, name="student.activity_detail")
async def activity_detail(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")

    activity = await svc.get_activity_by_id(db, activity_id)
    if not activity:
        return templates.TemplateResponse("student/activities.html", {
            "request": request,
            "current_user": current_user,
            "activities": [],
            "pagination": {"page": 1, "total_pages": 1, "total": 0},
            "filters": {},
        }, status_code=404)

    activity.registered_count = await svc.get_registration_count(db, activity.id)
    activity.display_status = activity.status.value

    # Check if student is already registered
    reg_result = await db.execute(
        select(Registration).where(
            Registration.student_id == current_user.id,
            Registration.activity_id == activity_id,
        )
    )
    my_registration = reg_result.scalar_one_or_none()

    now = datetime.now(tz=IST)
    deadline_passed = now > activity.registration_deadline.astimezone(IST)

    # Compute can_register and can_withdraw flags
    can_register = False
    register_blocked_reason = None
    can_withdraw = False
    withdraw_blocked_reason = None

    if my_registration and my_registration.status == RegistrationStatus.registered:
        # Already registered — show withdraw option
        if deadline_passed:
            can_withdraw = False
            withdraw_blocked_reason = "The registration deadline has passed. Withdrawals are no longer accepted."
        else:
            can_withdraw = True
    elif my_registration and my_registration.status == RegistrationStatus.withdrawn:
        # Previously withdrawn — can re-register if deadline not passed
        if deadline_passed:
            can_register = False
            register_blocked_reason = "Registration deadline has passed."
        elif activity.status not in (ActivityStatus.open, ActivityStatus.full):
            can_register = False
            register_blocked_reason = "Registration is not open for this activity."
        else:
            can_register = True
    elif not my_registration:
        # Never registered
        if deadline_passed:
            can_register = False
            register_blocked_reason = "Registration deadline has passed."
        elif activity.status == ActivityStatus.open:
            can_register = True
        elif activity.status == ActivityStatus.full:
            can_register = False
            register_blocked_reason = "This activity is full."
        else:
            can_register = False
            register_blocked_reason = "Registration is not open for this activity."

    # Attach group info to my_registration if it exists
    if my_registration:
        my_registration.group_status = "not_assigned"
        my_registration.group_label = None

        from app.models.group_member import GroupMember
        from app.models.group import Group, GroupStatus
        gm_result = await db.execute(
            select(GroupMember, Group)
            .join(Group, Group.id == GroupMember.group_id)
            .where(
                GroupMember.student_id == current_user.id,
                Group.activity_id == activity_id,
            )
        )
        row = gm_result.first()
        if row:
            gm, group = row
            if group.status == GroupStatus.finalised:
                my_registration.group_status = "assigned"
                my_registration.group_label = group.label
            else:
                my_registration.group_status = "pending"

    return templates.TemplateResponse("student/activity_detail.html", {
        "request": request,
        "current_user": current_user,
        "activity": activity,
        "resources": activity.resources,
        "my_registration": my_registration,
        "can_register": can_register,
        "register_blocked_reason": register_blocked_reason,
        "can_withdraw": can_withdraw,
        "withdraw_blocked_reason": withdraw_blocked_reason,
        "prefill": {"name": current_user.name, "email": current_user.email},
        "csrf_token": _csrf(request),
    })


# ── Stub routes ───────────────────────────────────────────────────────────────

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


# Register/withdraw stubs — Phase 3
@router.post("/activities/{activity_id}/register", name="student.register")
async def register(activity_id: int, request: Request, current_user: User = Depends(require_student)):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/student/activities/{activity_id}", status_code=303)


@router.post("/registrations/{registration_id}/withdraw", name="student.withdraw")
async def withdraw(registration_id: int, request: Request, current_user: User = Depends(require_student)):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/student/my-registrations", status_code=303)
