"""
group_service.py — read and administrative operations on finalised groups.

Group *proposal* lifecycle lives in `group_formation.py`; this module covers
looking at settled groups and the administrative edits Phase 6 will add.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity
from app.models.group import Group, GroupStatus
from app.models.group_member import GroupMember
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User

IST = ZoneInfo("Asia/Kolkata")


def _parse_date(value: str) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed


@dataclass
class MemberRef:
    """
    A group member as the history table consumes it.

    `group_history.html` does `members | map(attribute='name')`, so this must
    expose `.name`. `__str__` returns the bare name too, so the contract's
    "list of strings" reading also renders sensibly.
    """

    id: int
    name: str

    def __str__(self) -> str:  # pragma: no cover - display helper
        return self.name


@dataclass
class HistoryEntry:
    """One finalised group, shaped for `admin/group_history.html`."""

    id: int
    activity_id: int
    activity_title: str
    activity_date: datetime
    group_label: str
    formed_at: datetime | None
    status: str
    members: list[MemberRef] = field(default_factory=list)

    # The template reads `group.label`; the contract names it `group_label`.
    # Both are provided so neither consumer breaks.
    @property
    def label(self) -> str:
        return self.group_label


async def active_member_names(db: AsyncSession, group) -> list[str]:
    """Names of the group's members, in display order."""
    rows = await db.execute(
        select(User.name)
        .join(GroupMember, GroupMember.student_id == User.id)
        .join(
            Registration,
            (Registration.student_id == User.id)
            & (Registration.activity_id == group.activity_id),
        )
        .where(
            GroupMember.group_id == group.id,
            Registration.status == RegistrationStatus.registered,
        )
        .order_by(User.name)
    )
    return list(rows.scalars().all())


async def group_status_for_registration(
    db: AsyncSession, registration
) -> tuple[str, str | None]:
    """
    `(group_status_key, group_label)` for one registration.

    Only three states are reachable. Withdrawal is impossible once registration
    has closed and administrators cannot remove students, so a finalised group
    can never lose a member and there is no "awaiting decision" state.
    """
    if registration.status != RegistrationStatus.registered:
        return "no_group", None

    rows = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            Group.activity_id == registration.activity_id,
            Group.status == GroupStatus.finalised,
            GroupMember.student_id == registration.student_id,
        )
        .order_by(Group.id)
    )

    for group in rows.scalars().all():
        return "group_formed", group.label

    return "not_yet_formed", None


async def list_group_history(
    db: AsyncSession,
    q: str = "",
    activity_id: str = "",
    date_from: str = "",
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """
    Every finalised group, newest first, with members resolved.

    Proposed groups are excluded: history means settled groupings.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    query = (
        select(Group)
        .join(Activity, Activity.id == Group.activity_id)
        .where(Group.status == GroupStatus.finalised)
        # `activity` lazy-loads, which cannot happen under asyncio, so it is
        # fetched up front alongside the members.
        .options(selectinload(Group.activity), selectinload(Group.members).selectinload(GroupMember.student))
    )

    if q.strip():
        query = query.where(Activity.title.ilike(f"%{q.strip()}%"))
    if activity_id.strip().isdigit():
        query = query.where(Group.activity_id == int(activity_id.strip()))
    if date_from:
        dt = _parse_date(date_from)
        if dt:
            query = query.where(Activity.starts_at >= dt)

    # The filtered count must share the page query's predicate set, so it is
    # derived from the same statement rather than re-derived by hand.
    subquery = query.order_by(None).subquery()
    total = await db.scalar(select(func.count()).select_from(subquery)) or 0

    rows = await db.execute(
        query.order_by(Activity.starts_at.desc(), Group.label)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    entries = []
    for group in rows.scalars().unique().all():
        activity = group.activity
        members = sorted(
            (MemberRef(id=m.student_id, name=m.student.name) for m in group.members),
            key=lambda m: m.name,
        )
        entries.append(
            HistoryEntry(
                id=group.id,
                activity_id=group.activity_id,
                activity_title=activity.title,
                activity_date=activity.starts_at,
                group_label=group.label,
                formed_at=group.formed_at,
                # Student-facing badge key, so this renders as "Group Formed"
                # rather than an unmapped raw value.
                status="group_formed",
                members=members,
            )
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "entries": entries,
        "pagination": {
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "total_items": total,
        },
    }
