"""Group formation: automatic proposal, leftover handling, and finalisation.

The pairing history is built from *finalised* groups only, so proposed groups
never influence how the next activity is divided.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityStatus
from app.models.group import Group, GroupStatus
from app.models.group_member import GroupMember
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User

PairKey = tuple[int, int]


def pair_key(a: int, b: int) -> PairKey:
    return (a, b) if a < b else (b, a)


async def build_pair_history(db: AsyncSession) -> dict[PairKey, int]:
    """Count how often each pair of students was grouped together before."""
    rows = await db.execute(
        select(GroupMember.group_id, GroupMember.student_id)
        .join(Group, Group.id == GroupMember.group_id)
        .where(Group.status == GroupStatus.finalised)
    )

    by_group: dict[int, list[int]] = {}
    for group_id, student_id in rows.all():
        by_group.setdefault(group_id, []).append(student_id)

    history: dict[PairKey, int] = {}
    for members in by_group.values():
        for a, b in combinations(sorted(members), 2):
            key = pair_key(a, b)
            history[key] = history.get(key, 0) + 1
    return history


def assign_groups(
    student_ids: list[int],
    group_size: int,
    history: dict[PairKey, int],
    *,
    group_count: int | None = None,
    max_size: int | None = None,
) -> tuple[list[list[int]], list[int]]:
    """Greedily assign students to groups, minimising repeated pairings.

    ``max_size`` caps each group; students that cannot be placed without
    exceeding it are returned as leftovers. Leaving it ``None`` allows
    overshooting, which is what spreading leftovers over existing groups
    deliberately does.

    Returns ``(groups, leftovers)``. Each group is a list of student ids.
    """
    remaining = list(student_ids)
    random.shuffle(remaining)

    if group_count is None:
        group_count = len(remaining) // group_size if group_size else 0
    group_count = max(0, min(group_count, len(remaining)))

    groups: list[list[int]] = [[] for _ in range(group_count)]

    for student in remaining:
        best_index, best_key = None, None
        for index, members in enumerate(groups):
            if max_size is not None and len(members) >= max_size:
                continue
            repeats = sum(history.get(pair_key(student, m), 0) for m in members)
            # Fewest previous pairings, then smallest group, then first.
            candidate = (repeats, len(members), index)
            if best_key is None or candidate < best_key:
                best_index, best_key = index, candidate
        if best_index is None:
            continue
        groups[best_index].append(student)

    placed = {s for g in groups for s in g}
    leftovers = [s for s in student_ids if s not in placed]
    return [g for g in groups if g], leftovers


async def eligible_student_ids(db: AsyncSession, activity_id: int) -> list[int]:
    """Registered students for the activity, in a stable order."""
    rows = await db.execute(
        select(Registration.student_id)
        .where(
            Registration.activity_id == activity_id,
            Registration.status == RegistrationStatus.registered,
        )
        .order_by(Registration.student_id)
    )
    return list(rows.scalars().all())


async def get_activity_or_none(db: AsyncSession, activity_id: int) -> Activity | None:
    return await db.get(Activity, activity_id)


async def get_groups_with_members(db: AsyncSession, activity_id: int) -> list[Group]:
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Group)
        .where(Group.activity_id == activity_id)
        .options(selectinload(Group.members).selectinload(GroupMember.student))
        .order_by(Group.id)
    )
    return list(result.scalars().unique().all())


def grouped_student_ids(groups: list[Group]) -> set[int]:
    return {m.student_id for g in groups for m in g.members}


async def start_formation(db: AsyncSession, activity_id: int) -> tuple[bool, str]:
    """Build a proposal: complete groups only, remainder left as leftovers."""
    activity = await get_activity_or_none(db, activity_id)
    if activity is None:
        return False, "Activity not found."

    # Checked before the status guard: at this point registration *is* closed,
    # so the status message would be misleading.
    existing = await db.execute(
        select(Group.id).where(
            Group.activity_id == activity_id,
            Group.status == GroupStatus.proposed,
        )
    )
    if existing.first():
        return False, "A group proposal already exists. Discard it before starting again."

    if activity.status != ActivityStatus.registration_closed:
        return False, "Groups can only be proposed once registration is closed."
    if activity.registration_deadline > datetime.now(timezone.utc):
        return False, "The registration deadline has not passed yet."

    students = await eligible_student_ids(db, activity_id)
    if not students:
        return False, "No registered students to form groups from."

    history = await build_pair_history(db)
    groups, _leftovers = assign_groups(
        students, activity.group_size, history, max_size=activity.group_size
    )

    for index, members in enumerate(groups, start=1):
        group = Group(
            activity_id=activity_id,
            label=f"Group {index}",
            status=GroupStatus.proposed,
        )
        group.members = [GroupMember(student_id=student_id) for student_id in members]
        db.add(group)

    activity.status = ActivityStatus.groups_proposed
    await db.commit()
    return True, f"Proposed {len(groups)} group(s). Any remaining students are ungrouped."


async def create_group_from_students(
    db: AsyncSession, activity_id: int, student_ids: list[int]
) -> tuple[bool, str]:
    """Create one proposed group from an explicit selection of students."""
    activity = await get_activity_or_none(db, activity_id)
    if activity is None:
        return False, "Activity not found."
    if activity.status != ActivityStatus.groups_proposed:
        return False, "Start a group proposal before creating groups."

    wanted = list(dict.fromkeys(student_ids))
    if not wanted:
        return False, "Select at least one student."

    eligible = set(await eligible_student_ids(db, activity_id))
    unknown = [s for s in wanted if s not in eligible]
    if unknown:
        return False, "Some selected students are not registered for this activity."

    groups = await get_groups_with_members(db, activity_id)
    already = grouped_student_ids(groups)
    clash = [s for s in wanted if s in already]
    if clash:
        return False, "Some selected students are already in a group. Disband that group first."

    label_number = len(groups) + 1
    group = Group(
        activity_id=activity_id,
        label=f"Group {label_number}",
        status=GroupStatus.proposed,
    )
    group.members = [GroupMember(student_id=s) for s in wanted]
    db.add(group)
    await db.commit()
    return True, f"Created {group.label} with {len(wanted)} student(s)."


async def disband_group(db: AsyncSession, group_id: int) -> tuple[bool, str]:
    """Delete a proposed group; its students become ungrouped again."""
    group = await db.get(Group, group_id)
    if group is None:
        return False, "Group not found."
    if group.status != GroupStatus.proposed:
        return False, "Only proposed groups can be disbanded. Finalised groups are handled by removing the student."

    await db.delete(group)
    await db.commit()
    return True, f"Disbanded {group.label}."


async def new_group_from_leftovers(db: AsyncSession, activity_id: int) -> tuple[bool, str]:
    """Leftover option 1: put every ungrouped student into one new group."""
    activity = await get_activity_or_none(db, activity_id)
    if activity is None:
        return False, "Activity not found."

    groups = await get_groups_with_members(db, activity_id)
    grouped = grouped_student_ids(groups)
    eligible = await eligible_student_ids(db, activity_id)
    leftovers = [s for s in eligible if s not in grouped]

    if not leftovers:
        return False, "There are no ungrouped students."
    if activity.group_size > 1 and len(leftovers) == 1 and not groups:
        return False, "A single leftover student cannot form a group on their own."

    group = Group(
        activity_id=activity_id,
        label=f"Group {len(groups) + 1}",
        status=GroupStatus.proposed,
    )
    group.members = [GroupMember(student_id=s) for s in leftovers]
    db.add(group)
    await db.commit()
    return True, f"Created {group.label} from {len(leftovers)} leftover student(s)."


async def add_leftovers_to_existing(db: AsyncSession, activity_id: int) -> tuple[bool, str]:
    """Leftover option 2: spread ungrouped students across existing groups."""
    activity = await get_activity_or_none(db, activity_id)
    if activity is None:
        return False, "Activity not found."

    groups = [g for g in await get_groups_with_members(db, activity_id) if g.members]
    if not groups:
        return False, "There are no existing groups. Create a new group from the leftovers instead."

    grouped = grouped_student_ids(groups)
    eligible = await eligible_student_ids(db, activity_id)
    leftovers = [s for s in eligible if s not in grouped]
    if not leftovers:
        return False, "There are no ungrouped students."

    history = await build_pair_history(db)
    placed, _ = assign_groups(leftovers, activity.group_size, history, group_count=len(groups))

    target_for: dict[int, Group] = {}
    for index, chunk in enumerate(placed):
        target = groups[min(index, len(groups) - 1)]
        for student_id in chunk:
            target.members.append(GroupMember(student_id=student_id))
            target_for[student_id] = target

    if not target_for:
        return False, "Leftovers could not be assigned."

    await db.commit()
    spread = ", ".join(sorted({g.label for g in target_for.values()}))
    return True, f"Added {len(target_for)} leftover student(s) to {spread}."


async def finalise_groups(db: AsyncSession, activity_id: int) -> tuple[bool, str]:
    """Publish the proposal. All-or-nothing: every student must be grouped."""
    activity = await get_activity_or_none(db, activity_id)
    if activity is None:
        return False, "Activity not found."
    if activity.status != ActivityStatus.groups_proposed:
        return False, "There is no group proposal to finalise."

    groups = await get_groups_with_members(db, activity_id)
    if not groups:
        return False, "Create at least one group before finalising."

    grouped = grouped_student_ids(groups)
    eligible = await eligible_student_ids(db, activity_id)
    ungrouped = [s for s in eligible if s not in grouped]
    if ungrouped:
        return False, (
            f"{len(ungrouped)} student(s) are not in a group. "
            "Add them to a group or create a group from the leftovers first."
        )

    now = datetime.now(timezone.utc)
    for group in groups:
        group.status = GroupStatus.finalised
        group.formed_at = now
    activity.status = ActivityStatus.groups_formed
    await db.commit()
    return True, f"Published {len(groups)} group(s). Students can now see their group."


async def discard_formation(db: AsyncSession, activity_id: int) -> tuple[bool, str]:
    """Throw away a proposal and reopen the formation window."""
    activity = await get_activity_or_none(db, activity_id)
    if activity is None:
        return False, "Activity not found."
    if activity.status != ActivityStatus.groups_proposed:
        return False, "There is no group proposal to discard."

    for group in await get_groups_with_members(db, activity_id):
        await db.delete(group)
    activity.status = ActivityStatus.registration_closed
    await db.commit()
    return True, "Proposal discarded. You can start again."
