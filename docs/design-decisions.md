# Design Decisions

## Activity Registration and Group Formation System

This document records all resolved design decisions. Where it conflicts with other documents, this document wins.

Stack: **Python, FastAPI, Jinja2 server-rendered templates, PostgreSQL, session cookies.**

---

## Summary

| # | Topic | Decision |
|---|---|---|
| 1 | Template contract | Backend passes precomputed data and permission flags. Templates contain no business logic. |
| 2 | Withdrawal | Allowed until the formation cutoff. Afterwards, an administrator handles it. |
| 3 | Edit limits | Fields lock progressively as the activity moves through its lifecycle. |
| 4 | Session expiry | 60 minutes idle, 8 hours absolute. Redirect to login with a message, then return to the page. |
| 5 | Dark mode | Stored in browser `localStorage`, applied before the page paints. Defaults to device setting. |
| 6 | Capacity and waitlist | Capacity is in version 1. Waitlist is out of version 1. |
| 7 | Categories | Out of version 1. |
| 8 | Forgot password | Out of version 1. Login page tells users to contact an administrator. Change password on profile is in. |
| 9 | Empty states | Defined per page — see section 9. |
| 10 | File upload placeholder | Version 1 supports resource links only. File upload arrives later in the same UI slot. |

---

## 1. Template contract

### Principles

1. The backend computes statuses, labels, and permission flags. Templates only display them.
2. Templates never decide whether a button appears by comparing dates or statuses. They check a flag such as `can_register`.
3. Every page receives the global variables: `current_user`, `flashed_messages`, `csrf_token`, `active_nav`.
4. Missing optional data is passed as `None` or an empty list, never omitted.
5. Dates and times are passed as real datetime objects. Templates format them with one shared Jinja filter.

Full variable list: see `template-contract.md`.

---

## 2. Withdrawal rules

### Who can withdraw and when

| Activity state | Student can withdraw? | Notes |
|---|---|---|
| Open | Yes | Can re-register while registration is still open |
| Registration closed, groups not yet proposed | Yes, until the formation cutoff | Cannot re-register |
| Groups proposed (admin reviewing) | No | Message: "Groups are being finalised. Contact an administrator." |
| Groups formed | No | Administrator handles it |
| Cancelled | No | Registration is already marked cancelled |
| Completed | No | Not applicable |

The formation cutoff is the hard limit. After it has passed, students can no longer withdraw themselves.

### What happens on withdrawal

1. The student sees a confirmation dialog stating the activity name and that they will lose their place.
2. The registration is marked `withdrawn`. The record is kept, not deleted.
3. The student is excluded from group formation and from group history calculations.
4. The registration count drops, which may return a full activity to `open`.
5. My Registrations continues to show the entry with status `withdrawn`.
6. If registration is still open, the student may re-register. The existing record is updated back to `registered`.

### Withdrawal after groups are proposed or formed

Students cannot do this themselves. An administrator removes the student from the Activity Registrations page. Then:

- If groups are only **proposed**: the proposal is discarded and must be regenerated.
- If groups are **finalised**: the affected group is marked `awaiting_decision`. The administrator chooses how to resolve it.
- The student's registration status becomes `withdrawn`.

### Backend enforcement

- Only the owner of a registration can withdraw it.
- Withdrawal checks the current state at the moment of the request, not what the page showed earlier.
- A repeated withdrawal request on an already-withdrawn registration does nothing.

---

## 3. Edit limits by activity state

### Principle

The more the system has committed to, the less can change. Anything that would invalidate existing registrations or proposed groups is locked.

### Field editability table

| Field | Draft | Open, no registrations | Open, has registrations | Registration closed | Groups proposed | Groups formed | Cancelled / Completed |
|---|---|---|---|---|---|---|---|
| Title | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Description | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Venue or link | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Resources | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Activity date and time | ✓ | ✓ | ✓ (warning) | ✓ (warning) | ✓ (warning) | ✓ (warning) | ✗ |
| Duration | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Registration deadline | ✓ | ✓ | Extend only | Locked | Locked | Locked | ✗ |
| Capacity | ✓ | ✓ | Increase only | Locked | Locked | Locked | ✗ |
| Group size | ✓ | ✓ | Locked | Locked | Locked | Locked | ✗ |
| Formation cutoff | ✓ | ✓ | Extend only | Extend only | Locked | Locked | ✗ |

**Warning** means the form shows: "Students have already registered. Changing the date does not notify them." (There are no notifications in version 1.)

### Allowed status actions

| Action | Allowed when |
|---|---|
| Publish | Draft, with all required fields valid |
| Close registration | Open |
| Reopen registration | Registration closed, groups not yet proposed, deadline and cutoff still valid |
| Start group formation | Registration closed or after deadline has passed |
| Discard proposal | Groups proposed |
| Finalise groups | Groups proposed, and all leftover students have a resolution |
| Cancel | Any state before completed |
| Mark completed | After the activity's start time has passed |
| Delete | Draft only, or an activity with no registrations |

An activity with registrations is cancelled, never deleted.

### Group size change workaround

Group size is locked once any registration exists. The **change group size** leftover option on the Group Formation page records a new size for this formation and re-runs the proposal. It does not edit the activity record.

### Enforcement

- Locked fields are shown as read-only with a reason from `locked_reasons`.
- The backend rejects any change to a locked field even if the request was crafted by hand. Frontend read-only display is for usability only.

---

## 4. Session expiry behaviour

### Session lifetime

- **Idle timeout**: 60 minutes without a request.
- **Absolute limit**: 8 hours from login.
- Sessions are stored in a signed, HTTP-only cookie.
- Logging out ends the session immediately.

### On expiry

| Situation | Behaviour |
|---|---|
| User opens or navigates to a page | Redirect to login with: "Your session expired. Log in again." |
| After login | Redirect to the page they wanted, using `next_url`. `next_url` must be an internal path only — no redirects to external sites. |
| Form submitted after expiry | Submission is not processed. User goes to login, then back to the form page. Entered data is lost. |
| Background page request after expiry | Response signals expiry. Page redirects to login instead of showing a broken section. |

### Long forms

The Create Activity form can take time. Mitigation:
- A **Save draft** button works as a normal submission and resets the idle timer.
- The idle timeout resets on every request, so normal use does not expire the session.

### Related rules

- The CSRF token has the same lifetime as the session. A missing or invalid token shows: "That form expired. Reload the page and try again."
- If an administrator's role changes while logged in, the change takes effect on the next request. Role is read from the database each time, not trusted from the cookie.

---

## 5. Dark mode persistence

### Mechanism

| Part | Decision |
|---|---|
| Storage | Browser `localStorage`, key: `theme`, values: `light`, `dark`, or `system` |
| Default | `system` — follows the device/browser setting on first visit |
| Applying it | A small inline script in `<head>` applies the theme before the page paints, preventing a flash |
| How colours switch | A `data-theme` attribute on the root `<html>` element. All colours are CSS custom properties with light and dark sets. |

### Controls

- **Top bar toggle** (sun/moon icon): switches between light and dark, saves the explicit choice.
- **Profile page**: three-way choice — System, Light, Dark. Choosing System returns to following the device.

### Behaviour details

- If the device setting changes while on `system`, the page follows it via a `prefers-color-scheme` media query listener.
- The choice is per browser and device. It does not sync across devices in version 1.
- If `localStorage` is unavailable, the page falls back to `system`. The toggle still works for the current session via the `data-theme` attribute.
- Choosing a theme never requires a server request.

### Flash prevention script

```html
<script>
  (function() {
    var theme = localStorage.getItem('theme') || 'system';
    if (theme === 'system') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', theme);
  })();
</script>
```

This script runs before any CSS paints the page.

---

## 6. Capacity and waitlist

### Capacity

- Capacity is **optional**. If not set, there is no registration limit.
- When set, capacity must be at least the group size.
- Only registrations with `status = 'registered'` count toward capacity. Withdrawn and cancelled registrations do not count.
- When the count reaches capacity, the activity display status becomes `full` and registration is blocked with: "This activity is full."
- The status is computed from the live count. It is not a separately stored flag that can drift.
- If a registered student withdraws, the activity returns to `open` if otherwise open.
- The registration count check and save happen as a single database operation to prevent race conditions when two students try to take the last place simultaneously.

### Waitlist — out of version 1

Version 1 has no waitlist. A full activity shows "Full". The `waitlisted` status key is reserved in the data model so it can be added later without restructuring.

**Future waitlist rules (not implemented)**:
1. First in, first out by registration time.
2. When a registered student withdraws before the formation cutoff, the first waitlisted student is promoted automatically.
3. Waitlisted students are excluded from group formation until promoted.
4. Administrators can see the waitlist on the registrations page.
5. Students see "Waitlisted" and their position.

---

## 7. Categories

**Decision: out of version 1.**

- No category field on the activity form or data model.
- No category filter. Filters are: keyword search, date, and availability (and closure reason where applicable).

**If needed later**: add a single category field to activities and a corresponding filter. No other changes required.

---

## 8. Forgot password

**Decision: out of version 1.**

- The login page shows below the password field: "Forgot your password? Contact your administrator."
- Passwords are reset by an administrator or developer outside the interface (e.g. a maintenance CLI command). Reset passwords are always stored as hashes.
- **Change password on the profile page is in version 1.** It requires:
  - Current password (to confirm identity).
  - New password entered twice (must match).
  - Minimum length enforced.
  - On success: all other active sessions for that user are immediately ended.

**If a reset flow is added later**, it requires email sending, which the project does not otherwise use, and a time-limited reset token.

---

## 9. Empty states

An empty state names the space, explains it in one line, and offers the next step when there is one. Empty states never read like errors.

### Student pages

| Page | Situation | Message | Action |
|---|---|---|---|
| Dashboard | No upcoming activities | "No upcoming activities right now." Body: "New activities will appear here when they're published." | None |
| Dashboard | No pending items | Attention section is hidden entirely | — |
| Available Activities | No open activities | "No activities are open for registration." Body: "Check back soon, or browse past activities." | Link to Closed Activities |
| Available Activities | Search/filter returns nothing | "No activities match your search." Body: "Try a different keyword or clear the filters." | Clear filters |
| Activity Details | No resources | "No resources have been attached." | None |
| My Registrations | Never registered | "You haven't registered for anything yet." Body: "Find an activity to get started." | Browse activities |
| My Registrations | Search returns nothing | "No registrations match your search." | Clear filters |
| My Groups | No groups | "You don't have a group yet." Body: "Groups appear here after an administrator forms them." | View my registrations |
| Closed Activities | None | "No closed activities yet." Body: "Past, cancelled, and closed activities will appear here." | None |
| Closed Activities | Filter returns nothing | "No closed activities match your filters." | Clear filters |

### Administrator pages

| Page | Situation | Message | Action |
|---|---|---|---|
| Admin Dashboard | No activities | "No activities yet." Body: "Create your first activity to start collecting registrations." | Create activity |
| Admin Dashboard | Nothing needs attention | "Nothing needs your attention." | None |
| Manage Activities | No activities | "No activities yet." | Create activity |
| Manage Activities | Filter returns nothing | "No activities match your filters." | Clear filters |
| Activity Registrations | No registrations | "No students have registered yet." | None |
| Group Formation | No eligible students | "There are no eligible registrations to group." | Back to registrations |
| Group Formation | Fewer students than one group | "Not enough students for one complete group." Show count and group size. Show leftover options. | Leftover options |
| Group Formation | Not started | "Groups haven't been formed for this activity." | Start group formation button |
| Group History | None | "No group history yet." Body: "Finalised groups will appear here." | None |

### Related states

Every page also needs:
- **Loading state**: a simple indicator while data loads.
- **Error state**: a message and a retry option.

These use the shared loading indicator and error state components.

---

## 10. File upload placeholder

### Approach

Resources store a `kind` field (`link` or `file`) from the start. Version 1 supports **links only**. File upload takes over the same UI slot later, so nothing in the data model or page structure has to change.

### Administrator form — Resources section

- Heading: **Resources**
- Short note: "File uploads aren't available yet. Add links to your materials instead."
- Up to **5** resource rows. Each row: **Title** (required), **URL** (required, must start with `https://`), and a remove button.
- An **Add link** button adds a row.
- Completely blank rows are ignored on save.

When file upload is added: remove the note, add an **Upload file** button beside **Add link**, using the same row layout.

### Student Activity Details page — Resources card

- Lists each resource by title.
- Links open in a new tab.
- If none: "No resources have been attached."
- The card is visible on the Closed Activities detail view too.

### Data model

The `resources` table stores: `activity_id`, `kind`, `title`, `url`, and reserved columns `file_name`, `file_type`, `file_size_bytes`. Version 1 only uses `kind = 'link'`, `title`, and `url`.

### When file upload is added

Required additions:
- Allowed file types and maximum file size.
- A storage location outside the public web directory.
- A download route that checks the user is permitted to access the activity.
- Safe file names (uploaded file names cannot be used to traverse the filesystem).
