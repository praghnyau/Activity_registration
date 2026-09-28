# Template Contract

## Activity Registration and Group Formation System

This document defines every variable the backend must pass to each Jinja2 template. It is the integration contract between the backend developer and the frontend developer.

---

## Principles

1. The backend computes statuses, labels, and permission flags. Templates only display them.
2. Templates never decide whether a button appears by comparing dates or statuses themselves. They check a flag such as `can_register`.
3. Every page receives the global variables listed in section 1.
4. Missing optional data is passed as `None` or an empty list, never omitted entirely.
5. Dates and times are passed as real datetime objects. Templates format them with one shared Jinja filter for consistency.
6. Every form includes a `csrf_token` hidden field.

---

## 1. Global variables — every template

| Variable | Type | Contents |
|---|---|---|
| `current_user` | object | `id`, `name`, `email`, `role`, `student_id` (or `None`) |
| `flashed_messages` | list | Each item has `category` (`success`, `error`, `info`) and `text` |
| `csrf_token` | string | Must be placed as a hidden field in every form: `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`. The base template does not insert it automatically — each form is responsible. |
| `active_nav` | string | Key of the current navigation item, used to highlight the active sidebar link |
| `page_error` | object or None | Present when a page-level error occurs (e.g. activity not found, access denied). Has `code` (e.g. `404`, `403`) and `message`. When set, the template should render an error state instead of normal content. `None` on all normal page loads. |

---

## 2. Shared objects

### Status keys

These are the only valid values for each status field. The status badge component maps each key to a display label and colour role.

**Activity display status**

| Key | Display label |
|---|---|
| `draft` | Draft |
| `open` | Open |
| `full` | Full |
| `registration_closed` | Registration closed |
| `groups_proposed` | Groups proposed *(admin only)* |
| `groups_formed` | Groups formed |
| `cancelled` | Cancelled |
| `completed` | Completed |

**Registration status**

| Key | Display label |
|---|---|
| `registered` | Registered |
| `withdrawn` | Withdrawn |
| `cancelled` | Cancelled |

**Group status**

| Key | Display label |
|---|---|
| `not_yet_formed` | Not yet formed |
| `group_formed` | Group formed |
| `no_group` | No group assigned |

### Activity card object

Used on the Dashboard, Available Activities, and Closed Activities pages.

| Field | Type | Description |
|---|---|---|
| `id` | int/uuid | Activity ID |
| `title` | string | Activity title |
| `short_description` | string | Description trimmed to a maximum of 200 characters at a word boundary, with an ellipsis appended if truncated |
| `starts_at` | datetime | Date and time of the activity |
| `duration_minutes` | int | Duration |
| `location` | string or None | Venue or meeting link |
| `group_size` | int | Required students per group |
| `registration_deadline` | datetime | Registration deadline |
| `display_status` | string | Activity display status key |
| `my_registration_status` | string or None | Registration status key for the current student, or `None` |
| `can_register` | bool | True only if the student may register right now |
| `closure_reason` | string or None | Closed Activities only: `registration_closed`, `cancelled`, or `completed` |

---

## 3. Authentication

### Login page — `auth/login.html`

| Variable | Type | Contents |
|---|---|---|
| `form_errors` | dict or None | Field-level errors and a `general` key for overall error message |
| `next_url` | string or None | Safe internal path to return to after login |

---

## 4. Student pages

### Dashboard — `student/dashboard.html`

| Variable | Type | Contents |
|---|---|---|
| `stats` | object | `available_count`, `registered_count`, `groups_formed_count` |
| `upcoming_activities` | list | List of activity card objects |
| `attention_items` | list | Registrations whose group is `not_yet_formed`. Each item has `activity_id`, `activity_title`, `starts_at`, `registration_status`, `group_status` |

---

### Available Activities — `student/activities.html`

| Variable | Type | Contents |
|---|---|---|
| `activities` | list | List of activity card objects |
| `filters` | object | Current `q` (search text), `date_from`, `availability` |
| `pagination` | object | `page`, `total_pages`, `total_items` |

---

### Activity Details — `student/activity_detail.html`

| Variable | Type | Contents |
|---|---|---|
| `activity` | object | All activity fields: `id`, `title`, `description`, `starts_at`, `duration_minutes`, `location`, `group_size`, `capacity`, `registration_deadline`, `formation_cutoff`, `display_status` |
| `resources` | list | Each item: `title`, `kind` (`link` or `file`), `url` |
| `my_registration` | object or None | `id`, `status`, `registered_at`, `group_status`, `group_label` |
| `can_register` | bool | True if registration is currently allowed for this student |
| `register_blocked_reason` | string or None | Human-readable reason registration is blocked |
| `can_withdraw` | bool | True if withdrawal is currently allowed |
| `withdraw_blocked_reason` | string or None | Human-readable reason withdrawal is blocked |
| `prefill` | object | `name` and `email` from the student's account (read-only display) |

---

### Registration Confirmation — `student/registration_confirm.html`

| Variable | Type | Contents |
|---|---|---|
| `registration` | object | `registered_at`, `status` |
| `activity` | object | `id`, `title`, `starts_at` |
| `group_status` | string | Group status key |

---

### My Registrations — `student/my_registrations.html`

| Variable | Type | Contents |
|---|---|---|
| `registrations` | list | See registration entry object below |
| `filters` | object | `q` (search text) |
| `pagination` | object | `page`, `total_pages`, `total_items` |

**Registration entry object**

| Field | Type | Description |
|---|---|---|
| `registration_id` | int/uuid | Registration ID |
| `activity` | object | `id`, `title`, `starts_at`, `display_status` |
| `registered_at` | datetime | When the student registered |
| `registration_status` | string | Registration status key |
| `group_status` | string | Group status key |
| `group_summary` | object or None | `label` and `member_count` if group is formed; otherwise `None` |
| `can_withdraw` | bool | True if withdrawal is currently allowed |
| `withdraw_blocked_reason` | string or None | Human-readable reason, or `None` |

---

### My Groups — `student/my_groups.html`

| Variable | Type | Contents |
|---|---|---|
| `groups` | list | See group entry object below |

**Group entry object**

| Field | Type | Description |
|---|---|---|
| `activity` | object | `id`, `title`, `starts_at` |
| `group_label` | string | e.g. "Group 2" |
| `group_size` | int | Required group size |
| `member_count` | int | Actual number of members |
| `status` | string | Group status key |
| `members` | list of strings | Member names — only when status is `group_formed`; empty list otherwise |
| `instructions` | string or None | Meeting details or instructions |

---

### Closed Activities — `student/closed_activities.html`

| Variable | Type | Contents |
|---|---|---|
| `activities` | list | List of activity card objects, each with `closure_reason` set |
| `filters` | object | `q`, `date_from`, `closure_reason` |
| `pagination` | object | `page`, `total_pages`, `total_items` |

**`closure_reason`** is the activity status, restricted to `registration_closed`, `cancelled` or
`completed`. The template supplies its own `closure_labels` map for these three values, so the
backend does not need to send one.

---

### Profile — `student/profile.html`

| Variable | Type | Contents |
|---|---|---|
| `user` | object | `name`, `email`, `student_id`, `role` |
| `password_form_errors` | dict or None | Errors for the change-password form, keyed by field name; `None` if no submission attempted |

---

## 5. Administrator pages

### Admin Dashboard — `admin/dashboard.html`

| Variable | Type | Contents |
|---|---|---|
| `stats` | object | `total_activities`, `open_activities`, `total_registrations`, `awaiting_formation_count`, `unresolved_count` |
| `recent_activities` | list | Recently created or updated activities: `id`, `title`, `display_status`, `updated_at` |
| `attention_items` | list | Activities needing action: `id`, `title`, `display_status`, `reason` (e.g. "Ready for group formation") |

---

### Create / Edit Activity — `admin/activity_form.html`

| Variable | Type | Contents |
|---|---|---|
| `mode` | string | `create` or `edit` |
| `activity` | object or None | Existing field values when editing; `None` when creating |
| `field_errors` | dict | Errors keyed by field name; empty dict if no errors |
| `editable_fields` | set of strings | Field names the administrator may change right now |
| `locked_reasons` | dict | For each locked field name, a short human-readable explanation |
| `resource_links` | list | Existing resource link objects: `id`, `title`, `url` |
| `can_publish` | bool | True if all required fields are valid and the activity can be published |

---

### Manage Activities — `admin/manage_activities.html`

| Variable | Type | Contents |
|---|---|---|
| `rows` | list | See activity row object below |
| `filters` | object | `q`, `status` |
| `pagination` | object | `page`, `total_pages`, `total_items` |

**Activity row object**

| Field | Type | Description |
|---|---|---|
| `id` | int/uuid | Activity ID |
| `title` | string | Title |
| `starts_at` | datetime | Activity date and time |
| `registration_deadline` | datetime | Registration deadline |
| `registered_count` | int | Current registration count |
| `capacity` | int or None | Capacity, or `None` if unlimited |
| `group_size` | int | Required group size |
| `display_status` | string | Activity status key |
| `allowed_actions` | list of strings | Actions available right now, drawn from: `view`, `edit`, `registrations`, `close_registration`, `reopen_registration`, `cancel`, `complete`, `delete` |

---

### Activity Registrations sub-view — within `admin/manage_activities.html`

This view is rendered when the administrator selects an activity to inspect its registrations. It is not a separate template file. The variables below are passed alongside the main Manage Activities variables when the registrations sub-view is active.

| Variable | Type | Contents |
|---|---|---|
| `activity` | object | `id`, `title`, `display_status`, `capacity`, `registered_count` |
| `rows` | list | See registration row object below |

The view is read-only. Students are the only ones who can leave an activity, and only while
registration is open, so there is no removal action and no `can_remove_student` flag.

The sub-view is active when `sub_view == 'registrations'`. It is rendered from inside
`admin/manage_activities.html` as an `{% if sub_view == 'registrations' and rows is defined %}`
branch, so that template is shared by both the activity list and the registrations view. The list
context (`activities`, `pagination`, `filters`) is still supplied alongside it, as documented above.

**Registration row object**

| Field | Type | Description |
|---|---|---|
| `registration_id` | int/uuid | Registration ID |
| `student_name` | string | Student's full name |
| `student_email` | string | Student's college email |
| `registered_at` | datetime | Registration time |
| `registration_status` | string | Registration status key |
| `group_status` | string | Group status key |
| `group_label` | string or None | Group label if assigned |

---

### Group Formation — `admin/group_formation.html`

| Variable | Type | Contents |
|---|---|---|
| `activity` | object | `id`, `title`, `group_size`, `display_status` |
| `summary` | object | `eligible_count`, `complete_groups_possible`, `leftover_count`, `has_history` |
| `formation_state` | string | `not_started`, `proposed`, or `finalised` |
| `proposal` | list or None | Proposed groups when `formation_state` is `proposed`; each group has `label` and `members` (list of objects with `id` and `name`) |
| `leftovers` | list | List of leftover student objects with `id` and `name` — needed so the administrator can take action on specific students |
| `leftover_options` | list of strings | Options currently available: `add_to_existing_groups`, `new_group_from_leftovers` |
| `can_start` | bool | True if group formation can be started |
| `can_finalise` | bool | True if groups can be finalised (one of the two leftover options has been applied and no leftover is unplaced) |
| `can_discard` | bool | True if the current proposal can be discarded |

---

### Group History — `admin/group_history.html`

| Variable | Type | Contents |
|---|---|---|
| `entries` | list | See history entry object below |
| `filters` | object | `q`, `activity_id`, `date_from` |
| `pagination` | object | `page`, `total_pages`, `total_items` |

**History entry object**

| Field | Type | Description |
|---|---|---|
| `activity_title` | string | Activity name |
| `activity_date` | datetime | Activity start date |
| `group_label` | string | e.g. "Group 1" |
| `members` | list of objects | Each with `id` and `name`. The template renders these via `map(attribute='name')`, so they must be objects, not plain strings |
| `formed_at` | datetime | When the group was finalised |
| `status` | string | Group status key |

**Naming note.** The list is also supplied as `groups`, and each entry also exposes `label` as an
alias for `group_label`, because `group_history.html` uses those names. Prefer whichever pair you
are changing, and update both.

---

## 6. Form submission behaviour

Every form:
- Posts to its own route.
- Includes a `csrf_token` hidden field.
- On validation failure: the backend re-renders the same page with `field_errors` populated and previously entered values restored.
- On success: the backend redirects (Post/Redirect/Get pattern) and adds a message to `flashed_messages`.

This prevents duplicate submissions when a user refreshes after a successful POST.
