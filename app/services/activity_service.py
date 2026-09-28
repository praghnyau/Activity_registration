"""
activity_service.py — all business logic for activities and resources.

Responsibilities:
- Create and update activities with date validation
- Status transitions (publish, close, cancel, complete)
- Resource link management (add, remove, limit 5)
- Registration count queries
- Activity listing for admin and students
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.activity import Activity, ActivityStatus
from app.models.resource import Resource
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User

IST = ZoneInfo("Asia/Kolkata")


# ── Date helpers ──────────────────────────────────────────────────────────────

def _parse_dt(value: str) -> datetime | None:
    """Parse datetime-local input (YYYY-MM-DDTHH:MM) to timezone-aware datetime."""
    if not value or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt
    except ValueError:
        return None


def _fmt_input(dt: datetime | None) -> str:
    """Format datetime for HTML datetime-local input value."""
    if not dt:
        return ""
    local = dt.astimezone(IST)
    return local.strftime("%Y-%m-%dT%H:%M")


def validate_activity_dates(
    starts_at: datetime,
    registration_deadline: datetime,
    formation_cutoff: datetime,
) -> dict:
    """
    Validate date ordering rules. Returns dict of field errors (empty = valid).
    Required order: registration_deadline < formation_cutoff < starts_at
    """
    errors = {}
    now = datetime.now(tz=IST)

    if registration_deadline <= now:
        errors["registration_deadline"] = "Registration deadline must be in the future."

    if starts_at <= registration_deadline:
        errors["starts_at"] = "Activity date must be after the registration deadline."

    if formation_cutoff <= registration_deadline:
        errors["formation_cutoff"] = "Formation cutoff must be after the registration deadline."

    if formation_cutoff >= starts_at:
        errors["formation_cutoff"] = "Formation cutoff must be before the activity date."

    return errors


# ── Activity CRUD ─────────────────────────────────────────────────────────────

def validate_activity_form(data: dict) -> dict:
    """
    Validate all activity form fields. Returns dict of field-level errors.
    Empty dict means all valid.
    """
    errors = {}

    if not data.get("title", "").strip():
        errors["title"] = "Title is required."

    group_size = data.get("group_size")
    try:
        group_size = int(group_size)
        if group_size < 1:
            errors["group_size"] = "Group size must be at least 1."
    except (TypeError, ValueError):
        errors["group_size"] = "Group size must be a number."

    duration = data.get("duration_minutes")
    if duration:
        try:
            duration = int(duration)
            if duration < 1:
                errors["duration_minutes"] = "Duration must be at least 1 minute."
        except (TypeError, ValueError):
            errors["duration_minutes"] = "Duration must be a number."

    capacity = data.get("capacity")
    if capacity:
        try:
            capacity = int(capacity)
            if capacity < 1:
                errors["capacity"] = "Capacity must be at least 1."
            elif "group_size" not in errors and capacity < group_size:
                errors["capacity"] = "Capacity must be at least the group size."
        except (TypeError, ValueError):
            errors["capacity"] = "Capacity must be a number."

    starts_at = _parse_dt(data.get("starts_at"))
    if not starts_at:
        errors["starts_at"] = "Activity date is required."

    reg_deadline = _parse_dt(data.get("registration_deadline"))
    if not reg_deadline:
        errors["registration_deadline"] = "Registration deadline is required."

    # formation_cutoff defaults to registration_deadline if blank
    formation_cutoff_raw = data.get("formation_cutoff", "").strip()
    formation_cutoff = _parse_dt(formation_cutoff_raw) if formation_cutoff_raw else reg_deadline

    if starts_at and reg_deadline and formation_cutoff and not errors.get("starts_at") and not errors.get("registration_deadline"):
        date_errors = validate_activity_dates(starts_at, reg_deadline, formation_cutoff)
        errors.update(date_errors)

    return errors


async def create_activity(db: AsyncSession, data: dict, created_by: User) -> Activity:
    """Create a new activity in draft status."""
    starts_at = _parse_dt(data["starts_at"])
    reg_deadline = _parse_dt(data["registration_deadline"])
    formation_cutoff_raw = data.get("formation_cutoff", "").strip()
    formation_cutoff = _parse_dt(formation_cutoff_raw) if formation_cutoff_raw else reg_deadline

    duration = int(data["duration_minutes"]) if data.get("duration_minutes") else None
    capacity = int(data["capacity"]) if data.get("capacity") else None

    activity = Activity(
        title=data["title"].strip(),
        description=data.get("description", "").strip(),
        starts_at=starts_at,
        duration_minutes=duration or 60,
        location=data.get("location", "").strip() or None,
        group_size=int(data["group_size"]),
        capacity=capacity,
        registration_deadline=reg_deadline,
        formation_cutoff=formation_cutoff,
        status=ActivityStatus.draft,
        created_by=created_by.id,
    )
    db.add(activity)
    await db.flush()  # get the id without committing

    # Save resource links
    await _save_resources(db, activity, data)

    await db.commit()
    await db.refresh(activity)
    return activity


async def update_activity(db: AsyncSession, activity: Activity, data: dict) -> Activity:
    """Update an existing activity. Only allowed when status is draft or open."""
    starts_at = _parse_dt(data["starts_at"])
    reg_deadline = _parse_dt(data["registration_deadline"])
    formation_cutoff_raw = data.get("formation_cutoff", "").strip()
    formation_cutoff = _parse_dt(formation_cutoff_raw) if formation_cutoff_raw else reg_deadline

    activity.title = data["title"].strip()
    activity.description = data.get("description", "").strip()
    activity.starts_at = starts_at
    activity.duration_minutes = int(data["duration_minutes"]) if data.get("duration_minutes") else 60
    activity.location = data.get("location", "").strip() or None
    activity.group_size = int(data["group_size"])
    activity.capacity = int(data["capacity"]) if data.get("capacity") else None
    activity.registration_deadline = reg_deadline
    activity.formation_cutoff = formation_cutoff

    # Replace resources
    await db.execute(
        Resource.__table__.delete().where(Resource.activity_id == activity.id)
    )
    await _save_resources(db, activity, data)

    await db.commit()
    await db.refresh(activity)
    return activity


async def _save_resources(db: AsyncSession, activity: Activity, data: dict):
    """Parse resource_title_N / resource_url_N pairs from form data and save."""
    for i in range(5):
        title = data.get(f"resource_title_{i}", "").strip()
        url = data.get(f"resource_url_{i}", "").strip()
        if title and url:
            if not url.startswith("https://"):
                continue  # skip invalid URLs silently — form should validate
            resource = Resource(
                activity_id=activity.id,
                title=title,
                url=url,
            )
            db.add(resource)


# ── Status transitions ────────────────────────────────────────────────────────

async def publish_activity(db: AsyncSession, activity: Activity) -> tuple[bool, str]:
    """Draft → Open. Returns (success, error_message)."""
    if activity.status != ActivityStatus.draft:
        return False, "Only draft activities can be published."
    activity.status = ActivityStatus.open
    await db.commit()
    return True, ""


async def close_registration(db: AsyncSession, activity: Activity) -> tuple[bool, str]:
    """Open/Full → Registration Closed."""
    if activity.status not in (ActivityStatus.open, ActivityStatus.full):
        return False, "Registration can only be closed on open activities."
    activity.status = ActivityStatus.registration_closed
    await db.commit()
    return True, ""


async def cancel_activity(db: AsyncSession, activity: Activity) -> tuple[bool, str]:
    """Cancel an activity. Updates all registered registrations to cancelled."""
    if activity.status in (ActivityStatus.cancelled, ActivityStatus.completed):
        return False, "Activity is already cancelled or completed."

    activity.status = ActivityStatus.cancelled

    # Cancel all active registrations
    result = await db.execute(
        select(Registration).where(
            and_(
                Registration.activity_id == activity.id,
                Registration.status == RegistrationStatus.registered,
            )
        )
    )
    for reg in result.scalars().all():
        reg.status = RegistrationStatus.cancelled

    await db.commit()
    return True, ""


async def complete_activity(db: AsyncSession, activity: Activity) -> tuple[bool, str]:
    """Mark activity as completed."""
    if activity.status != ActivityStatus.groups_formed:
        return False, "Activity can only be completed after groups are formed."
    activity.status = ActivityStatus.completed
    await db.commit()
    return True, ""


async def recompute_full_status(db: AsyncSession, activity: Activity):
    """
    Recompute whether activity is full after a registration change.
    Called by registration service whenever a registration is added or removed.
    """
    if activity.capacity is None:
        return  # unlimited — never full
    if activity.status not in (ActivityStatus.open, ActivityStatus.full):
        return

    result = await db.execute(
        select(func.count()).where(
            and_(
                Registration.activity_id == activity.id,
                Registration.status == RegistrationStatus.registered,
            )
        )
    )
    count = result.scalar()
    if count >= activity.capacity:
        activity.status = ActivityStatus.full
    else:
        activity.status = ActivityStatus.open
    await db.commit()


# ── Listing queries ───────────────────────────────────────────────────────────

async def get_activity_by_id(db: AsyncSession, activity_id: int) -> Activity | None:
    """Fetch a single activity with its resources eagerly loaded."""
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.resources))
        .where(Activity.id == activity_id)
    )
    return result.scalar_one_or_none()


async def get_registration_count(db: AsyncSession, activity_id: int) -> int:
    """Count active (registered) registrations for an activity."""
    result = await db.execute(
        select(func.count()).where(
            and_(
                Registration.activity_id == activity_id,
                Registration.status == RegistrationStatus.registered,
            )
        )
    )
    return result.scalar() or 0


async def list_activities_admin(
    db: AsyncSession,
    q: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    List all activities for admin with optional filters and pagination.
    Returns dict with activities list and pagination info.
    """
    query = select(Activity).options(selectinload(Activity.resources))

    if q:
        query = query.where(Activity.title.ilike(f"%{q}%"))
    if status:
        query = query.where(Activity.status == status)

    # Total count for pagination
    count_query = select(func.count()).select_from(Activity)
    if q:
        count_query = count_query.where(Activity.title.ilike(f"%{q}%"))
    if status:
        count_query = count_query.where(Activity.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Activity.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    activities_raw = (await db.execute(query)).scalars().all()

    # Attach registration counts and helper fields
    activities = []
    for a in activities_raw:
        count = await get_registration_count(db, a.id)
        a.registered_count = count
        a.display_status = a.status.value
        # datetime-local input format for edit form
        a.starts_at_input = _fmt_input(a.starts_at)
        a.registration_deadline_input = _fmt_input(a.registration_deadline)
        a.formation_cutoff_input = _fmt_input(a.formation_cutoff)
        activities.append(a)

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "activities": activities,
        "pagination": {"page": page, "total_pages": total_pages, "total": total},
    }


async def list_activities_student(
    db: AsyncSession,
    q: str = "",
    date_from: str = "",
    availability: str = "",
    page: int = 1,
    page_size: int = 12,
) -> dict:
    """
    List open/full activities for students with optional filters.
    Students only see open and full activities.
    """
    query = select(Activity).where(
        Activity.status.in_([ActivityStatus.open, ActivityStatus.full])
    )

    if q:
        query = query.where(Activity.title.ilike(f"%{q}%"))
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from).replace(tzinfo=IST)
            query = query.where(Activity.starts_at >= dt)
        except ValueError:
            pass
    if availability == "open":
        query = query.where(Activity.status == ActivityStatus.open)
    elif availability == "full":
        query = query.where(Activity.status == ActivityStatus.full)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Activity.starts_at.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    activities_raw = (await db.execute(query)).scalars().all()

    activities = []
    for a in activities_raw:
        count = await get_registration_count(db, a.id)
        a.registered_count = count
        a.display_status = a.status.value
        activities.append(a)

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "activities": activities,
        "pagination": {"page": page, "total_pages": total_pages, "total": total},
    }


# ── Admin registrations view (Phase 6) ───────────────────────────────────────

@dataclass
class RegistrationRow:
    """One row of the admin Activity Registrations sub-view."""

    registration_id: int
    student_name: str
    student_email: str
    registered_at: datetime
    registration_status: str
    group_status: str
    group_label: str | None = None


async def list_activity_registrations(db: AsyncSession, activity_id: int) -> dict:
    """
    Every registration for an activity, with the student's group assignment.

    Read-only. Students are the only ones who can leave an activity, and only
    until registration closes, so there is no administrative removal to offer
    here.
    """
    from app.services import group_service as group_svc

    activity = await db.get(Activity, activity_id)
    if activity is None:
        return {"activity": None, "rows": []}

    rows = await db.execute(
        select(Registration, User)
        .join(User, User.id == Registration.student_id)
        .where(Registration.activity_id == activity_id)
        .order_by(User.name)
    )

    entries = []
    registered_count = 0
    for registration, student in rows.all():
        group_status, group_label = await group_svc.group_status_for_registration(db, registration)
        if registration.status == RegistrationStatus.registered:
            registered_count += 1
        entries.append(
            RegistrationRow(
                registration_id=registration.id,
                student_name=student.name,
                student_email=student.email,
                registered_at=registration.registered_at,
                registration_status=registration.status.value,
                group_status=group_status,
                group_label=group_label,
            )
        )

    activity.display_status = activity.status.value
    activity.registered_count = registered_count

    return {"activity": activity, "rows": entries}


CLOSED_STATUSES = (
    ActivityStatus.registration_closed,
    ActivityStatus.cancelled,
    ActivityStatus.completed,
)


async def list_closed_activities(
    db: AsyncSession,
    q: str = "",
    date_from: str = "",
    closure_reason: str = "",
    page: int = 1,
    page_size: int = 12,
) -> dict:
    """
    The student-facing archive: activities no longer open for registration.

    `closure_reason` is the activity status restricted to the three closable
    values, which is what `closed_activities.html` resolves through its own
    `closure_labels` map. Unknown values are ignored rather than raising, so a
    stale bookmark cannot 500 the page.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    query = select(Activity).where(Activity.status.in_(CLOSED_STATUSES))

    if q.strip():
        query = query.where(Activity.title.ilike(f"%{q.strip()}%"))
    if date_from:
        dt = _parse_dt(date_from)
        if dt:
            query = query.where(Activity.starts_at >= dt)
    if closure_reason in {s.value for s in CLOSED_STATUSES}:
        query = query.where(Activity.status == ActivityStatus(closure_reason))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    rows = await db.execute(
        query.order_by(Activity.starts_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    activities = list(rows.scalars().all())

    for a in activities:
        a.display_status = a.status.value
        a.closure_reason = a.status.value

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "activities": activities,
        "pagination": {
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "total_items": total,
        },
    }
