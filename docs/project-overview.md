# Project Overview

## Activity Registration and Group Formation System

---

## 1. Introduction

The Activity Registration and Group Formation System is a web application for colleges that run group-based activities such as workshops, coding challenges, and design sprints. It lets students find activities, register for them, and see the group they have been assigned to. It lets administrators create activities, manage registrations, and form groups.

---

## 2. Problem statement

Organising group activities by hand causes several problems:

- Students do not always know which activities are available or when the deadlines are.
- Registrations are collected in scattered places such as forms, messages, and spreadsheets.
- Administrators must split students into groups manually, which is slow and error-prone.
- The same students end up together repeatedly because nobody tracks who has already worked with whom.
- When the number of students does not divide evenly into groups, leftover students are easy to overlook.
- Students are unsure whether they are registered or which group they belong to.

---

## 3. Proposed solution

One system that handles the whole process:

1. Administrators publish activities with a group size, deadline, and resources.
2. Students browse, register, and track their registration.
3. The system forms groups from the registered students, preferring people who have not worked together before.
4. Administrators review and finalise the groups, and decide how to handle leftover students.
5. Students see their final group and its members.

---

## 4. Objectives

- Provide one place to discover and register for activities.
- Give students clear, accurate status information at every stage.
- Automate group formation while keeping the administrator in control.
- Reduce repeated pairings using previous group history.
- Never leave a registered student without a clear status.
- Keep the system simple enough to build and maintain as a college project.

---

## 5. Scope

### Included in version 1

- Login with separate student and administrator roles.
- Activity creation and management.
- Student registration and tracking.
- Group formation, review, and finalisation.
- Handling of incomplete groups and leftover students.
- Group history and previous-pairing avoidance.
- Closed activities archive.
- Light and dark modes.
- Resource links attached to activities.
- Change password on profile page.

### Not included in version 1 (possible future work)

- Email or SMS notifications.
- Waitlist automation.
- File uploads (links only for now).
- Forgot-password flow.
- Categories on activities.
- Payment or fees.
- Chat between group members.
- Grading or attendance tracking.
- Mobile apps.
- Cross-device theme sync.

---

## 6. Users and roles

### Student

Can:
- Log in and view their dashboard.
- Search and filter activities.
- View activity details and download resources.
- Register for open activities.
- Withdraw from an activity (while registration is open and the deadline has not passed).
- View their registrations and statuses.
- View their assigned groups and members.
- Browse closed, cancelled, and completed activities.
- Change their password on their profile page.

Cannot access administrator pages or see other students' data except the members of their own finalised groups.

### Administrator

Can:
- Create, edit, publish, close, cancel, and complete activities.
- Set group size, registration deadline, and formation cutoff.
- Set optional capacity.
- View registered students and registration counts.
- Remove a student from a registration.
- Start group formation and review the proposed groups.
- Finalise groups and resolve leftover students.
- View group history.

---

## 7. Core concepts

### Activity

A scheduled event that students register for and complete in small groups. Each activity has a title, description, date, duration, venue or link, required group size, registration deadline, group-formation cutoff, optional capacity, resource links, and a status.

### Registration

A student's sign-up for an activity. A student can register for a given activity only once at a time.

### Group

A set of registered students assigned to work together on one activity. A group belongs to exactly one activity.

### Group history

A record of which students were grouped together in past activities. Used to prefer new pairings in future group formation.

### Registration status vs group status

These are tracked separately. A student can be successfully registered while their group is not yet formed. The interface must never show a student as assigned to a group until the assignment has been saved successfully.

---

## 8. Status definitions

### Activity display status

| Status | Meaning |
|---|---|
| `draft` | Saved by the administrator but not visible to students |
| `open` | Published and accepting registrations |
| `full` | Capacity reached |
| `registration_closed` | Deadline passed or closed manually; activity may still be upcoming |
| `groups_proposed` | Administrator has reviewed but not yet finalised — **admin-only visibility; students never see this status** |
| `groups_formed` | Groups have been finalised and are visible to students |
| `cancelled` | Cancelled by the administrator |
| `completed` | The activity has taken place |

`registration_closed` does not mean `completed`. An upcoming activity can be closed to new registrations while still being scheduled.

### Registration status

| Status | Meaning |
|---|---|
| `registered` | Registration is successful |
| `withdrawn` | The student withdrew |
| `cancelled` | The activity was cancelled |

`waitlisted` is reserved for a future version and is not produced in version 1.

### Group status

| Status | Meaning |
|---|---|
| `not_yet_formed` | Group formation has not happened |
| `group_formed` | Members are assigned and saved |
| `no_group` | The student was not placed in a group |

---

## 9. Functional requirements

### Authentication and access

- Users log in with a college email and password.
- Each user has a role: student or administrator.
- After login, users are redirected to the dashboard for their role.
- Every protected page and action is checked on the backend, not only hidden in the interface.
- Sessions expire after 60 minutes of inactivity or 8 hours absolute.
- Sessions are stored in a signed, HTTP-only cookie.
- The login page shows: "Forgot your password? Contact your administrator."
- Change password on the profile page requires the current password, the new password twice, and a minimum length. After a successful change, other sessions for that user are ended.

### Activity management (administrator)

- Create an activity with all required details.
- Save as a draft and publish only when required information is complete.
- Edit an activity, with fields locking progressively as the activity moves through its lifecycle (see design-decisions.md section 3).
- Close registration early. This freezes the roster: only students already registered take part, and no one may withdraw afterwards.
- Reopen registration if groups have not yet been proposed and the deadline has not passed. Students then once again have the option to register or withdraw.
- Cancel an activity at any point before completion.
- Mark an activity as completed after its start time has passed.
- Delete an activity only if it is a draft or has no registrations.
- Attach up to 5 resource links per activity (file upload deferred to a later version).

### Activity discovery (student)

- See open activities on the Available Activities page.
- Search by keyword and filter by date and availability.
- Open a details page for any activity.
- See closed, cancelled, and completed activities on the Closed Activities page.

### Registration

- A student can register only while registration is open and the activity is not full.
- A confirmation step appears before submitting.
- Duplicate registration is blocked.
- Registration after the deadline is blocked.
- Registration when the activity is full is blocked with the message "This activity is full."
- Capacity counts only registrations with status `registered`. Withdrawn and cancelled registrations do not count.
- The capacity check and save happen as one operation to prevent two students taking the last place simultaneously.
- After registering, the student sees a confirmation that clearly states whether a group has been assigned.
- Registering, withdrawing, and re-registering are all permitted inside one **open window**, which requires both that the activity is open (or full) and that the registration deadline has not passed. All three are blocked outside it. There is no separate withdrawal rule.
- **Closing registration freezes the roster.** Only students registered at that moment take part, and withdrawals are blocked from that point.
- **Reopening registration restores the window.** Provided groups have not been proposed and the deadline has not passed, students once again have the option to register or withdraw.
- Because registration always closes before group formation, a student can never withdraw while groups are proposed or formed, and there is no administrative removal. A finalised group is therefore permanent and never needs repairing.
- If a student withdraws and the activity was full, it returns to `open` if otherwise open.
- A withdrawn student may re-register only while the open window is still open. That updates the existing registration record back to `registered`.

### Group formation

- An administrator selects an activity and starts group formation.
- The system proposes groups of the required size using the shuffle-and-greedy algorithm.
- The administrator reviews the proposal before it becomes final.
- The system flags any students who do not fit into complete groups.
- The administrator resolves leftovers before finalising.
- Once finalised, groups are saved as one all-or-nothing operation and become visible to students.
- If saving fails, no partial groups appear and no student is shown as assigned.
- A proposed (not yet finalised) group is never shown to students.

### Leftover handling

When registrations are not divisible by the group size, the leftover students are left entirely to the administrator. The system proposes the complete groups and flags the remainder; it never resolves them on its own.

The administrator chooses one of exactly two options:

1. **Add to existing groups** — distributes the leftover students among the groups that were already proposed, making those groups larger than the required size.
2. **Create a new group from the leftovers** — puts all leftover students together in one additional group, which is smaller than the required size.

Both options place every leftover student, so no student is ever left without a group. There is no "leave pending" option — finalisation is blocked until the administrator picks one of the two options.

Neither option edits the activity's `group_size`. A group may end up larger or smaller than the required size, and that is expected.

**Example.** 11 students registered, group size 3. The system proposes 3 complete groups of 3 and flags 2 leftover students. The administrator then either:

- puts both leftovers together into a new fourth group (sizes 3, 3, 3, 2), or
- adds one leftover to two of the existing groups (sizes 4, 4, 3).

**Not included.** Changing the group size for the formation, closing or reopening registration, and leaving students unassigned are not leftover options. Group size is edited on the activity form under the normal edit limits, not from the formation screen.

### Group history

- Finalised groups are stored permanently.
- Administrators can review past groups on the Group History page.
- The history is used to reduce repeat pairings in future formations.
- Previous collaboration is a soft constraint. It must never stop groups from being formed.

---

## 10. Group formation logic

### Inputs

- The list of eligible registered students (status `registered`, not withdrawn or cancelled).
- The required group size (or the adjusted size if changed for this formation).
- The history of previous groups.

### Rules

1. Each eligible student is placed in at most one group per activity.
2. Groups should have the required size.
3. Students who have not worked together before are preferred in the same group.
4. Repeat pairings are allowed when avoiding them is not feasible.
5. Previous collaboration is a soft constraint. It must never stop groups from being formed.
6. No student is left without a clear status.

### Algorithm — shuffle-and-greedy

1. Build a record of previous pairs from group history.
2. Shuffle the eligible students so results are not always the same.
3. Build groups one at a time, choosing members who add the fewest repeat pairings to the current group.
4. Repeat until no complete group can be made.
5. Report any remaining students as leftovers.

Score a candidate group by counting how many pairs inside it have worked together before. Prefer the lowest count. The exact scoring implementation can be refined without changing the rest of the system, as long as it lives in its own function (`app/services/group_formation.py`).

### Saving groups safely

Group assignments must be saved as a single all-or-nothing database transaction. If saving fails, no partial groups appear, and students are not shown as assigned. This protects against students seeing a group that was never fully saved.

---

## 11. User workflows

### Student workflow

1. Log in.
2. Browse available activities.
3. Open an activity to see details and resources.
4. Register and confirm.
5. See a confirmation that states whether a group has been assigned.
6. Track status under My Registrations.
7. See the assigned group and members under My Groups after finalisation.
8. Revisit past activities under Closed Activities.

### Administrator workflow

1. Log in.
2. Create an activity and save it as a draft.
3. Publish the activity.
4. Monitor registrations.
5. Close registration when the deadline passes or when needed.
6. Start group formation.
7. Review proposed groups and leftover students.
8. Resolve leftovers and finalise groups.
9. Mark the activity as completed afterwards.

### Activity lifecycle

```
Draft → Open → Registration closed → Groups proposed (admin only) → Groups formed → Completed
```

An activity can be cancelled at any point before completion.

---

## 12. Security and privacy

- Passwords are stored as bcrypt hashes via Passlib. Plain text passwords are never stored or logged.
- Every protected route checks the user's role on the backend at request time.
- The role is read from the database on each request, not trusted from the session cookie.
- Students can see group members only for groups they belong to, and only after finalisation.
- Uploaded resource links must start with `https://`. Other schemes are rejected.
- All input is validated on the server regardless of what the frontend checked.
- Sessions expire after 60 minutes of inactivity or 8 hours absolute.
- After a password change, all other active sessions for that user are ended.
- Only the data needed for the system is collected.

---

## 13. Validation rules

- Required fields must be filled in.
- The registration deadline must be before the activity starts.
- The group-formation cutoff must not conflict with the schedule.
- Duration and group size must be positive numbers.
- Capacity, if set, must be at least the group size.
- A student cannot register twice for the same activity (while their registration is active).
- Registration is rejected after the deadline or when the activity is closed, full, or cancelled.
- Resource link URLs must start with `https://`. Titles are required.
- Password change requires the current password and the new password entered twice.

---

## 14. Error handling and edge cases

| Situation | Expected behaviour |
|---|---|
| Duplicate registration | Blocked with a clear message |
| Registration after deadline | Blocked, activity shown as closed |
| Activity full | Blocked with "This activity is full" |
| Registrations not divisible by group size | Leftovers flagged; administrator adds them to existing groups or makes a new group |
| Too few students for one group | No complete group proposed, so there are no existing groups to add to. Only "create a new group from the leftovers" is offered |
| Saving groups fails | Nothing saved, no student shown as assigned |
| Activity cancelled after registrations | Registrations marked cancelled, students see the status |
| Administrator edits group size after registration | Field is locked |
| Student withdraws while registration is open and the deadline has not passed | Allowed. Removed from the eligible list; activity may return to `open` if it was full |
| Student tries to withdraw after registration is closed | Blocked, even if the deadline has not passed. The roster is frozen; an administrator removes the student from the registrations page |
| Registration reopened, deadline not yet passed | Students may once again register, withdraw, or re-register |
| Registration reopened after the deadline has passed | Reopen is refused; the window stays shut |
| Administrator removes a student after groups are finalised | Registration becomes `withdrawn`; affected group marked awaiting decision |
| Session expires | User redirected to login with "Your session expired. Log in again." Then returned to the page they wanted. |
| CSRF token missing or invalid | Form not processed; message: "That form expired. Reload the page and try again." |
| Two students register for the last place simultaneously | Only one succeeds; the other sees "This activity is full." |

---

## 15. Testing plan

### Areas to test

- Login and role-based redirects.
- Blocking of student access to admin pages.
- Activity creation and validation.
- Registration, duplicate prevention, and deadline enforcement.
- Capacity enforcement and concurrent registration edge case.
- Status changes across the activity lifecycle.
- Withdrawal rules across each activity state, including that closing registration blocks withdrawal before the deadline.
- Edit-limit enforcement per activity state and field.
- Group formation with exact multiples, leftovers, and too few students.
- Both leftover-handling options.
- Repeat-pairing avoidance using sample history.
- Safe saving of group results (transaction rollback on failure).
- Closed Activities display and its overlap with My Registrations.
- Light and dark modes.
- Responsive layouts on different screen sizes.
- Session expiry redirect and return-to-page behaviour.
- CSRF protection on all forms.
- Password change: current password required, new passwords must match, minimum length enforced.
- Password change ends all other active sessions for that user.
- Three-way theme control on profile page (System / Light / Dark).
- CSRF token rejection: form shows "That form expired. Reload the page and try again."

### Sample scenarios

| Scenario | Expected result |
|---|---|
| 8 students, group size 4 | 2 complete groups |
| 11 students, group size 3 | 3 complete groups and 2 leftovers flagged; administrator places the 2 either as a new group or into existing groups |
| 3 students, group size 4 | No complete group. Only "create a new group from the leftovers" is available, producing one group of 3 |
| Two students who worked together before | Placed apart if possible |
| Not enough new pairings available | Repeat pairing allowed |
| Student registers twice | Second attempt rejected |
| Activity closed with 3 days until the deadline, student tries to withdraw | Blocked — the roster is frozen |
| Activity closed, then reopened with the deadline still ahead | Student may withdraw, and a new student may register |
| Student withdraws, activity was full | Activity returns to open |
| Session expires mid-form | Redirect to login, then back to form page; entered data lost |
