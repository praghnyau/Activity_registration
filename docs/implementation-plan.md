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

- [ ] Activity service: create, read, update, status transitions
- [ ] Admin router: `GET /admin/activities`, `POST /admin/activities`, `GET /admin/activities/{id}/edit`, `POST /admin/activities/{id}/edit`
- [ ] Status action routes: publish, close registration, reopen, cancel, complete, delete
- [ ] Field editability enforcement: check `editable_fields` before applying any update
- [ ] Resource links: save, update, remove (up to 5 per activity, link only)
- [ ] Student router: `GET /activities` (open activities only), `GET /activities/{id}`
- [ ] Activity card objects constructed by the backend with `can_register` computed

### Frontend

- [ ] `admin/activity_form.html`: all sections, locked field display with reasons, resource link rows
- [ ] `admin/manage_activities.html`: table with status badges and `allowed_actions` buttons
- [ ] Status badge component (maps status key to label and colour class)
- [ ] `student/activities.html`: activity cards, search bar, date and availability filters
- [ ] `student/activity_detail.html`: full detail layout, resources card, register/withdraw button visibility
- [ ] Empty states for Available Activities
- [ ] Pagination component

**Done when**: An administrator can create a draft, publish it, and students can see it on the Available Activities page.

---

## Phase 3 — Registration

**Goal**: Students can register and withdraw. All rules are enforced.

### Backend

- [ ] Registration service: register, withdraw, re-register
- [ ] Capacity enforcement with row-level locking (prevents race condition)
- [ ] Duplicate registration check
- [ ] Deadline enforcement
- [ ] Student router: `POST /activities/{id}/register`, `POST /registrations/{id}/withdraw`
- [ ] Registration Confirmation route
- [ ] My Registrations route: list with registration and group status
- [ ] `can_register` and `can_withdraw` flags computed per registration

### Frontend

- [ ] Registration confirmation step (dialog or confirmation page)
- [ ] `student/registration_confirm.html`: activity name, date, registration status, group status message
- [ ] `student/my_registrations.html`: list with dual status badges, withdraw button, confirmation dialog
- [ ] Withdraw confirmation dialog
- [ ] Empty states for My Registrations

**Done when**: A student can register, see the confirmation, see their registration in My Registrations, and withdraw from an activity that permits it.

---

## Phase 4 — Group formation

**Goal**: Administrators can form groups. Students can see their assigned groups.

### Backend

- [ ] Group formation service (`app/services/group_formation.py`):
  - Build previous-pair history from finalised groups. Note: this query joins `groups` and `group_members` across all past activities — it is acceptable at college scale (hundreds of students, tens of activities) without caching. If the dataset grows significantly, the pair-history lookup should be cached per formation run, not recomputed on every candidate check.
  - Shuffle eligible students
  - Greedy assignment minimising repeat pairs
  - Return proposed groups and leftovers
- [ ] Formation routes: `POST /admin/activities/{id}/formation/start`, `/finalise`, `/discard`
- [ ] Leftover handling: `smaller_group`, `change_group_size`, `leave_pending`
- [ ] All-or-nothing transaction for group saves
- [ ] Student My Groups route
- [ ] Group status computed for each student registration

### Frontend

- [ ] `admin/group_formation.html`: summary, proposal review, leftover list, leftover option buttons, finalise/discard buttons
- [ ] `student/my_groups.html`: list of finalised groups with members
- [ ] Group status badge added to My Registrations entries
- [ ] Empty states for Group Formation and My Groups

**Done when**: An administrator can start formation, review the proposal, handle leftovers, finalise, and students can see their groups.

---

## Phase 5 — Closed Activities and Group History

**Goal**: The complete archive is accessible to students. Administrators can review past groups.

### Backend

- [ ] Closed Activities route: activities with status `registration_closed`, `cancelled`, or `completed`, with `closure_reason`
- [ ] Group History route: all finalised groups with members, filters, pagination

### Frontend

- [ ] `student/closed_activities.html`: cards with closure reason, search, filter, pagination
- [ ] `admin/group_history.html`: table with filters, pagination
- [ ] Empty states for both pages

**Done when**: Students can browse the full archive and administrators can review past groupings.

---

## Phase 6 — Profile, password, and admin registrations view

**Goal**: Users can change their password. Administrators have the full registrations view.

### Backend

- [ ] Profile route: `GET /profile`, `POST /profile/password`
- [ ] Password change: verify current password, hash and save new password, end other sessions
- [ ] Admin registrations route: `GET /admin/activities/{id}/registrations`
- [ ] Remove student from registration route: `POST /admin/registrations/{id}/remove`

### Frontend

- [ ] `student/profile.html`: read-only fields, change password form, theme three-way control, error display
- [ ] Admin registrations sub-view within `manage_activities.html`: student list with status badges, remove student action

**Done when**: Users can change their password and administrators can manage individual registrations.

---

## Phase 7 — Polish, validation, and accessibility

**Goal**: All edge cases are handled gracefully. The interface is responsive and accessible.

### Backend

- [ ] All validation rules enforced and returning field-level errors
- [ ] CSRF protection on all form routes
- [ ] Session expiry redirect with `next_url`
- [ ] Concurrent registration race condition confirmed working (row-level locking verified with concurrent test)

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
- [ ] Test the full student journey: login → browse → register → check status → view group
- [ ] Test the full admin journey: create → publish → monitor → form groups → finalise
- [ ] Test edge cases from the testing plan in `project-overview.md`
- [ ] Fix any integration mismatches between frontend and backend

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
