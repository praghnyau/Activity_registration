# Data Model

## Activity Registration and Group Formation System

---

## Overview

The database has seven tables. The ORM is SQLAlchemy (async) with PostgreSQL. Migrations are managed by Alembic.

```
users
activities
resources
registrations
groups
group_members
```

Group history is not a separate table. It is derived from `groups` and `group_members` where `groups.status = 'finalised'`.

---

## Tables

### users

Stores all user accounts. Role determines access.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Full name |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | College email, used to log in |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt hash — never plain text |
| `role` | ENUM(`student`, `administrator`) | NOT NULL | Access level |
| `student_id` | VARCHAR(100) | NULLABLE | Optional institutional ID |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Account creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last update time |

Notes:
- `email` is the login identifier. It must be unique across all roles.
- `password_hash` is produced by Passlib with bcrypt. The raw password is never stored or logged.
- Role is read from the database on every request. It is not trusted from the session cookie.

---

### activities

One row per activity created by an administrator.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | Unique identifier |
| `title` | VARCHAR(255) | NOT NULL | Activity name |
| `description` | TEXT | NOT NULL | Purpose and instructions |
| `starts_at` | TIMESTAMPTZ | NOT NULL | Date and time the activity takes place |
| `duration_minutes` | INTEGER | NOT NULL, > 0 | Length of the activity |
| `location` | TEXT | NULLABLE | Venue or meeting link |
| `group_size` | INTEGER | NOT NULL, > 0 | Required students per group |
| `capacity` | INTEGER | NULLABLE, >= group_size | Maximum registrations; NULL means unlimited |
| `registration_deadline` | TIMESTAMPTZ | NOT NULL | Last time to register; must be before `starts_at` |
| `formation_cutoff` | TIMESTAMPTZ | NOT NULL | When groups are finalised |
| `status` | ENUM | NOT NULL, DEFAULT `draft` | See status values below |
| `created_by` | FK → users.id | NOT NULL | Administrator who created the activity |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last update time |

**Status enum values**: `draft`, `open`, `full`, `registration_closed`, `groups_proposed`, `groups_formed`, `cancelled`, `completed`

Notes:
- `full` is computed from the current registration count vs capacity. It is stored to avoid repeated counts, but must be recalculated when registrations change.
- `groups_proposed` is only visible to administrators. Students never see this status.
- No `category` column. Categories are out of version 1.

---

### resources

Resource links attached to an activity. Up to 5 per activity.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | Unique identifier |
| `activity_id` | FK → activities.id | NOT NULL, ON DELETE CASCADE | The activity it belongs to |
| `kind` | ENUM(`link`, `file`) | NOT NULL, DEFAULT `link` | Version 1 uses `link` only |
| `title` | VARCHAR(255) | NOT NULL | Display name |
| `url` | TEXT | NOT NULL | Must start with `https://` |
| `file_name` | VARCHAR(255) | NULLABLE | Reserved for future file upload |
| `file_type` | VARCHAR(100) | NULLABLE | Reserved for future file upload |
| `file_size_bytes` | INTEGER | NULLABLE | Reserved for future file upload |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation time |

Notes:
- Version 1 uses only `kind = 'link'`, `title`, and `url`.
- The file columns are reserved so the schema does not need to change when file upload is added.
- `url` must pass validation: starts with `https://`.

---

### registrations

One row per student per activity. A student can have at most one non-withdrawn registration for a given activity.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | Unique identifier |
| `student_id` | FK → users.id | NOT NULL | The registering student |
| `activity_id` | FK → activities.id | NOT NULL, ON DELETE CASCADE | The activity |
| `status` | ENUM(`registered`, `withdrawn`, `cancelled`) | NOT NULL, DEFAULT `registered` | Registration status |
| `registered_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When the registration was created |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last status change |

**Unique constraint**: `(student_id, activity_id)` — one record per student per activity. Re-registration after withdrawal updates this record back to `registered` rather than inserting a new row.

Notes:
- `waitlisted` is reserved for a future version and is not a valid status in version 1.
- Withdrawn and cancelled records are kept for history and reporting. They are never deleted.
- Only registrations with `status = 'registered'` count toward capacity.

---

### groups

One row per group per activity.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID or BIGSERIAL | PK | Unique identifier |
| `activity_id` | FK → activities.id | NOT NULL, ON DELETE CASCADE | The activity |
| `label` | VARCHAR(100) | NOT NULL | Display label, e.g. "Group 1" |
| `status` | ENUM(`proposed`, `finalised`) | NOT NULL | Proposal state |
| `formed_at` | TIMESTAMPTZ | NULLABLE | Set when status becomes `finalised` |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation time |

Notes:
- `proposed` groups are only visible to administrators.
- `finalised` groups are visible to their members.
- All groups for an activity are saved in a single transaction. If the transaction fails, no rows are inserted and no student is shown as assigned.
- When a proposal is discarded, all `proposed` groups for the activity are deleted.

---

### group_members

Maps students to groups. One row per student per group.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `group_id` | FK → groups.id | NOT NULL, ON DELETE CASCADE | The group |
| `student_id` | FK → users.id | NOT NULL | The member |

**Primary key**: `(group_id, student_id)`

**Additional constraint**: a student can belong to at most one finalised group per activity. Enforced by the application layer during formation.

---

## Relationships

```
users (1) ──< registrations (N)     one student, many registrations
activities (1) ──< registrations (N) one activity, many registrations
activities (1) ──< resources (N)     one activity, many resource links
activities (1) ──< groups (N)        one activity, many groups
groups (1) ──< group_members (N)     one group, many members
users (1) ──< group_members (N)      one student, many group memberships
users (1) ──< activities (N)         one administrator, many created activities
```

---

## Group history

Group history is not a separate table. It is derived by querying finalised groups:

```sql
SELECT
    g.activity_id,
    g.label,
    g.formed_at,
    gm.student_id
FROM groups g
JOIN group_members gm ON gm.group_id = g.id
WHERE g.status = 'finalised'
ORDER BY g.formed_at DESC;
```

Previous pairs are derived by self-joining `group_members` on `group_id`:

```sql
SELECT
    gm1.student_id AS student_a,
    gm2.student_id AS student_b,
    COUNT(*) AS times_together
FROM group_members gm1
JOIN group_members gm2 ON gm1.group_id = gm2.group_id AND gm1.student_id < gm2.student_id
JOIN groups g ON g.id = gm1.group_id AND g.status = 'finalised'
GROUP BY gm1.student_id, gm2.student_id;
```

---

## Indexes

Recommended indexes beyond primary keys:

| Table | Column(s) | Reason |
|---|---|---|
| `users` | `email` | Login lookup |
| `activities` | `status` | Filtering by status |
| `activities` | `starts_at` | Sorting and date filtering |
| `registrations` | `student_id` | My Registrations queries |
| `registrations` | `activity_id` | Registration count queries |
| `registrations` | `(student_id, activity_id)` | Unique constraint / duplicate check |
| `groups` | `activity_id` | Group queries per activity |
| `group_members` | `student_id` | Member lookup |

---

## Migrations

Alembic manages schema migrations. All schema changes must go through a migration file. Never apply manual SQL to a shared or production database.

Typical commands:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```
