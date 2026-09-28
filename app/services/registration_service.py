"""
registration_service.py — business logic for student registrations.

Rules enforced here:
- No registration after registration_deadline
- No duplicate active registrations (re-registration updates existing record)
- No registration on non-open activities
- Capacity enforcement with row-level locking
- Withdrawal only before registration_deadline
- No withdrawal after deadline
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.registration import Registration, RegistrationStatus
from app.models.activity import Activity, ActivityStatus
from app.models.group import Group, GroupStatus
from app.models.group_member import GroupMember
from app.services.activity_service import recompute_full_status

IST = ZoneInfo("Asia/Kolkata")


# ── Register ──────────────────────────────────────────────────────────────────

async def register_student(
    db: AsyncSession,
    student_id: int,
    activity_id: int,
) -> tuple[Registration | None, str | None]:
    """
    Register a student for an activity.
    Returns (registration, error_message).
    error_message is None on success.

    Handles three cases:
    1. No existing record → insert new registration
    2. Existing withdrawn record → update status back to registered
    3. Existing registered record → duplicate, return error
    """
    now = datetime.now(tz=IST)

    # Fetch activity with a row-level lock to prevent race conditions on capacity
    result = await db.execute(
        select(Activity)
        .where(Activity.id == activity_id)
        .with_for_update()
    )
    activity = result.scalar_one_or_none()

    if not activity:
        return None, "Activity not found."

    # Rule: activity must be open or full (full still allows registration? No — full means no more slots)
    if activity.status not in (ActivityStatus.open,):
        if activity.status == ActivityStatus.full:
            return None, "This activity is full. No more registrations are available."
        elif activity.status == ActivityStatus.draft:
            return None, "This activity is not open for registration yet."
        elif activity.status == ActivityStatus.registration_closed:
            return None, "Registration for this activity has closed."
        elif activity.status == ActivityStatus.cancelled:
            return None, "This activity has been cancelled."
        else:
            return None, "Registration is not available for this activity."

    # Rule: registration deadline must not have passed
    if now > activity.registration_deadline.astimezone(IST):
        return None, "The registration deadline has passed."

    # Rule: capacity check
    if activity.capacity is not None:
        count_result = await db.execute(
            select(func.count()).where(
                and_(
                    Registration.activity_id == activity_id,
                    Registration.status == RegistrationStatus.registered,
                )
            )
        )
        current_count = count_result.scalar() or 0
        if current_count >= activity.capacity:
            return None, "This activity is full."

    # Check for existing registration record
    existing_result = await db.execute(
        select(Registration).where(
            Registration.student_id == student_id,
            Registration.activity_id == activity_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.status == RegistrationStatus.registered:
            return None, "You are already registered for this activity."
        elif existing.status == RegistrationStatus.withdrawn:
            # Re-registration — update existing record
            existing.status = RegistrationStatus.registered
            existing.registered_at = now
            await db.commit()
            await db.refresh(existing)
            await recompute_full_status(db, activity)
            return existing, None
        elif existing.status == RegistrationStatus.cancelled:
            return None, "Your registration was cancelled. Please contact an administrator."

    # New registration
    registration = Registration(
        student_id=student_id,
        activity_id=activity_id,
        status=RegistrationStatus.registered,
    )
    db.add(registration)
    await db.commit()
    await db.refresh(registration)

    # Recompute full status after adding a new registration
    await recompute_full_status(db, activity)

    return registration, None


# ── Withdraw ──────────────────────────────────────────────────────────────────

async def withdraw_student(
    db: AsyncSession,
    registration_id: int,
    student_id: int,
) -> tuple[bool, str]:
    """
    Withdraw a student from an activity.
    Returns (success, error_message).

    Rules:
    - Only the student who registered can withdraw
    - Only if status is 'registered'
    - Only while registration is still open: status must be `open` and the
      deadline must not have passed

    Because a withdrawal is impossible once registration has closed, the roster
    is frozen by the time groups are finalised. A finalised group can therefore
    never lose a member, and no "awaiting decision" state is reachable.
    """
    now = datetime.now(tz=IST)

    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.activity))
        .where(Registration.id == registration_id)
    )
    registration = result.scalar_one_or_none()

    if not registration:
        return False, "Registration not found."

    # Security: ensure the student owns this registration
    if registration.student_id != student_id:
        return False, "You are not authorised to withdraw this registration."

    if registration.status != RegistrationStatus.registered:
        return False, "This registration is not active."

    # Rule: withdrawal is only possible while registration is still open
    activity = registration.activity
    if activity.status != ActivityStatus.open:
        return False, "Registration for this activity has closed. Withdrawals are no longer accepted."
    if now > activity.registration_deadline.astimezone(IST):
        return False, "The registration deadline has passed. Withdrawals are no longer accepted."

    registration.status = RegistrationStatus.withdrawn
    await db.commit()

    # Recompute full status — a slot just freed up
    await recompute_full_status(db, activity)

    return True, ""


# ── List registrations for a student ─────────────────────────────────────────

async def list_my_registrations(
    db: AsyncSession,
    student_id: int,
    q: str = "",
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """
    Return all registrations for a student, enriched with group info.
    Each entry in the list is a dict with everything the template needs.
    """
    query = (
        select(Registration)
        .options(selectinload(Registration.activity))
        .where(Registration.student_id == student_id)
        .order_by(Registration.registered_at.desc())
    )

    if q:
        query = query.join(Activity).where(Activity.title.ilike(f"%{q}%"))

    count_query = select(func.count()).select_from(
        select(Registration)
        .where(Registration.student_id == student_id)
        .subquery()
    )
    if q:
        count_query = select(func.count()).select_from(
            select(Registration)
            .join(Activity)
            .where(
                and_(
                    Registration.student_id == student_id,
                    Activity.title.ilike(f"%{q}%"),
                )
            )
            .subquery()
        )

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    registrations_raw = (await db.execute(query)).scalars().all()

    now = datetime.now(tz=IST)
    entries = []

    for reg in registrations_raw:
        activity = reg.activity
        activity.display_status = activity.status.value
        deadline_passed = now > activity.registration_deadline.astimezone(IST)

        # Determine can_withdraw. Withdrawal is only possible while registration
        # is still open, which is what keeps a finalised group intact forever.
        registration_open = (
            activity.status == ActivityStatus.open and not deadline_passed
        )
        can_withdraw = (
            reg.status == RegistrationStatus.registered
            and registration_open
        )
        withdraw_blocked_reason = None
        if reg.status == RegistrationStatus.registered and not registration_open:
            withdraw_blocked_reason = "Registration for this activity has closed. Withdrawals are no longer accepted."

        # Group status uses the keys defined in template-contract.md. A
        # withdrawn or cancelled registration has no group. A proposal that is
        # not yet finalised reports `not_yet_formed` — students must never see
        # a proposed group.
        group_status = "not_yet_formed"
        group_summary = None

        if reg.status == RegistrationStatus.registered:
            gm_result = await db.execute(
                select(GroupMember, Group)
                .join(Group, Group.id == GroupMember.group_id)
                .where(
                    and_(
                        GroupMember.student_id == student_id,
                        Group.activity_id == activity.id,
                    )
                )
            )
            row = gm_result.first()
            if row:
                gm, group = row
                if group.status == GroupStatus.finalised:
                    from app.services import group_service as group_svc

                    # One source of truth for the status key, shared with My
                    # Groups and the admin registrations view.
                    group_status, group_label = await group_svc.group_status_for_registration(
                        db, reg
                    )
                    count_result = await db.execute(
                        select(func.count())
                        .select_from(GroupMember)
                        .join(
                            Registration,
                            (Registration.student_id == GroupMember.student_id)
                            & (Registration.activity_id == group.activity_id),
                        )
                        .where(
                            GroupMember.group_id == group.id,
                            Registration.status == RegistrationStatus.registered,
                        )
                    )
                    member_count = count_result.scalar() or 0
                    group_summary = {
                        "label": group_label,
                        "member_count": member_count,
                    }
        else:
            group_status = "no_group"

        entries.append({
            "registration_id": reg.id,
            "registration_status": reg.status.value,
            "registered_at": reg.registered_at,
            "activity": activity,
            "can_withdraw": can_withdraw,
            "withdraw_blocked_reason": withdraw_blocked_reason,
            "group_status": group_status,
            "group_summary": group_summary,
        })

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "registrations": entries,
        "pagination": {
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "total_items": total,
        },
    }
