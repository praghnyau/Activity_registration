"""
admin.py — administrator routes.
"""
from dataclasses import dataclass
from types import SimpleNamespace

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.database import get_db
from app.dependencies import require_admin
from app.models.activity import Activity, ActivityStatus
from app.models.group import Group
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User
from app.services import activity_service as svc
from app.services import group_formation as formation
from app.services import group_service as group_svc
from app.templating import templates, add_flash, check_csrf

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse, name="admin.dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.list_activities_admin(db, page_size=5)
    activities = result["activities"]

    total_result = await db.execute(select(func.count()).select_from(Activity))
    total_activities = total_result.scalar() or 0

    open_result = await db.execute(
        select(func.count())
        .select_from(Activity)
        .where(Activity.status == ActivityStatus.open)
    )
    open_count = open_result.scalar() or 0

    reg_result = await db.execute(
        select(func.count())
        .select_from(Registration)
        .where(Registration.status == RegistrationStatus.registered)
    )
    total_regs = reg_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count())
        .select_from(Activity)
        .where(Activity.status == ActivityStatus.registration_closed)
    )
    pending_formation = pending_result.scalar() or 0

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "current_user": current_user,
            "stats": {
                "total_activities": total_activities,
                "open_activities_count": open_count,
                "total_registrations_count": total_regs,
                "pending_group_formation_count": pending_formation,
            },
            "attention_items": [],
            "recent_activities": activities,
            "active_nav": "dashboard",
        },
    )


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
    return templates.TemplateResponse(
        request,
        "admin/manage_activities.html",
        {
            "current_user": current_user,
            "activities": result["activities"],
            "pagination": result["pagination"],
            "filters": {"q": q, "status": status},
            "active_nav": "manage_activities",
        },
    )


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

    return templates.TemplateResponse(
        request,
        "admin/activity_form.html",
        {
            "current_user": current_user,
            "activity": activity,
            "form_errors": None,
            "active_nav": "manage_activities",
        },
    )


@router.post("/activities/new", response_class=HTMLResponse, name="admin.activity_form_post")
async def activity_form_post(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    data = dict(form)

    def render_form(errors, activity=None):
        return templates.TemplateResponse(
            request,
            "admin/activity_form.html",
            {
                "current_user": current_user,
                "activity": activity,
                "form_errors": errors,
                "active_nav": "manage_activities",
            },
            status_code=400,
        )

    if not check_csrf(request, data.get("csrf_token", "")):
        return render_form(
            {"general": "That form expired. Reload the page and try again."}
        )

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
        add_flash(request, "Activity updated.", "success")
        return RedirectResponse(url="/admin/activities", status_code=303)
    else:
        # Create new activity
        await svc.create_activity(db, data, current_user)
        add_flash(request, "Activity created as a draft.", "success")
        return RedirectResponse(url="/admin/activities", status_code=303)


# ── Status actions ────────────────────────────────────────────────────────────

async def _run_status_action(
    request: Request,
    db: AsyncSession,
    activity_id: int,
    action,
    success_message: str,
):
    """
    Shared body for the publish/close/cancel/complete routes.

    Each service function returns (success, error_message); the error is
    surfaced as a flash rather than being discarded.
    """
    form = await request.form()
    if not check_csrf(request, form.get("csrf_token", "")):
        add_flash(request, "That form expired. Reload the page and try again.", "error")
        return RedirectResponse(url="/admin/activities", status_code=303)

    activity = await svc.get_activity_by_id(db, activity_id)
    if not activity:
        add_flash(request, "Activity not found.", "error")
        return RedirectResponse(url="/admin/activities", status_code=303)

    success, error = await action(db, activity)
    add_flash(request, success_message if success else error,
              "success" if success else "error")
    return RedirectResponse(url="/admin/activities", status_code=303)


@router.post("/activities/{activity_id}/publish", name="admin.publish_activity")
async def publish_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _run_status_action(
        request, db, activity_id, svc.publish_activity, "Activity published."
    )


@router.post("/activities/{activity_id}/close-registration", name="admin.close_registration")
async def close_registration(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _run_status_action(
        request,
        db,
        activity_id,
        svc.close_registration,
        "Registration closed. The roster is now frozen.",
    )


@router.post("/activities/{activity_id}/cancel", name="admin.cancel_activity")
async def cancel_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _run_status_action(
        request, db, activity_id, svc.cancel_activity, "Activity cancelled."
    )


@router.post("/activities/{activity_id}/complete", name="admin.complete_activity")
async def complete_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _run_status_action(
        request, db, activity_id, svc.complete_activity, "Activity marked completed."
    )


# ── Stub routes ───────────────────────────────────────────────────────────────

@dataclass
class _GroupAdminView:
    """Shape the group-formation template expects for one group."""

    id: int
    label: str
    status: str
    members: list


def _formation_redirect(activity_id: int | None = None) -> RedirectResponse:
    url = "/admin/group-formation"
    if activity_id is not None:
        url += f"?activity_id={activity_id}"
    return RedirectResponse(url=url, status_code=303)


async def _formation_action(request: Request, db: AsyncSession, activity_id, action) -> RedirectResponse:
    """CSRF-check, run a formation service call, flash, redirect back."""
    form = await request.form()
    if not check_csrf(request, form.get("csrf_token", "")):
        add_flash(request, "That form expired. Reload the page and try again.", "error")
        return _formation_redirect(activity_id)
    success, message = await action()
    add_flash(request, message, "success" if success else "error")
    return _formation_redirect(activity_id)


@router.get("/group-formation", response_class=HTMLResponse, name="admin.group_formation")
async def group_formation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    activity_id: int | None = None,
):
    context = {
        "current_user": current_user,
        "activity": None,
        "pending_activities": [],
        "groups": [],
        "ungrouped_students": [],
        "active_nav": "group_formation",
    }

    # Activities awaiting group formation, newest deadline first.
    pending_rows = await db.execute(
        select(Activity, func.count(Registration.id))
        .join(Registration, Registration.activity_id == Activity.id)
        .where(
            Activity.status.in_([ActivityStatus.registration_closed, ActivityStatus.groups_proposed]),
            Registration.status == RegistrationStatus.registered,
        )
        .group_by(Activity.id)
        .order_by(Activity.registration_deadline.desc())
    )
    pending = []
    for activity, registered in pending_rows.all():
        activity.registered_count = registered
        activity.display_status = activity.status.value
        pending.append(activity)
    context["pending_activities"] = pending

    if activity_id is None:
        return templates.TemplateResponse(request, "admin/group_formation.html", context)

    activity = await formation.get_activity_or_none(db, activity_id)
    if activity is None:
        add_flash(request, "Activity not found.", "error")
        return _formation_redirect()

    # activity_status_badge.html reads display_status / registered_count,
    # normally attached by activity_service; this route loads the row directly.
    activity.display_status = activity.status.value
    activity.registered_count = await svc.get_registration_count(db, activity_id)

    student_ids = await formation.eligible_student_ids(db, activity_id)
    groups = await formation.get_groups_with_members(db, activity_id)
    grouped = formation.grouped_student_ids(groups)
    leftovers = [s for s in student_ids if s not in grouped]

    users = {}
    if leftovers:
        rows = await db.execute(select(User).where(User.id.in_(leftovers)))
        users = {u.id: u for u in rows.scalars().all()}

    formation_state = (
        "finalised" if activity.status == ActivityStatus.groups_formed
        else "proposed" if activity.status == ActivityStatus.groups_proposed
        else "not_started"
    )
    group_views = _group_views(groups)

    # The template iterates `groups` and `ungrouped_students`; the contract keys
    # (`proposal`, `leftovers`) are supplied too so either shape works.
    context.update(
        {
            "activity": activity,
            "groups": group_views,
            "ungrouped_students": [users[s] for s in leftovers if s in users],
            "summary": {
                "eligible_count": len(student_ids),
                "complete_groups_possible": len(student_ids) // activity.group_size,
                "leftover_count": len(leftovers),
                "has_history": bool(groups),
            },
            "formation_state": formation_state,
            "proposal": group_views if formation_state == "proposed" else None,
            "leftovers": [SimpleNamespace(id=s, name=users[s].name)
                          for s in leftovers if s in users],
            "leftover_options": _leftover_options(activity, groups, leftovers),
            "can_start": activity.status == ActivityStatus.registration_closed and bool(student_ids),
            "can_finalise": activity.status == ActivityStatus.groups_proposed and bool(groups) and not leftovers,
            "can_discard": activity.status == ActivityStatus.groups_proposed,
        }
    )
    return templates.TemplateResponse(request, "admin/group_formation.html", context)


def _group_views(groups) -> list[_GroupAdminView]:
    """Plain view objects for the template.

    `Group.status` is a Python enum, and rendering it directly would put a
    `GroupStatus.proposed` repr into the page, so the status is passed as a
    plain string for the badge partial to look up.
    """
    return [
        _GroupAdminView(
            id=g.id,
            label=g.label,
            status=g.status.value,
            members=[SimpleNamespace(id=m.student_id, name=m.student.name)
                     for m in g.members],
        )
        for g in groups
    ]


def _leftover_options(activity: Activity, groups: list, leftovers: list[int]) -> list[str]:
    """Only the two documented options, and only when they are actionable.

    With no complete group there is nothing to add leftovers to, so the
    create-a-new-group option is the only one offered.
    """
    if not leftovers:
        return []
    if any(g.members for g in groups):
        return ["add_to_existing_groups", "new_group_from_leftovers"]
    return ["new_group_from_leftovers"]


@router.post("/activities/{activity_id}/formation/start", name="admin.start_formation")
async def start_formation(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await _formation_action(
        request, db, activity_id, lambda: formation.start_formation(db, activity_id)
    )


@router.post("/activities/{activity_id}/formation/create-group", name="admin.create_group")
async def create_group(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    form = await request.form()
    raw_ids = form.getlist("student_ids")
    if not check_csrf(request, form.get("csrf_token", "")):
        add_flash(request, "That form expired. Reload the page and try again.", "error")
        return _formation_redirect(activity_id)

    student_ids = [int(v) for v in raw_ids if str(v).isdigit()]
    return await _formation_action(
        request,
        db,
        activity_id,
        lambda: formation.create_group_from_students(db, activity_id, student_ids),
    )


@router.post("/activities/{activity_id}/formation/leftovers/new-group", name="admin.new_group_from_leftovers")
async def new_group_from_leftovers(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await _formation_action(
        request, db, activity_id, lambda: formation.new_group_from_leftovers(db, activity_id)
    )


@router.post("/activities/{activity_id}/formation/leftovers/add-to-existing", name="admin.add_leftovers_to_existing")
async def add_leftovers_to_existing(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await _formation_action(
        request, db, activity_id, lambda: formation.add_leftovers_to_existing(db, activity_id)
    )


@router.post("/activities/{activity_id}/formation/finalize", name="admin.finalize_groups")
async def finalize_groups(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await _formation_action(
        request, db, activity_id, lambda: formation.finalise_groups(db, activity_id)
    )


@router.post("/activities/{activity_id}/formation/discard", name="admin.discard_formation")
async def discard_formation(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await _formation_action(
        request, db, activity_id, lambda: formation.discard_formation(db, activity_id)
    )


@router.post("/groups/{group_id}/disband", name="admin.remove_group")
async def remove_group(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    group = await db.get(Group, group_id)
    activity_id = group.activity_id if group else None
    return await _formation_action(
        request, db, activity_id, lambda: formation.disband_group(db, group_id)
    )


@router.get(
    "/activities/{activity_id}/registrations",
    response_class=HTMLResponse,
    name="admin.activity_registrations",
)
async def activity_registrations(
    request: Request,
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await svc.list_activity_registrations(db, activity_id)
    if result["activity"] is None:
        add_flash(request, "Activity not found.", "error")
        return RedirectResponse(url="/admin/activities", status_code=303)

    # manage_activities.html is the shell for this sub-view, so its list context
    # is supplied alongside the registrations data. The sub-view markup itself
    # is not in the template yet (ISSUE 17).
    listing = await svc.list_activities_admin(db)
    return templates.TemplateResponse(
        request,
        "admin/manage_activities.html",
        {
            "current_user": current_user,
            "activities": listing["activities"],
            "filters": {"q": "", "status": "", "page": 1},
            "pagination": listing["pagination"],
            "activity": result["activity"],
            "rows": result["rows"],

            "sub_view": "registrations",
            "active_nav": "manage_activities",
        },
    )


@router.get("/group-history", response_class=HTMLResponse, name="admin.group_history")
async def group_history(
    request: Request,
    q: str = Query(default=""),
    activity_id: str = Query(default=""),
    date_from: str = Query(default=""),
    page: int = Query(default=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await group_svc.list_group_history(
        db, q=q, activity_id=activity_id, date_from=date_from, page=page
    )
    # Supplied under both names: the template iterates `groups`, while
    # template-contract.md names the list `entries` (ISSUE 11).
    return templates.TemplateResponse(
        request,
        "admin/group_history.html",
        {
            "current_user": current_user,
            "groups": result["entries"],
            "entries": result["entries"],
            "filters": {"q": q, "activity_id": activity_id, "date_from": date_from},
            "pagination": result["pagination"],
            "active_nav": "group_history",
        },
    )
