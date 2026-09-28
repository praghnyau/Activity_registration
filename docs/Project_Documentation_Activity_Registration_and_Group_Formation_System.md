# Project Documentation

## Activity Registration and Group Formation System

---

## 1. Project overview

### 1.1 Introduction

The Activity Registration and Group Formation System is a web application for colleges that run group-based activities such as workshops, coding challenges, and design sprints. It lets students find activities, register for them, and see the group they have been assigned to. It lets administrators create activities, manage registrations, and form groups.

### 1.2 Problem statement

Organising group activities by hand causes several problems:

- Students do not always know which activities are available or when the deadlines are.
- Registrations are collected in scattered places such as forms, messages, and spreadsheets.
- Administrators must split students into groups manually, which is slow and error-prone.
- The same students end up together repeatedly, because nobody tracks who has already worked with whom.
- When the number of students does not divide evenly into groups, leftover students are easy to overlook.
- Students are unsure whether they are registered or which group they belong to.

### 1.3 Proposed solution

One system that handles the whole process:

1. Administrators publish activities with a group size, deadline, and resources.
2. Students browse, register, and track their registration.
3. The system forms groups from the registered students, preferring people who have not worked together before.
4. Administrators review and finalise the groups, and decide how to handle leftover students.
5. Students see their final group and its members.

### 1.4 Objectives

- Provide one place to discover and register for activities.
- Give students clear, accurate status information at every stage.
- Automate group formation while keeping the administrator in control.
- Reduce repeated pairings using previous group history.
- Never leave a registered student without a clear status.
- Keep the system simple enough to build and maintain as a college project.

### 1.5 Scope

**Included**

- Login with separate student and administrator roles.
- Activity creation and management.
- Student registration and tracking.
- Group formation, review, and finalisation.
- Handling of incomplete groups and leftover students.
- Group history and previous-pairing avoidance.
- Closed activities archive.
- Light and dark modes.

**Not included by default (possible future work)**

- Email or SMS notifications.
- Payment or fees.
- Chat between group members.
- Grading or attendance tracking.
- Mobile apps.

---

## 2. Users and roles

### 2.1 Student

Can:

- Log in and view their dashboard.
- Search and filter activities.
- View activity details and download resources.
- Register for open activities.
- View their registrations and statuses.
- View their assigned groups and members.
- Browse closed, cancelled, and completed activities.
- View their profile.

Cannot access administrator pages or see other students' data except the members of their own groups.

### 2.2 Administrator

Can:

- Create, edit, publish, close, cancel, and complete activities.
- Set group size, registration deadline, and formation cutoff.
- View registered students and registration counts.
- Start group formation and review the proposed groups.
- Finalise groups and resolve leftover students.
- View group history.

---

## 3. Core concepts

### 3.1 Activity

A scheduled event that students register for and complete in small groups. Each activity has a title, description, date, duration, venue or link, required group size, registration deadline, group-formation cutoff, optional capacity, attached resources, and a status.

### 3.2 Registration

A student's sign-up for an activity. A student can register for a given activity only once.

### 3.3 Group

A set of registered students assigned to work together on one activity. A group belongs to exactly one activity.

### 3.4 Group history

A record of which students were grouped together in past activities. It is used to prefer new pairings in future group formation.

### 3.5 Registration status versus group status

These are tracked separately on purpose. A student can be successfully registered while their group is not yet formed. The interface must never show a student as assigned to a group until the assignment has been saved successfully.

---

## 4. Status definitions

### 4.1 Activity status

| Status | Meaning |
|---|---|
| Draft | Saved by the administrator but not visible to students |
| Open | Published and accepting registrations |
| Full | Capacity reached (only if capacity is used) |
| Registration closed | Deadline passed or closed manually, but the activity may still be upcoming |
| Groups formed | Groups have been finalised |
| Cancelled | Cancelled by the administrator |
| Completed | The activity has taken place |

Registration closed does not mean completed. An upcoming activity can be closed to new registrations while still being scheduled.

### 4.2 Registration status

| Status | Meaning |
|---|---|
| Registered | Registration is successful |
| Waitlisted | The activity reached capacity (optional) |
| Withdrawn | The student withdrew |
| Cancelled | The activity was cancelled |

### 4.3 Group status

| Status | Meaning |
|---|---|
| Not yet formed | Group formation has not happened |
| Group formed | Members are assigned and saved |
| Awaiting decision | The number of students does not fit the required group size and needs an administrator decision |
| No group assigned | The student was not placed in a group |

---

## 5. Functional requirements

### 5.1 Authentication and access

- Users log in with a college email and password.
- Each user has a role, either student or administrator.
- After login, users are sent to the dashboard for their role.
- Every protected page and action is checked on the backend, not only hidden in the interface.
- Sessions expire, and the user is asked to log in again.

### 5.2 Activity management (administrator)

- Create an activity with all required details.
- Save as a draft and publish only when the required information is complete.
- Edit an activity, with limits once registrations exist.
- Close registration early.
- Cancel an activity.
- Mark an activity as completed.
- Attach resource files.

### 5.3 Activity discovery (student)

- See open activities as cards.
- Search and filter by date, availability, and category if used.
- Open a details page for any activity.
- See closed, cancelled, and completed activities on a separate Closed Activities page.

### 5.4 Registration

- A student can register only while registration is open.
- A confirmation step appears before submitting.
- Duplicate registration is blocked.
- Registration after the deadline is blocked.
- Registration when the activity is full is blocked or waitlisted.
- After registering, the student sees a confirmation that clearly states whether a group has been assigned.
- Withdrawal is allowed only if the activity's rules permit it.

### 5.5 Group formation

- An administrator selects an activity and starts group formation.
- The system proposes groups of the required size.
- The administrator reviews the proposal before it becomes final.
- The system flags any students who do not fit into complete groups.
- The administrator chooses how to handle them.
- Once finalised, groups are saved and become visible to students.

### 5.6 Group history

- Finalised groups are stored permanently.
- Administrators can review past groups.
- The history is used to reduce repeat pairings.

---

## 6. Group formation logic

### 6.1 Inputs

- The list of eligible registered students.
- The required group size.
- The history of previous groups.

### 6.2 Rules

1. Each eligible student is placed in at most one group per activity.
2. Groups should have the required size.
3. Students who have not worked together before are preferred in the same group.
4. Repeat pairings are allowed when avoiding them is not feasible.
5. Previous collaboration is a **soft constraint**. It must never stop groups from being formed.
6. No student is left without a clear status.

### 6.3 Approach

A simple approach is enough for a college project:

1. Build a record of previous pairs from group history.
2. Shuffle the eligible students so results are not always the same.
3. Build groups one at a time, choosing members who add the fewest repeat pairings to the group.
4. Repeat until no complete group can be made.
5. Report any remaining students.

A common way to score a group is to count how many pairs inside it have worked together before, and prefer lower counts. The exact scoring method can be chosen during implementation.

### 6.4 Leftover students

If the number of students is not divisible by the group size, some students are left over. Example: 10 students with a group size of 4 gives 2 full groups and 2 leftover students.

The administrator chooses one of the defined options:

- Allow a smaller group.
- Change the group size before formation.
- Leave the case pending for a later decision.

The chosen option is recorded. Until a decision is made, affected students show **Awaiting decision**, never a blank status.

### 6.5 Saving groups safely

Group assignments must be saved as a single all-or-nothing operation. If saving fails, no partial groups appear, and students are not shown as assigned. This protects against students seeing a group that was never saved.

### 6.6 Example

Group size 4, eight students registered, no leftovers:

| Group | Members | Status |
|---|---|---|
| Group 1 | 4 of 4 | Finalised |
| Group 2 | 4 of 4 | Finalised |

All names in this example are illustrative, not real data.

---

## 7. System architecture

### 7.1 Overview

The project uses a simple three-part structure:

| Part | Responsibility |
|---|---|
| Frontend | Pages that users see and interact with |
| Backend | Business rules, authentication, permissions, and group formation |
| Database | Stored users, activities, registrations, groups, and history |

### 7.2 Recommended technology

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Templates | Jinja (with Flask) |
| Backend | Python with Flask |
| Database | SQLite |

Flask with server-rendered templates and SQLite is enough for a college-scale project and is easy to set up and demonstrate.

### 7.3 Backend responsibilities

The backend must enforce everything that affects security or correctness:

- Authentication and password handling.
- Role-based permissions.
- Registration deadlines and capacity.
- Duplicate registration prevention.
- Valid activity dates and group sizes.
- Group formation and its validity.
- Safe saving of group results.

The frontend performs checks for convenience, but the backend never trusts them.

---

## 8. Data model

The tables below describe the information the system stores. Exact field types and names can be decided during implementation.

### 8.1 Users

| Field | Description |
|---|---|
| ID | Unique identifier |
| Name | Full name |
| College email | Used to log in, unique |
| Password | Stored as a secure hash, never as plain text |
| Role | Student or administrator |
| Student ID | Optional institutional ID |

### 8.2 Activities

| Field | Description |
|---|---|
| ID | Unique identifier |
| Title | Name of the activity |
| Description | Purpose and instructions |
| Category | Optional |
| Activity date and time | When it takes place |
| Duration | Length of the activity |
| Venue or link | Location or meeting link |
| Group size | Required students per group |
| Capacity | Optional maximum registrations |
| Registration deadline | Last time to register |
| Formation cutoff | When groups are finalised |
| Status | See section 4.1 |
| Created by | Administrator who created it |
| Created and updated times | For tracking |

### 8.3 Resources

| Field | Description |
|---|---|
| ID | Unique identifier |
| Activity | The activity it belongs to |
| File name and location | The uploaded file |
| File type and size | For validation and display |

### 8.4 Registrations

| Field | Description |
|---|---|
| ID | Unique identifier |
| Student | The registering user |
| Activity | The activity registered for |
| Registration status | See section 4.2 |
| Registered at | Date and time |

A student and activity pair must be unique, so duplicate registrations are impossible.

### 8.5 Groups

| Field | Description |
|---|---|
| ID | Unique identifier |
| Activity | The activity the group belongs to |
| Group number | Label such as Group 1 |
| Status | Proposed or finalised |
| Formed at | Date and time of finalisation |

### 8.6 Group members

| Field | Description |
|---|---|
| Group | The group |
| Student | The member |

A student can belong to only one group per activity.

### 8.7 Group history

Group history can be derived from finalised groups and their members. Each finalised group contributes the pairs of students who worked together, along with the activity and date.

### 8.8 Relationships

- One activity has many registrations, resources, and groups.
- One student has many registrations.
- One group has many members.
- One student can belong to many groups, but only one per activity.

---

## 9. User workflows

### 9.1 Student workflow

1. Log in.
2. Browse available activities.
3. Open an activity to see details and resources.
4. Register and confirm.
5. See a confirmation that states whether a group is assigned.
6. Track status under My Registrations.
7. See the assigned group and members under My Groups after finalisation.
8. Revisit past activities under Closed Activities.

### 9.2 Administrator workflow

1. Log in.
2. Create an activity and save it as a draft.
3. Publish the activity.
4. Monitor registrations.
5. Close registration when the deadline passes or when needed.
6. Start group formation.
7. Review proposed groups and leftover students.
8. Resolve leftovers and finalise groups.
9. Mark the activity as completed afterwards.

### 9.3 Activity lifecycle

Draft → Open → Registration closed → Groups formed → Completed

An activity can be cancelled at any point before completion.

---

## 10. Frontend summary

The frontend has two interfaces, one for students and one for administrators, sharing the same branding.

### 10.1 Student pages

Login, Dashboard, Available Activities, Activity Details, Registration Confirmation, My Registrations, My Groups, Closed Activities, and My Profile.

### 10.2 Administrator pages

Admin Dashboard, Create/Edit Activity, Manage Activities and Registrations, Group Formation, and Group History.

### 10.3 Visual design

- Layout: fixed sidebar, top bar, and a main content area of rounded cards.
- Palette: burgundy and cream, with a gold accent.
- Light and dark modes with a toggle, defaulting to the device setting and remembering the user's choice.
- Status badges always include text and use colours reserved for status.
- Responsive on desktop, tablet, and mobile.

Full details are in the separate frontend documentation.

---

## 11. Security and privacy

- Passwords are stored as secure hashes.
- Every protected route checks the user's role on the backend.
- Students can see group members only for groups they belong to.
- Uploaded files are checked for allowed types and size limits.
- All input is validated on the server, whatever the frontend checked.
- Sessions expire after a period of inactivity.
- Only the data needed for the system is collected.

---

## 12. Validation rules

- Required fields must be filled in.
- The registration deadline must be before the activity starts.
- The group-formation cutoff must not conflict with the schedule.
- Duration and group size must be positive numbers.
- Capacity, if set, must be at least the group size.
- A student cannot register twice for the same activity.
- Registration is rejected after the deadline or when the activity is closed or cancelled.
- Uploaded files must match allowed types and size limits.

---

## 13. Error handling and edge cases

| Situation | Expected behaviour |
|---|---|
| Duplicate registration | Blocked, with a clear message |
| Registration after deadline | Blocked, activity shown as closed |
| Activity full | Blocked or waitlisted |
| Registrations not divisible by group size | Leftovers flagged, administrator decides |
| Too few students for one group | Flagged for an administrator decision |
| Saving groups fails | Nothing saved, no student shown as assigned |
| Activity cancelled after registrations | Registrations marked cancelled and students see the status |
| Administrator edits group size after registration | Blocked or clearly warned |
| Student withdraws before formation | Removed from the eligible list |
| Student withdraws after formation | Handled by an administrator, with the group flagged |
| Session expires | User is asked to log in again |

---

## 14. Testing plan

### 14.1 Areas to test

- Login and role-based redirects.
- Blocking of student access to admin pages.
- Activity creation and validation.
- Registration, duplicate prevention, and deadline enforcement.
- Status changes across the activity lifecycle.
- Group formation with exact multiples, leftovers, and too few students.
- Repeat-pairing avoidance using sample history.
- Safe saving of group results.
- Closed Activities display and its overlap with My Registrations.
- Light and dark modes.
- Responsive layouts on different screen sizes.

### 14.2 Sample scenarios

| Scenario | Expected result |
|---|---|
| 8 students, group size 4 | 2 complete groups |
| 10 students, group size 4 | 2 groups and 2 leftovers flagged |
| 3 students, group size 4 | No complete group, all flagged as awaiting decision |
| Two students who worked together before | Placed apart if possible |
| Not enough new pairings available | Repeat pairing allowed |
| Student registers twice | Second attempt rejected |

---

## 15. Implementation plan

1. Set up the project, database, and user roles.
2. Build login and role-based navigation.
3. Build activity creation and management for administrators.
4. Build activity browsing and details for students.
5. Implement registration and its rules.
6. Build My Registrations and My Groups.
7. Build the Closed Activities page.
8. Implement group formation, review, and leftover handling.
9. Add group history and repeat-pairing avoidance.
10. Add validation, error states, loading states, and dark mode.
11. Test with sample data and fix issues.
12. Prepare the final demonstration and documentation.

---

## 16. Limitations and future scope

**Current limitations**

- Group formation uses a simple approach, not an optimal one.
- No notifications are sent when groups are finalised.
- The system assumes one institution.

**Possible future improvements**

- Email or in-app notifications.
- Waitlist automation.
- Skill-based or interest-based grouping.
- Exporting group lists.
- Attendance and feedback collection.
- Analytics for administrators.

---

## 17. Conclusion

The Activity Registration and Group Formation System replaces manual, scattered coordination with one clear process. Students can find activities, register, and see their group. Administrators can manage activities and form groups fairly, while the system encourages new collaborations and handles incomplete groups openly. The main design principle is a straightforward student journey: find an activity, view details, register, track the registration, and view the assigned group.
