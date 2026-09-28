# Implementation Plan

## Activity Registration and Group Formation System

---

## Overview

The build is split into phases. Each phase produces something testable before the next begins. Frontend and backend work on each phase together so integration happens incrementally rather than all at once.

---

## Phase 1 — Foundation

**Goal**: The app runs, users can log in, and role-based routing works.

### Backend

- [ ] Project scaffold: folder structure, `requirements.txt`, `.env.example`, Alembic config
- [ ] `.gitignore` set up to exclude `.env`, `__pycache__`, `.venv`, and any local SQLite files. Verify `.env` is never committed.
- [ ] `.env.example` committed with placeholder values for all required keys (`DATABASE_URL`, `SESSION_SECRET_KEY`, `DEBUG`)
- [ ] Database connection: async SQLAlchemy engine and session factory
- [ ] All ORM models: `users`, `activities`, `resources`, `registrations`, `groups`, `group_members`
- [ ] Initial Alembic migration
- [ ] Session middleware setup (itsdangerous signed cookie)
- [ ] Auth router: `GET /login`, `POST /login`, `POST /logout`
- [ ] Role-based dependency: a reusable FastAPI dependency that checks the session and returns the current user
- [ ] Student guard dependency: blocks non-students
- [ ] Admin guard dependency: blocks non-administrators
- [ ] Student dashboard route (stub — returns empty data)
- [ ] Admin dashboard route (stub — returns empty data)
- [ ] Seed script: creates one administrator and a few student accounts for testing

### Frontend

- [ ] CSS custom properties for both light and dark mode (all colour tokens defined once)
- [ ] `base.html`: sidebar, top bar, flash messages, theme toggle, navigation
- [ ] Theme toggle script in `<head>` (reads `localStorage`, sets `data-theme` before paint)
- [ ] `auth/login.html`: email, password, show/hide, error messages, "contact administrator" line
- [ ] Student `base.html` sidebar navigation
- [ ] Admin `base.html` sidebar navigation
- [ ] Stub student dashboard
- [ ] Stub admin dashboard

**Done when**: An administrator and a student can log in, are redirected to different dashboards, and cannot reach each other's pages by typing a URL.

---

## Phase 2 — Activity management

**Goal**: Administrators can create, edit, publish, and manage activities. Students can browse and view them.

### Backend

- [x] Activity service: create, read, status transitions
- [x] Admin router: `GET /admin/activities`, `GET/POST /admin/activities/new`
- [x] Status action routes: publish, close registration, cancel, complete
- [x] Close registration freezes withdrawals; reopen restores them while the deadline has not passed
- [x] Resource links saved with the activity (up to 5 per activity, link only)
- [x] Student router: `GET /activities` (open activities only), `GET /activities/{id}`
- [x] Activity card objects constructed by the backend with `can_register` computed
- [x] Dashboard `attention_items` (supplied in Phase 6, previously hardcoded `[]`)

### Not built

- [ ] Activity **edit** route. `activity_service.update_activity` exists but is not wired to any
      route, so a published or formed activity cannot currently be edited. `GET/POST
      /admin/activities/{id}/edit` is missing entirely.
- [ ] **Reopen** route. Once `open → registration_closed`, the only way back is a database edit.
- [ ] **Delete** route for activities.
- [ ] Field editability enforcement. There is no `editable_fields` concept anywhere in `app/` yet —
      it has to be introduced together with the edit route, not before.
- [ ] `open → registration_closed` is not applied automatically when the deadline passes; an
      administrator has to trigger it.

### Frontend

- [x] `admin/activity_form.html`: all sections, resource link rows
- [x] `admin/manage_activities.html`: table with status badges and action buttons
- [x] Status badge components (`activity_status_badge`, `reg_status_badge`, `group_status_badge`)
- [x] `student/activities.html`: activity cards, search, date and availability filters
- [x] `student/activity_detail.html`: full detail layout, resources card, register/withdraw button
- [x] `student/registration_confirm.html`, `student/my_registrations.html`
- [ ] Locked-field display with reasons — belongs with the missing edit route above
- [ ] Empty states for Available Activities
- [ ] Pagination component

**Done when**: An administrator can create a draft, publish it, and students can see it on the Available Activities page.

---

## Phase 3 — Registration

**Goal**: Students can register and withdraw. All rules are enforced.

### Backend

- [x] Registration service: register, withdraw, re-register
- [x] Capacity enforcement with row-level locking
- [x] Duplicate registration check
- [x] Deadline enforcement
- [x] Student router: `POST /activities/{id}/register`, `POST /registrations/{id}/withdraw`
- [x] Registration Confirmation route
- [x] My Registrations route: list with registration and group status
- [x] `can_register` and `can_withdraw` flags computed per registration

### Notes and known gaps

- **Capacity is locked correctly.** `register_student` takes `SELECT … FOR UPDATE` on the `Activity`
  row before counting, which serialises concurrent registrations for the same activity, and the
  capacity count is taken inside that lock. What is *not* yet done is the Phase 7 test that proves it
  under real concurrency — the behaviour is implemented but unverified.

- [ ] `can_withdraw` checks the deadline only. It does not check `Activity.status`, so the withdraw
      option can still be offered on an activity that is `cancelled` or `groups_formed`. Same gap in
      `registration_service.can_withdraw` and in the withdraw service itself.
- [ ] `can_register` allows re-registration when `Activity.status == full`, so a student who withdrew
      can take a slot that the capacity check in `register_student` will then reject. The button and
      the service disagree.
- [ ] Group status in My Registrations is computed by duplicated logic in `registration_service`
      rather than by the shared `group_service.group_status_for_registration`, and its member count
      includes withdrawn students. My Groups uses the correct active-member count; these two lists are
      not yet consistent with each other.

### Frontend

- [x] Registration confirmation step
- [x] `student/registration_confirm.html`: activity name, date, registration status, group status message
- [x] `student/my_registrations.html`: list with dual status badges, withdraw button, confirmation dialog
- [x] Withdraw confirmation dialog
- [x] Empty states for My Registrations


**Done when**: A student can register, see the confirmation, see their registration in My Registrations, and withdraw from an activity that permits it.

---

## Phase 4 — Group formation

**Goal**: Administrators can form groups. Students can see their assigned groups.

### Backend

- [x] Group formation service (`app/services/group_formation.py`):
  - Build previous-pair history from finalised groups. Note: this query joins `groups` and `group_members` across all past activities — it is acceptable at college scale (hundreds of students, tens of activities) without caching. If the dataset grows significantly, the pair-history lookup should be cached per formation run, not recomputed on every candidate check.
  - Shuffle eligible students
  - Greedy assignment minimising repeat pairs
  - Return proposed groups and leftovers
- [x] Formation routes: `POST /admin/activities/{id}/formation/start`, `/finalize`, `/discard`
- [x] Leftover handling: `add_to_existing_groups`, `new_group_from_leftovers` (two options only; no leave-pending, no change-group-size)
- [x] All-or-nothing transaction for group saves
- [x] Student My Groups route
- [x] Group status computed for each student registration
- [x] Manual proposal editing, as the shipped template requires: `create-group` (checkbox multi-select) and `groups/{id}/disband`

**Route names note.** The template already posts to `admin.create_group`, `admin.remove_group` and
`admin.finalize_groups`, so those names are kept. The path for the first two is
`/admin/activities/{id}/formation/create-group` and `/admin/groups/{id}/disband`.

**Leftover option naming note.** The two documented options are implemented as separate routes
(`/formation/leftovers/new-group`, `/formation/leftovers/add-to-existing`) and surfaced through the
`leftover_options` context key rather than a single dispatch route. `leftover_options` returns only
`new_group_from_leftovers` when no complete group exists, since there is nothing to add to.

### Frontend

- [x] `student/my_groups.html`: list of finalised groups with members
- [x] Group status badge on My Registrations entries
- [x] Empty states for My Groups
- [ ] `admin/group_formation.html`: summary, proposal review, leftover list, finalise/discard buttons
  - **Still needed**: the template has no "start formation" button (for `admin.start_formation`) and
    no leftover option buttons (for `admin.new_group_from_leftovers` / `admin.add_leftovers_to_existing`).
    The backend routes exist and are tested; the buttons are not in the markup yet. Manual checkbox
    group creation covers the same workflow in the meantime.
- [ ] Empty state for Group Formation specifically
- [ ] `partials/group_status_badge.html` has no `proposed` or `finalised` keys. The badge falls back to
  rendering the raw key, so the admin view shows a lowercase "proposed" with the neutral colour class
  instead of a styled badge.

**Done when**: An administrator can start formation, review the proposal, handle leftovers, finalise, and students can see their groups.

---

## Phase 5 — Closed Activities and Group History

**Goal**: The complete archive is accessible to students. Administrators can review past groups.

### Backend

- [x] Closed Activities route: activities with status `registration_closed`, `cancelled`, or `completed`, with `closure_reason`
- [x] Group History route: all finalised groups with members, filters, pagination

**`closure_reason` is not a column.** The shipped `closed_activities.html` defines its own
`closure_labels` map keyed by `registration_closed` / `cancelled` / `completed`, and its filter
dropdown offers exactly those three. So `closure_reason` is the activity status, and the service
attaches `activity.closure_reason = activity.status.value` to each card. No migration is required.

**Group History naming.** The list is supplied under both `groups` (what the template iterates) and
`entries` (what the contract names), and each entry exposes both `label` (template) and `group_label`
(contract). `status` is set to `group_formed` so the badge renders properly rather than falling
through to an unmapped raw value.

**`members` shape.** `group_history.html` does `members | map(attribute='name')`, so members are
objects with `.name`, not plain strings as the contract stated. The contract has been corrected.

### Frontend

- [x] `student/closed_activities.html`: cards with closure reason, search, filter, pagination
- [x] `admin/group_history.html`: table with filters, pagination
- [x] Empty states for both pages
- [ ] Group History pagination links do not carry `activity_id`. The route accepts the filter
  (`admin.py:109`) but `group_history.html` never includes it, so the filter would be lost on page
  change. Harmless today only because the filter is not exposed in the form. Verified still open
  while writing up Phase 6.

**Done when**: Students can browse the full archive and administrators can review past groupings.

---

## Phase 6 — Profile, password, and admin registrations view

**Goal**: Users can change their password. Administrators have the full registrations view.

### Backend

- [x] Profile route: `GET /profile`, `POST /profile/password`
- [x] Password change: verify current password, hash and save new password, end other sessions
- [x] Admin registrations route: `GET /admin/activities/{id}/registrations`
- [x] Remove student from registration route: `POST /admin/registrations/{id}/remove`
- [x] `GET /student/dashboard` populates `attention_items` (was hardcoded `[]` since Phase 3)

### Frontend

- [x] `student/profile.html`: read-only fields, change password form, error display
- [x] Admin registrations sub-view within `manage_activities.html`: student list with status badges,
      remove student action behind a confirmation dialog

**Done when**: Users can change their password and administrators can manage individual registrations.

### Implementation notes

**Ending other sessions.** `users.session_version` (migration `c7f1a9d24b60`, server default `"1"`)
is stamped into the signed cookie at login and compared against the database on every request. A
password change increments it, which invalidates every cookie minted before the change. The changing
session's own cookie is re-stamped in the same response so the user is not logged out of the browser
they are currently using.

The version comparison deliberately tolerates cookies with **no** `session_version` at all, so
deploying this does not sign out every existing session at once. Requiring the key would be stricter
but is a separate decision — see "Still open" below.

**Administrator removal.** `group_service.remove_student_registration` sets the registration to
`withdrawn` and behaves differently depending on where the activity is:

- *groups still proposed* — the proposal is deleted and `Activity.status` is reset from
  `groups_proposed` to `registration_closed`, so formation can be run again. Without the status
  reset the activity would be permanently stuck: no groups would exist, and `start_formation` only
  accepts `registration_closed`.
- *groups already finalised* — the group is left intact and the `GroupMember` row is kept as an
  audit trail. The remaining members derive the status `awaiting_decision`; the removed student
  derives `no_group` and no longer sees the group at all.

**`awaiting_decision` is derived, never stored.** `GroupStatus` has no such member and the withdrawn
registration is the signal. It is computed by `group_status_for_registration`, which resolves the
student's own group via `GroupMember` and then asks `group_is_disrupted` whether anyone in that
group is no longer registered. The lookup is scoped to the group the student is actually in — an
earlier version returned the activity's first finalised group, which reported one student's group
disruption to the students of a different group.

**Still open — needs a product decision.** `awaiting_decision` names a state but no way out of it.
There is no route, service function, or UI for dissolving and re-forming the group, replacing just
the removed student, or accepting a shrunken group as final. Until that is decided, Phase 6
intentionally shows the state rather than resolving it automatically.

---

## Phase 7 — Polish, validation, and accessibility

**Goal**: All edge cases are handled gracefully. The interface is responsive and accessible.

**Status: not started.** Phases 1–6 are implemented and verified; this is the next block of work.

### Backend

- [ ] All validation rules enforced and returning field-level errors
- [ ] CSRF protection on all form routes
- [ ] Session expiry redirect with `next_url`
- [ ] Concurrent registration race condition confirmed working

**Starting points, already identified while writing up Phase 6:**

- The locking in `register_student` is already in place (`SELECT … FOR UPDATE` on `Activity`), so
  this item is about *proving* it. A test needs two concurrent registrations against an activity
  with one remaining slot and must show exactly one success.
- `can_withdraw` and `can_register` disagree with the service layer in the two cases listed under
  Phase 3: withdrawal ignores `Activity.status`, and re-registration is offered while the activity is
  `full` but then rejected by the capacity check.
- `registration_service` still duplicates the group-status logic that Phase 6 consolidated in
  `group_service`, and counts withdrawn students as members.
- `awaiting_decision` needs a resolution path before this state can be considered handled. This is the
  one item here that is blocked on a product decision rather than on effort.

### Frontend

- [ ] All empty states implemented
- [ ] Loading indicators on pages that fetch data
- [ ] Error states with retry options
- [ ] Full responsive layout: mobile hamburger menu, single-column cards, scrollable tables
- [ ] Keyboard focus rings visible in both modes
- [ ] All status badges have text labels (not colour only)
- [ ] All form fields have labels
- [ ] Frontend validation on all forms (does not replace backend)
- [ ] Dark mode tested on every page
- [ ] CSRF token included in every form

**Done when**: Every page works correctly in both modes, on all screen sizes, with keyboard navigation.

---

## Phase 8 — Integration testing and sample data

**Goal**: The complete flow works end to end with realistic data.

- [ ] Sample data script (`app/seed.py`): 10–15 students, 3–4 activities in different states, some existing group history. Note: the `testing/` directory contains a JavaScript seed file (`testing/src/seedData.js`) used for the prototype group formation tests. The Python seed script for the real app is separate and should be created fresh — it populates the actual PostgreSQL database, not the in-memory JS store.
  - **Constraint discovered in Phase 6:** `is_valid_email_for_login` only accepts
    `@bvrithyakarta.edu.in` (or the configured admin address). Any seeded student therefore has to
    use that domain or it will be unable to log in. The `@test.local` users created by the smoke
    scripts exist for grouping tests only and can never authenticate.
- [ ] Test the full student journey: login → browse → register → check status → view group
- [ ] Test the full admin journey: create → publish → monitor → form groups → finalise
- [ ] Test edge cases from the testing plan in `project-overview.md`
- [ ] Fix any integration mismatches between frontend and backend

**Note on the admin journey.** Creating is covered, but the admin cannot currently *edit* an activity
and cannot *reopen* one that has been closed for registration — see the Phase 2 checklist. The end-to-end
admin journey has to use create and status transitions only until those exist.

---

## Appendix — Phase 9 (File upload, deferred)

This phase is deferred and not part of the version 1 build. It is documented here for reference only.

When this phase is started:

- [ ] Add allowed file types and max size to config
- [ ] Add a storage location outside the public web directory
- [ ] Add a download route with permission checks
- [ ] Safe file name handling
- [ ] Update the resource form: add Upload file button beside Add link
- [ ] Remove the "File uploads aren't available yet" note

---

## Dependency order

```
Phase 1 (Foundation)
    ↓
Phase 2 (Activities)
    ↓
Phase 3 (Registration)
    ↓
Phase 4 (Group Formation)      Phase 5 (Closed + History)
    ↓                                ↓
Phase 6 (Profile + Admin Reg)
    ↓
Phase 7 (Polish)
    ↓
Phase 8 (Integration testing)
    ↓
Phase 9 (File upload — deferred)
```

Phases 4 and 5 can start in parallel once Phase 3 is done.

---

## Integration checkpoints

At the end of each phase, the frontend and backend developer should verify together:

1. Every template variable listed in `template-contract.md` for that phase's pages is being passed.
2. All status keys used in templates match the keys defined in `design-decisions.md`.
3. All `can_*` flags are correct for the test scenarios.
4. Forms POST to the correct routes and redirect correctly on success and failure.
