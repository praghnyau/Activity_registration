# Design Decisions

## Activity Registration and Group Formation System

This document records all resolved design decisions. Where it conflicts with other documents, this document wins.

Stack: **Python, FastAPI, Jinja2 server-rendered templates, PostgreSQL, session cookies.**

---

## Summary

| # | Topic | Decision |
|---|---|---|
| 1 | Template contract | Backend passes precomputed data and permission flags. Templates contain no business logic. |
| 2 | Withdrawal | Allowed only inside the open window: activity status is `open` and the deadline has not passed. Close registration freezes withdrawal; reopen restores it. |
| 3 | Edit limits | Fields lock progressively as the activity moves through its lifecycle. |
| 4 | Session expiry | 60 minutes idle, 8 hours absolute. Redirect to login with a message, then return to the page. |
| 5 | Dark mode | Stored in browser `localStorage`, applied before the page paints. Defaults to device setting. |
| 6 | Capacity and waitlist | Capacity is in version 1. Waitlist is out of version 1. |
| 7 | Categories | Out of version 1. |
| 8 | Forgot password | Out of version 1. Login page tells users to contact an administrator. Change password on profile is in. |
| 9 | Empty states | Defined per page — see section 9. |
| 10 | File upload placeholder | Version 1 supports resource links only. File upload arrives later in the same UI slot. |
| 11 | Leftover handling | Left to the administrator. Two options only: add leftovers to existing groups, or make a new group from them. No leave-pending, no change-group-size. |

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

## 2. Registration window, withdrawal, and close/reopen

### The open window

There is a single window during which students may both register and withdraw. It is open only when **both** conditions hold:

1. The activity status is `open` (or `full`, which still permits withdrawal), and
2. The current time is before `registration_deadline`.

Call this the **open window**. Registering, withdrawing, and re-registering are all permitted inside it and all blocked outside it. There is no separate withdrawal rule — the same two conditions govern all three actions.

### Why closing registration also freezes withdrawal

**Close registration** locks the roster. Only the students already registered at that moment take part. Because the participant list is fixed from that point, no student may remove themselves afterwards.

This makes close/reopen meaningful:

- **Close registration** — the roster freezes. New registrations blocked, withdrawals blocked. The administrator can now run group formation against a fixed list.
- **Reopen registration** — the roster unfreezes. Inside the open window, students may once again register, withdraw, or re-register.

Reopening is only permitted while the deadline has not passed, so reopening never resurrects a lapsed window.

### Action matrix

| Activity state | Deadline | Register | Withdraw |
|---|---|---|---|
| Draft | any | No — not visible to students | No |
| Open | not passed | Yes | Yes |
| Open | passed | No | No |
| Full | not passed | No — activity is full | Yes — frees a slot |
| Registration closed | not passed | No | No |
| Registration closed | passed | No | No |
| Groups proposed | any | No | No — administrator removes |
| Groups formed | any | No | No — administrator removes |
| Cancelled | any | No | No — registration already `cancelled` |
| Completed | any | No | No |

The formation cutoff still exists as a field, but it governs when group formation is finalised. It has no role in registration or withdrawal.

### What happens on withdrawal

1. The student sees a confirmation dialog stating the activity name and that they will lose their place.
2. The registration is marked `withdrawn`. The record is kept, not deleted.
3. The student is excluded from group formation and from group history calculations.
4. The registration count drops, which may return a full activity to `open`.
5. My Registrations continues to show the entry with status `withdrawn`.
6. The student may re-register only while the open window is still open. The existing record is updated back to `registered` rather than a new row being inserted.

### Nobody can leave after the window closes

Withdrawal requires `Activity.status == open` **and** the deadline still ahead. Both are checked, so
closing registration manually freezes the roster even when the deadline has not passed.

This matters because registration always closes before group formation begins. The consequence is
that the roster is frozen at exactly the moment groups are built from it, and therefore:

- a student can never withdraw while groups are proposed or finalised, and
- an administrator cannot remove a student at all.

The second point is deliberate. There is no administrative removal route. Once the roster is frozen it
is correct for the lifetime of the activity, and since every group is built from a frozen roster, a
finalised group can never lose a member. Groups therefore need no repair path, and no
`awaiting_decision` state exists.

### Backend enforcement

- Only the owner of a registration can withdraw it.
- Withdrawal checks the current status and deadline at the moment of the request, not what the page showed earlier.
- A repeated withdrawal request on an already-withdrawn registration does nothing.
- Status and deadline are both compared on the server on every request. Hiding the buttons in the template is a usability measure only and is never the enforcement.

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
| Close registration | Open or Full. Freezes the roster — blocks new registrations and withdrawals |
| Reopen registration | Registration closed, groups not yet proposed, and the registration deadline has not passed |
| Start group formation | Registration closed or after deadline has passed |
| Discard proposal | Groups proposed |
| Finalise groups | Groups proposed, and one of the two leftover options has been applied |
| Cancel | Any state before completed |
| Mark completed | After the activity's start time has passed |
| Delete | Draft only, or an activity with no registrations |

An activity with registrations is cancelled, never deleted.

### Leftover handling

Leftover students are never resolved automatically. The system proposes the complete groups, flags the remainder, and blocks finalisation until the administrator picks one of two options:

| Option | Effect |
|---|---|
| Add to existing groups | Leftovers are distributed among the already-proposed groups, making them larger than the required size |
| Create a new group from the leftovers | All leftovers go into one additional group, smaller than the required size |

Both options place every leftover student, so no student is ever left without a group and finalisation
is blocked until one of the two is chosen. There is no pending or undecided state during formation,
and no state after it either — see section 2.

**Availability.** "Add to existing groups" requires at least one complete proposed group. If the eligible students do not fill even one group, that option is not offered and the new-group option is the only way forward.

There is no "change group size for this formation" option, and no formation session is needed. Group size is a plain activity field edited under the normal edit limits, and the leftover options never write to it. A group ending up larger or smaller than the required size is an expected outcome, not an error.

Finalise groups is enabled only once one of the two options has been applied and no leftover student is unplaced.

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
| Background page request after expiry | Because the app is server-rendered, there are no true background API calls during normal navigation. This row covers any JavaScript-initiated `fetch` requests (e.g. the theme toggle saving a preference, or a future polling scenario). If such a request detects an expired session (HTTP 401 response), the page should redirect to login rather than silently failing. |

### Long forms

The Create Activity form can take time. Mitigation:
- A **Save draft** button works as a normal submission and resets the idle timer.
- The idle timeout resets on every request, so normal use does not expire the session.

### Related rules

- The CSRF token has the same lifetime as the session. A missing or invalid token shows: "That form expired. Reload the page and try again."
- If an administrator's role changes while logged in, the change takes effect on the next request. Role is read from the database each time, not trusted from the cookie.
- **Ending other sessions on password change.** Every user carries a `session_version` (an integer,
  default `1`). Login stamps the current value into the signed cookie, and each request compares the
  cookie against the database; a mismatch ends the session. Changing a password increments the value,
  which invalidates every cookie issued before the change. The response that performs the change
  re-stamps the current session's cookie, so the user stays logged in on the device they are using
  while every other device is logged out.
- **Legacy cookies are tolerated.** A cookie with no `session_version` at all is accepted rather than
  rejected, so deploying the change does not sign out every existing session at once. The trade-off is
  that a session created before the change can never be invalidated by a later password change, because
  there is no version in the cookie to compare. Requiring the key closes that hole at the cost of a
  forced global logout on deploy. Revisit once sessions are short-lived enough that this stops
  mattering.

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
2. When a registered student withdraws inside the open window, the first waitlisted student is promoted automatically.
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
| Group Formation | Fewer students than one group | "Not enough students for one complete group." Show count and group size. Show the two leftover options. | Leftover options |
| Group Formation | Not started | "Groups haven't been formed for this activity." | Start group formation button |
| Group History | None | "No group history yet." Body: "Finalised groups will appear here." | None |

### Related states

Every page also needs:
- **Loading state**: a simple centred spinner or skeleton shown while the page is fetching data. Replaces the content area until data arrives. Never shows a blank or partially rendered page.
- **Error state**: a message ("Something went wrong.") with a Retry button. Replaces the content area. Never shows a blank page. Uses the shared error state component.

These use the shared loading indicator and error state components defined in `frontend.md` section 8.

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

When file upload is added: the "File uploads aren't available yet" note is removed, and an Upload file button is added beside Add link using the same row layout. The tasks for this are tracked in `implementation-plan.md` Phase 9.

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

---

## 11. The roster is frozen once registration closes

An earlier draft of this document described an administrator removal action: an admin removes a
student, and if that student is already in a finalised group the group is flagged `awaiting_decision`
for the remaining members. That action and that state have both been removed.

The reason is that they are unnecessary, and in fact unreachable. Withdrawal is only possible while
registration is open, and no administrative removal exists. Registration closes before group formation
starts, so by the time any group is finalised every member of it has a `registered` registration that
cannot be withdrawn and cannot be touched by anyone else.

A finalised group is therefore permanent, and needs no "disrupted" concept, no decision for an
administrator to make, and no resolution path. An earlier version of this feature did add all three,
along with a `GroupMember` row that survived its student's removal purely as an audit trail.

What remains is the read-only Activity Registrations view inside Manage Activities, which shows who
is registered, their registration status, and their group if one has been formed. It offers no
mutating action.
