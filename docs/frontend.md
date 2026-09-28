# Frontend Documentation

## Activity Registration and Group Formation System

---

## 1. Introduction

The frontend is the user-facing part of the application. It is built with HTML, CSS, and JavaScript, served as Jinja2 templates by the FastAPI backend. There is no separate JavaScript framework.

Students use it to discover college activities, register, track their registrations, and view their assigned groups. Administrators use a separate interface to manage activities, registrations, and group formation.

### Core student journey

```
Find an activity → View details → Register → Track registration → View assigned group
```

The Closed Activities page stays accessible from the navigation throughout this journey.

---

## 2. Design goals

- **Simple navigation** — students find activities and their registrations quickly.
- **Clear information** — dates, deadlines, group sizes, and statuses are always visible.
- **Consistent design** — every page follows the same visual style.
- **Responsive layout** — works on laptops, tablets, and mobile phones.
- **Role-based access** — students and administrators see different dashboards and navigation.
- **Clear feedback** — every important action produces a confirmation, error message, or status update.
- **Accessible design** — text is readable, buttons are clearly labelled, status is never communicated by colour alone.
- **Light and dark modes** — both modes are fully supported and equally readable.

---

## 3. Visual design

### 3.1 Design direction

The interface feels warm, traditional, and professional. The identity comes from a **burgundy and cream** palette with a gold-cream accent used sparingly.

### 3.2 Colour palette — light mode

| Role | Colour | Hex | Used for |
|---|---|---|---|
| Primary | Burgundy | `#6B1F3A` | Sidebar, primary buttons, headings on cards |
| Accent | Cream gold | `#F0D9A8` | Active navigation item, highlights |
| Page background | Warm cream | `#FAF5F0` | Main page background |
| Card surface | White | `#FFFFFF` | Cards, tables, forms |
| Text | Dark plum | `#2A1A20` | Primary text |
| Secondary text | Grey | `#6B6B66` | Dates, hints, metadata |
| Sidebar text | Light rose | `#EBCFD9` | Inactive navigation items |

### 3.3 Colour palette — dark mode

| Role | Colour | Hex | Used for |
|---|---|---|---|
| Sidebar | Deep burgundy | `#2C0F1C` | Sidebar background |
| Page background | Dark wine-brown | `#191114` | Main page background |
| Card surface | Dark plum | `#261A1F` | Cards, tables, forms |
| Text | Warm off-white | `#F3E9E4` | Primary text |
| Secondary text | Muted rose-grey | `#B9A9AF` | Dates, hints, metadata |
| Accent / primary button | Cream gold | `#F0D9A8` | Primary buttons, active navigation item |
| Text on accent | Deep burgundy | `#4A1228` | Text on gold buttons |
| Sidebar text | Muted rose | `#C9AEB9` | Inactive navigation items |

In dark mode, burgundy is too low-contrast for buttons. The primary button and active navigation item switch to the gold accent.

### 3.4 Status colours

Status colours are separate from brand colours and stay consistent on every page. Every badge must also contain a text label.

| Status meaning | Light mode (bg / text) | Dark mode (bg / text) |
|---|---|---|
| Success, Open, Group formed | `#DDF1E1` / `#1B5E2E` | `#1F3D2A` / `#9FDDB0` |
| Pending, Awaiting decision | `#FFF0D0` / `#7A4B00` | `#4A3510` / `#F2CB7A` |
| Closed, Completed | `#E8E8E4` / `#444444` | `#3A3335` / `#CFCBC8` |
| Error, Cancelled | `#FBE4E4` / `#8A1C1C` | `#4A1C1C` / `#F3A8A8` |

Rules:
1. The brand accent is never used for status badges.
2. Amber is only used for pending states.
3. Use one accent colour only. Avoid adding extra colours.
4. Status is never communicated by colour alone. Every badge contains a text label.

### 3.5 CSS implementation

All colours are defined as CSS custom properties (variables) on the root element. A theme attribute on the root switches between light and dark sets. This way switching themes changes the variables, not every individual element.

```css
/* Example structure only */
:root[data-theme="light"] { --color-primary: #6B1F3A; ... }
:root[data-theme="dark"]  { --color-primary: #F0D9A8; ... }
```

### 3.6 Layout

- A fixed sidebar on the left on desktop.
- A top bar containing the system name, the theme toggle, and the user profile menu.
- A main content area made of cards on the page background.
- On smaller screens the sidebar collapses into a hamburger menu.

### 3.7 Component style

Rounded cards, consistent spacing, readable typography, simple icons, clear buttons, search bars, filters, tables, and status badges. Avoid excessive animation, decorative elements, and unnecessary information.

---

## 4. Light and dark mode

### 4.1 Behaviour

| Aspect | Requirement |
|---|---|
| Toggle | Sun/moon button in the top bar on every page, including login |
| Default | `system` — follows the device or browser setting on first visit |
| Persistence | Stored in browser `localStorage` as `light`, `dark`, or `system` |
| Scope | Applies to all pages, forms, tables, dialogs, badges, and messages |
| Flash prevention | A small inline script in `<head>` applies the theme before the page paints |

### 4.2 Controls

- **Top bar toggle** — switches between light and dark, saves the explicit choice.
- **Profile page** — a three-way choice: System, Light, or Dark. Choosing System returns to following the device.

### 4.3 Implementation notes

- If the device setting changes while the user is on `system`, the page follows it.
- The choice is per browser and device. It does not sync across devices in version 1.
- If `localStorage` is unavailable, the page falls back to `system` and the toggle still works for the current session.
- Choosing a theme never requires a server request.
- Pure black and pure white are avoided. Warm off-white text and dark wine-brown backgrounds are used instead.

---

## 5. Navigation

### 5.1 Student navigation

| Item | Purpose |
|---|---|
| Dashboard | Overview of activities and registrations |
| Available Activities | Browse and register for activities |
| My Registrations | Track registration status |
| My Groups | View group assignments and members |
| Closed Activities | Browse closed, cancelled, and completed activities |
| My Profile / Logout | Account information and sign-out |

### 5.2 Administrator navigation

| Item | Purpose |
|---|---|
| Admin Dashboard | System overview |
| Create Activity | Add a new activity |
| Manage Activities | Edit, publish, close, cancel, complete activities, and view registrations |
| Group Formation | Run and review group formation |
| Group History | Review past group assignments |
| Logout | Sign out |

The current page is highlighted in the sidebar using the `active_nav` variable passed by the backend.

---

## 6. Student pages

### 6.1 Login page

**Elements**
- System name and a simple logo or icon.
- College email field.
- Password field with a show/hide toggle.
- Login button.
- Clear validation and error messages.
- Theme toggle.
- Line below password field: "Forgot your password? Contact your administrator."

**Behaviour**
- Students are redirected to the student dashboard after login.
- Administrators are redirected to the admin dashboard.
- The backend checks permissions on every request. Hiding links is not enough.

### 6.2 Student dashboard

**Layout**
- Welcome message with the student's name.
- Summary cards: available activities, active registrations, formed groups.
- Upcoming activities section.
- Attention section: registrations with a pending or awaiting-decision group status.
- Quick links to Available Activities, My Registrations, My Groups, and Closed Activities.

Each activity preview shows the title, date, group size, status badge, and a View Details button.

**Empty states**
- No upcoming activities: "No upcoming activities right now." Body: "New activities will appear here when they're published."
- No attention items: the attention section is hidden entirely.

### 6.3 Available Activities page

**Activity card contents**
- Title and short description.
- Date and duration.
- Venue or meeting link (if available).
- Required group size.
- Registration deadline.
- Status badge (Open, Full).
- View Details button.

**Filters**
- Search bar (keyword).
- Date filter.
- Availability filter.

No category filter (categories are out of version 1).

**Rules**
- A registration option is shown only when `can_register` is true (set by the backend).
- Activities that are full or past their deadline are labelled accordingly and have no active registration button.

**Empty states**
- No open activities: "No activities are open for registration." Body: "Check back soon, or browse past activities." Link to Closed Activities.
- Search returns nothing: "No activities match your search." Body: "Try a different keyword or clear the filters." Clear filters action.

### 6.4 Activity details page

| Field | Description |
|---|---|
| Activity title | Name |
| Description | Purpose, instructions, expectations |
| Date and time | When it takes place |
| Duration | Expected length |
| Group size | Required students per group |
| Registration deadline | Last date and time to register |
| Group-formation cutoff | When group formation is finalised |
| Resources | Resource links (title + URL, opens in new tab) |
| Venue or link | Location or meeting link |
| Status badge | Current activity status |

**Behaviour**
- When `can_register` is true: show a prominent **Register for Activity** button.
- The student's name and email are pre-filled from their account (read only).
- A confirmation step is shown before submission.
- If the student has already registered, show their current registration and group status instead of the register button.
- When `can_withdraw` is true: show a **Withdraw** button.
- When `register_blocked_reason` is set: show it below the disabled button.
- When `withdraw_blocked_reason` is set: show it below the disabled button.

**Resources empty state**: "No resources have been attached."

### 6.5 Registration confirmation page

**Contents**
- Activity name.
- Registration date.
- Registration status badge.
- Group formation status.
- Link to My Registrations.

If groups have not been formed: "Registration successful. Your group has not been assigned yet."

This message must never imply the student already has a group.

If registration fails: explain the reason (full, closed, already registered) and suggest a next step.

### 6.6 My Registrations page

**Each entry shows**
- Activity name and date.
- Date of registration.
- Registration status badge.
- Group status badge.
- Link to activity details.
- Group details when available.
- **Withdraw** button when `can_withdraw` is true, with a confirmation dialog.

**Registration status values**

| Key | Label |
|---|---|
| `registered` | Registered |
| `withdrawn` | Withdrawn |
| `cancelled` | Cancelled |

**Group status values**

| Key | Label |
|---|---|
| `not_yet_formed` | Not yet formed |
| `group_formed` | Group formed |
| `awaiting_decision` | Awaiting admin decision |
| `no_group` | No group assigned |

Registration status and group status are shown separately. A student can be registered while the group is still pending.

A student is never shown as assigned to a group until the assignment has been saved successfully.

**Empty states**
- Never registered: "You haven't registered for anything yet." Body: "Find an activity to get started." Browse activities link.
- Search returns nothing: "No registrations match your search." Clear filters action.

### 6.7 My Groups page

**Each group shows**
- Activity title and date.
- Group label (e.g. "Group 2").
- Group size (required vs actual).
- Formation status badge.
- Member names (only when the group is finalised).
- Instructions or meeting details (if provided).

Only finalised group members are ever shown. A proposed group is never shown to students.

**Empty state**: "You don't have a group yet." Body: "Groups appear here after an administrator forms them." Link to My Registrations.

### 6.8 Closed Activities page

Activities with statuses `registration_closed`, `cancelled`, or `completed` appear here.

**Each card shows**
- Title.
- Date.
- Group size.
- Closure status badge with a short explanation (e.g. "Registration deadline has passed").
- View Details button.

**Rules**
- Search and filters (keyword, date, closure reason).
- Students can still read descriptions and view resources from the details page.
- An activity can appear in both Closed Activities and My Registrations.
- `registration_closed` does not mean `completed`. An upcoming activity can be closed to new registrations and still be scheduled.

**Empty states**
- No closed activities: "No closed activities yet." Body: "Past, cancelled, and closed activities will appear here."
- Filter returns nothing: "No closed activities match your filters." Clear filters action.

### 6.9 My Profile page

- Student name.
- College email.
- Student ID (if available).
- Role.
- Theme preference (System / Light / Dark three-way control).
- Change password form: requires current password, new password, new password confirmation.

After a successful password change, all other active sessions for that user are ended.

---

## 7. Administrator pages

### 7.1 Admin Dashboard

**Stats**
- Total activities.
- Open activities.
- Total registrations.
- Activities awaiting group formation.
- Activities with unresolved cases (leftover students awaiting decision).

**Attention items**: activities needing action, with a reason such as "Ready for group formation" or "3 students awaiting decision."

**Quick actions**: Create activity, View registrations, Manage group formation.

**Empty states**
- No activities: "No activities yet." Body: "Create your first activity to start collecting registrations." Create activity action.
- Nothing needs attention: "Nothing needs your attention."

### 7.2 Create and edit activity page

The form is split into sections.

| Section | Fields |
|---|---|
| Basic details | Title, description |
| Schedule | Activity date, start time, duration |
| Registration | Registration deadline, optional capacity |
| Group formation | Required group size, formation cutoff |
| Resources | Up to 5 resource link rows (title + URL). Note: "File uploads aren't available yet. Add links to your materials instead." |
| Location | Venue or online meeting link |
| Publication | Save as draft, Publish |

**Rules**
- Required fields are clearly marked.
- Date validation: registration deadline must be before the activity start; formation cutoff must not conflict.
- `editable_fields` from the backend determines which fields are editable. Locked fields are shown as read-only with the reason from `locked_reasons`.
- Administrators can save drafts. They can publish only when all required fields are valid.
- Resource rows: each has a title (required) and a URL (must start with `https://`). Completely blank rows are ignored. An **Add link** button adds a row up to 5. Each row has a remove button.

**Edit field lock summary** (full table in design-decisions.md section 3):
- Group size locks once any registration exists.
- Registration deadline and capacity lock once registration is closed.
- All fields lock when the activity is cancelled or completed.

### 7.3 Manage activities and registrations page

**Columns**
- Activity name.
- Activity date.
- Registration deadline.
- Registered students (count / capacity).
- Group size.
- Status badge.
- Actions.

**Actions** (shown based on `allowed_actions`):
`view`, `edit`, `registrations`, `close_registration`, `reopen_registration`, `cancel`, `complete`, `delete`

**Activity Registrations view** — for a selected activity:
- Student name, email, registration date, registration status, group status, group label.
- Option to remove a student (when `can_remove_student` is true).

**Empty states**
- No activities: "No activities yet." Create activity action.
- Filter returns nothing: "No activities match your filters." Clear filters action.
- No registrations: "No students have registered yet."

### 7.4 Group Formation page

**For a selected activity, shows**
- Total eligible registrations.
- Required group size.
- Number of complete groups possible.
- Number of leftover students.
- Whether previous collaboration history is available.
- Current formation state (`not_started`, `proposed`, `finalised`).

**Workflow**
1. Administrator starts group formation (when `can_start` is true).
2. System proposes groups.
3. Administrator reviews proposed groups and any leftover students.
4. Administrator resolves leftovers using available options from `leftover_options`.
5. Administrator finalises (when `can_finalise` is true — all leftovers resolved).
6. Administrator can discard the proposal (when `can_discard` is true) to start again.

**Leftover options shown as buttons**
- Allow a smaller group.
- Change group size for this formation (re-runs proposal with new size).
- Leave pending (sets affected students to `awaiting_decision`).

All leftovers must have a decision before finalisation is enabled.

**Empty states**
- No eligible students: "There are no eligible registrations to group."
- Fewer students than one group: "Not enough students for one complete group." Show count and group size. Show leftover options.
- Not started: "Groups haven't been formed for this activity." Show Start group formation button.

### 7.5 Group History page

**Displays**
- Activity name and date.
- Group label.
- Members.
- Formation date.
- Status badge.

**Filters**: keyword, activity, date range.

**Empty state**: "No group history yet." Body: "Finalised groups will appear here."

---

## 8. Reusable components

| Component | Purpose |
|---|---|
| Activity card | Used on Dashboard, Available Activities, Closed Activities |
| Status badge | Displays a status key as a coloured label with text |
| Search and filter bar | Keyword search + filter dropdowns |
| Confirmation dialog | Shown before destructive or irreversible actions |
| Form field | Label, input, error message, locked state |
| Empty state | Illustration, message, and optional action |
| Loading indicator | Shown while data loads |
| Error state | Message with a retry option |
| Notification / flash message | Success, error, and info messages from flashed_messages |
| Theme toggle | Sun/moon button that writes to localStorage and updates the theme attribute |
| Pagination | Page controls for lists |

---

## 9. Feedback and status handling

| User action | Expected frontend response |
|---|---|
| Login succeeds | Redirect to the appropriate dashboard |
| Login fails | Show a clear error message |
| Registration succeeds | Show confirmation page, update My Registrations |
| Duplicate registration attempted | Explain that the student is already registered |
| Registration deadline passes | Disable registration, show closed status |
| Activity full | Show "Full" badge, disable registration |
| Group formation completes | Show assigned group and members |
| Group formation has leftovers | Show pending or awaiting-decision status |
| Activity cancelled | Show cancellation status |
| Data loading | Show loading indicator |
| No activities available | Show empty state message |
| Session expires | Redirect to login: "Your session expired. Log in again." Return to original page after login. |
| CSRF token missing or expired | "That form expired. Reload the page and try again." |
| Network request fails | Show error message and a retry option |

---

## 10. Responsive design

| Screen | Behaviour |
|---|---|
| Desktop | Persistent sidebar, multi-column activity cards |
| Tablet | Narrower sidebar, fewer cards per row |
| Mobile | Collapsible hamburger navigation, single-column cards, forms that fit screen width |

Tables on small screens either scroll horizontally or become compact card layouts. Buttons and form controls are large enough for touchscreens.

---

## 11. Validation and accessibility

### Frontend validation

Before submission, the frontend validates:
- Required login fields.
- Required activity fields.
- Valid dates and times (deadline before activity start, etc.).
- Positive duration and group size.
- Resource link URLs start with `https://`, titles are present.
- Password change: current password present, new passwords match, minimum length.

These checks improve usability but do not replace backend validation.

### Accessibility

- Clear field labels on all inputs.
- Visible keyboard focus rings in both light and dark mode.
- Readable contrast in both modes (status colours are tuned separately per mode).
- Descriptive button text (not just "Submit" or "OK").
- Helpful, specific error messages.
- No error or status communicated by colour alone — every badge has a text label.
- Forms are keyboard-navigable.

---

## 12. Page structure

```
templates/
├── base.html               # Shared layout: sidebar, top bar, flash messages, theme script
├── auth/
│   └── login.html
├── student/
│   ├── dashboard.html
│   ├── activities.html
│   ├── activity_detail.html
│   ├── registration_confirm.html
│   ├── my_registrations.html
│   ├── my_groups.html
│   ├── closed_activities.html
│   └── profile.html
└── admin/
    ├── dashboard.html
    ├── activity_form.html
    ├── manage_activities.html
    ├── registrations.html
    ├── group_formation.html
    └── group_history.html
```

---

## 13. Development sequence

1. Shared layout, CSS variables (light/dark), navigation, theme toggle, login page.
2. Student dashboard and Available Activities page.
3. Activity Details and Registration Confirmation.
4. My Registrations and My Groups.
5. Closed Activities page.
6. Admin dashboard and activity form.
7. Manage Activities and Registrations view.
8. Group Formation and Group History.
9. Responsive styling, validation, loading states, error states, accessibility checks.
10. Connect to backend and test with sample data.
