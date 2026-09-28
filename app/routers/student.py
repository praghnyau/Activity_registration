"""
student.py — student-facing routes.
"""
from dataclasses import dataclass
from types import SimpleNamespace
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_student
from app.models.group import Group, GroupStatus
from app.models.group_member import GroupMember
from app.models.user import User
from app.models.activity import Activity, ActivityStatus
from app.models.registration import Registration, RegistrationStatus
from app.services import activity_service as svc
from app.services import auth_service as auth_svc
from app.services import group_service as group_svc
from app.services import registration_service as reg_svc
from app.templating import templates, add_flash, check_csrf

router = APIRouter(prefix="/student", tags=["student"])

IST = ZoneInfo("Asia/Kolkata")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse, name="student.dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, and_

    # Count open activities
    open_result = await db.execute(
        select(func.count())
        .select_from(Activity)
        .where(Activity.status.in_([ActivityStatus.open, ActivityStatus.full]))
    )
    available_count = open_result.scalar() or 0

    # Count active registrations for this student
    reg_result = await db.execute(
        select(func.count())
        .select_from(Registration)
        .where(
            and_(
                Registration.student_id == current_user.id,
                Registration.status == RegistrationStatus.registered,
            )
        )
    )
    registered_count = reg_result.scalar() or 0

    # Count finalised groups for this student
    groups_result = await db.execute(
        select(func.count())
        .select_from(GroupMember)
        .join(Group, Group.id == GroupMember.group_id)
        .where(
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

    # Registrations that need the student to act: not yet grouped, or in a group
    # that an administrator has disrupted. Left empty since Phase 3.
    attention_regs = await db.execute(
        select(Registration)
        .options(selectinload(Registration.activity))
        .where(
            Registration.student_id == current_user.id,
            Registration.status == RegistrationStatus.registered,
        )
        .order_by(Registration.id)
    )
    attention = []
    for reg in attention_regs.scalars().all():
        group_status, _label = await group_svc.group_status_for_registration(db, reg)
        if group_status not in ("not_yet_formed", "awaiting_decision"):
            continue
        activity = reg.activity
        if activity.status in (ActivityStatus.cancelled,):
            continue
        attention.append(
            SimpleNamespace(
                activity_id=activity.id,
                activity_title=activity.title,
                starts_at=activity.starts_at,
                registration_status=reg.status.value,
                group_status=group_status,
            )
        )

    return templates.TemplateResponse(
        request,
        "student/dashboard.html",
        {
            "current_user": current_user,
            "stats": {
                "available_count": available_count,
                "registered_count": registered_count,
                "groups_formed_count": groups_formed_count,
            },
            "attention_items": attention,
            "upcoming_activities": upcoming,
            "active_nav": "dashboard",
        },
    )


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
    return templates.TemplateResponse(
        request,
        "student/activities.html",
        {
            "current_user": current_user,
            "activities": result["activities"],
            "pagination": result["pagination"],
            "filters": {"q": q, "date_from": date_from, "availability": availability},
            "active_nav": "activities",
        },
    )


# ── Activity Detail ───────────────────────────────────────────────────────────

@router.get("/activities/{activity_id}", response_class=HTMLResponse, name="student.activity_detail")
async def activity_detail(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    activity = await svc.get_activity_by_id(db, activity_id)
    if not activity:
        return templates.TemplateResponse(
            request,
            "student/activities.html",
            {
                "current_user": current_user,
                "activities": [],
                "pagination": {"page": 1, "total_pages": 1, "total": 0, "total_items": 0},
                "filters": {"q": "", "date_from": "", "availability": ""},
                "active_nav": "activities",
                "page_error": {
                    "code": "404",
                    "message": "That activity could not be found.",
                },
            },
            status_code=404,
        )

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

    # Attach group info to my_registration if it exists. Group status keys are
    # the ones defined in template-contract.md. A proposal that is not yet
    # finalised reports `not_yet_formed` — students must never see a proposal.
    if my_registration:
        if my_registration.status != RegistrationStatus.registered:
            my_registration.group_status = "no_group"
        else:
            my_registration.group_status = "not_yet_formed"

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
                _, group = row
                if group.status == GroupStatus.finalised:
                    my_registration.group_status = "group_formed"
                    my_registration.group_label = group.label

    return templates.TemplateResponse(
        request,
        "student/activity_detail.html",
        {
            "current_user": current_user,
            "activity": activity,
            "resources": activity.resources,
            "my_registration": my_registration,
            "can_register": can_register,
            "register_blocked_reason": register_blocked_reason,
            "can_withdraw": can_withdraw,
            "withdraw_blocked_reason": withdraw_blocked_reason,
            "prefill": {"name": current_user.name, "email": current_user.email},
            "active_nav": "activities",
        },
    )


# ── Registration ──────────────────────────────────────────────────────────────

@router.post("/activities/{activity_id}/register", name="student.register")
async def register(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if not check_csrf(request, form.get("csrf_token", "")):
        add_flash(request, "That form expired. Reload the page and try again.", "error")
        return RedirectResponse(
            url=f"/student/activities/{activity_id}", status_code=303
        )

    registration, error = await reg_svc.register_student(
        db, student_id=current_user.id, activity_id=activity_id
    )

    if error:
        add_flash(request, error, "error")
        return RedirectResponse(
            url=f"/student/activities/{activity_id}", status_code=303
        )

    add_flash(request, "You are registered for this activity.", "success")
    return RedirectResponse(
        url=f"/student/registrations/{registration.id}/confirmation", status_code=303
    )


@router.post("/registrations/{registration_id}/withdraw", name="student.withdraw")
async def withdraw(
    registration_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if not check_csrf(request, form.get("csrf_token", "")):
        add_flash(request, "That form expired. Reload the page and try again.", "error")
        return RedirectResponse(url="/student/my-registrations", status_code=303)

    success, error = await reg_svc.withdraw_student(
        db, registration_id=registration_id, student_id=current_user.id
    )

    if not success:
        add_flash(request, error, "error")
    else:
        add_flash(request, "You have withdrawn from this activity.", "success")

    return RedirectResponse(url="/student/my-registrations", status_code=303)


@router.get(
    "/registrations/{registration_id}/confirmation",
    response_class=HTMLResponse,
    name="student.registration_confirm",
)
async def registration_confirm(
    registration_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.activity))
        .where(
            Registration.id == registration_id,
            Registration.student_id == current_user.id,
        )
    )
    registration = result.scalar_one_or_none()

    if not registration:
        return templates.TemplateResponse(
            request,
            "student/my_registrations.html",
            {
                "current_user": current_user,
                "registrations": [],
                "filters": {"q": ""},
                "pagination": {"page": 1, "total_pages": 1, "total": 0, "total_items": 0},
                "active_nav": "my_registrations",
                "page_error": {"code": "404", "message": "Registration not found."},
            },
            status_code=404,
        )

    activity = registration.activity

    # A group is only ever reported as formed once it has been finalised.
    group_status = "not_yet_formed"
    if registration.status != RegistrationStatus.registered:
        group_status = "no_group"
    else:
        gm_result = await db.execute(
            select(GroupMember, Group)
            .join(Group, Group.id == GroupMember.group_id)
            .where(
                GroupMember.student_id == current_user.id,
                Group.activity_id == activity.id,
                Group.status == GroupStatus.finalised,
            )
        )
        if gm_result.first():
            group_status = "group_formed"

    return templates.TemplateResponse(
        request,
        "student/registration_confirm.html",
        {
            "current_user": current_user,
            "registration": registration,
            "activity": activity,
            "group_status": group_status,
            "active_nav": "my_registrations",
        },
    )


# ── My Registrations ──────────────────────────────────────────────────────────

@router.get("/my-registrations", response_class=HTMLResponse, name="student.my_registrations")
async def my_registrations(
    request: Request,
    q: str = Query(default=""),
    page: int = Query(default=1),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await reg_svc.list_my_registrations(
        db, student_id=current_user.id, q=q, page=page
    )
    return templates.TemplateResponse(
        request,
        "student/my_registrations.html",
        {
            "current_user": current_user,
            "registrations": result["registrations"],
            "filters": {"q": q},
            "pagination": result["pagination"],
            "active_nav": "my_registrations",
        },
    )


# ── Stub routes ───────────────────────────────────────────────────────────────

@dataclass
class _GroupView:
    """Shape the student My Groups template expects for one group."""

    activity: Activity
    group_label: str
    group_size: int
    member_count: int
    status: str
    members: list[str]
    instructions: str | None = None


@router.get("/my-groups", response_class=HTMLResponse, name="student.my_groups")
async def my_groups(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    # Only finalised groups are visible: a proposal must not leak early.
    # A student removed by an administrator keeps the GroupMember row as an audit
    # trail, so their withdrawn registration is what excludes the group here.
    rows = await db.execute(
        select(Group, Activity)
        .join(Activity, Activity.id == Group.activity_id)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .join(
            Registration,
            (Registration.student_id == GroupMember.student_id)
            & (Registration.activity_id == Group.activity_id),
        )
        .where(
            Group.status == GroupStatus.finalised,
            GroupMember.student_id == current_user.id,
            Registration.status == RegistrationStatus.registered,
        )
        .order_by(Activity.starts_at)
    )

    views = []
    for group, activity in rows.unique().all():
        names = await group_svc.active_member_names(db, group)
        views.append(
            _GroupView(
                activity=activity,
                group_label=group.label,
                group_size=activity.group_size,
                member_count=len(names),
                status=("awaiting_decision" if await group_svc.group_is_disrupted(db, group)
                        else "group_formed"),
                members=names,
                instructions=getattr(activity, "instructions", None),
            )
        )

    return templates.TemplateResponse(
        request,
        "student/my_groups.html",
        {"current_user": current_user, "groups": views, "active_nav": "my_groups"},
    )


@router.get("/closed-activities", response_class=HTMLResponse, name="student.closed_activities")
async def closed_activities(
    request: Request,
    q: str = Query(default=""),
    date_from: str = Query(default=""),
    closure_reason: str = Query(default=""),
    page: int = Query(default=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    result = await svc.list_closed_activities(
        db, q=q, date_from=date_from, closure_reason=closure_reason, page=page
    )
    return templates.TemplateResponse(
        request,
        "student/closed_activities.html",
        {
            "current_user": current_user,
            "activities": result["activities"],
            "filters": {"q": q, "date_from": date_from, "closure_reason": closure_reason},
            "pagination": result["pagination"],
            "active_nav": "closed_activities",
        },
    )


@dataclass
class _ProfileView:
    """Shape the profile template expects; `role` must not be the raw enum."""

    name: str
    email: str
    student_id: str | None
    role: str


def _profile_context(current_user: User, password_form_errors=None) -> dict:
    return {
        "current_user": current_user,
        "user": _ProfileView(
            name=current_user.name,
            email=current_user.email,
            student_id=current_user.student_id,
            role=current_user.role.value,
        ),
        "password_form_errors": password_form_errors,
    }


@router.get("/profile", response_class=HTMLResponse, name="student.profile")
async def profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    return templates.TemplateResponse(
        request,
        "student/profile.html",
        {**_profile_context(current_user), "active_nav": "profile"},
    )


@router.post("/profile/password", name="student.change_password")
async def change_password(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    form = await request.form()
    if not check_csrf(request, form.get("csrf_token", "")):
        add_flash(request, "That form expired. Reload the page and try again.", "error")
        return RedirectResponse(url="/student/profile", status_code=303)

    ok, errors, new_version = await auth_svc.change_password(
        db,
        current_user,
        form.get("current_password", ""),
        form.get("new_password", ""),
        form.get("confirm_password", ""),
    )

    if not ok:
        return templates.TemplateResponse(
            request,
            "student/profile.html",
            {**_profile_context(current_user, errors), "active_nav": "profile"},
        )

    # Keep this session alive; the version bump ends every other one.
    request.session["session_version"] = new_version
    add_flash(request, "Your password has been changed. Other sessions were signed out.", "success")
    return RedirectResponse(url="/student/profile", status_code=303)
