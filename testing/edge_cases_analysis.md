# Comprehensive Edge Case Analysis: Activity Registration & Group Formation System

This document covers all real edge cases in the system. Cases that cannot occur due to system design constraints have been removed with explanations.

---

## System Lifecycle (reference)

```
Activity created (draft)
    ↓
Admin publishes → status: open
    ↓
Students register or withdraw  ← ONLY in this window
    ↓
registration_deadline passes → list is LOCKED, no more register/withdraw
    ↓
Admin forms groups from the locked list
    ↓
Admin reviews proposal → finalises OR discards
    ↓
Students see their groups → Activity takes place
```

---

## Removed Cases and Why They Do Not Exist

| Removed Case | Reason It Cannot Happen |
| :--- | :--- |
| **Dropout After Group Formation** | Withdrawal is blocked after `registration_deadline`. Groups only form after that deadline. The withdrawal window is always closed before groups exist. |
| **Late Registration Post-Formation** | Registration closes at `registration_deadline`. Groups form after it. There is no open registration window once groups are being formed. |
| **Inverted Cutoff Dates** | Caught at activity creation/edit time. The form enforces `registration_deadline < formation_cutoff < starts_at`. Invalid dates never reach the database. |
| **Overwriting Manual Adjustments** | The system has no manual group editing feature. Groups are algorithm-proposed then finalised. There are no manual tweaks to overwrite. |
| **Rapid Double-Click Registration** | The Register button is disabled immediately after the first click. A second request cannot be sent. Normal system behavior, not an edge case. |
| **Re-Running Group Formation** | Once groups are proposed, the Form Groups button is replaced by Finalise and Discard. Re-formation is only possible after an explicit Discard, which is a deliberate admin action, not an accident. |

---

## 1. Registration Math & Group Division Edge Cases

| Edge Case | Condition | System Impact | Handling |
| :--- | :--- | :--- | :--- |
| **1.1 Zero Registrations** | No students registered when formation runs | Cannot form any groups | Admin notified. Options: extend deadline and re-open, or cancel activity |
| **1.2 Fewer Students Than Group Size** | Total registered N < required group size k | Cannot form even one full group | Admin flagged. Options: (1) form one partial group of size N, (2) extend deadline, (3) cancel |
| **1.3 One Leftover Student** | N mod k = 1, e.g. 10 students, group size 3 | 1 student unassigned after forming full groups | Admin options: add them to an existing group, or leave pending |
| **1.4 Multiple Leftover Students** | N mod k > 1, e.g. 11 students, group size 4 | Multiple students unassigned | Admin options: form one smaller partial group, distribute across existing groups, or leave pending |
| **1.5 Group Size of 1** | Admin sets group_size = 1 | Each student is their own group | Algorithm creates N groups of 1. Collaboration penalty skipped since there are no pairs |

---

## 2. Past Collaboration & Algorithm Edge Cases

| Edge Case | Condition | System Impact | Handling |
| :--- | :--- | :--- | :--- |
| **2.1 All Students Have Worked Together** | Every possible pair has collaborated before | No fresh pairings available | Algorithm still runs. Forms groups with minimum repeated pairings. Formation is never blocked by history |
| **2.2 New Students With No History** | Students have never been in any previous group | Collaboration score is 0 for all pairs | All pairings are equal cost. Students are shuffled and assigned freely |
| **2.3 Uneven Collaboration History** | Student A worked with B many times, B never worked with others | Risk of heavy repeat pairing for A+B | Pair count used as penalty weight. High-frequency pairs are avoided when alternatives exist |
| **2.4 Tie in Penalty Score** | Multiple group combinations have identical penalty scores | Non-deterministic output risk | Tie broken deterministically by student ID. Same input always produces same output |

---

## 3. Temporal & Lifecycle Edge Cases

| Edge Case | Condition | System Impact | Handling |
| :--- | :--- | :--- | :--- |
| **3.1 Student Withdraws Before Deadline** | Student withdraws while registration window is open | Registration status set to withdrawn, slot freed | Allowed. Record kept for history. Student can re-register before the deadline |
| **3.2 Withdrawal Attempted After Deadline** | Student tries to withdraw after registration_deadline | Registration is locked | Rejected with error: "Registration deadline has passed. Withdrawals are no longer accepted." |
| **3.3 Formation Attempted Before Deadline** | Admin runs group formation before registration_deadline | List is not final, students can still register or withdraw | System warns admin. Admin can proceed but the warning makes the risk clear |
| **3.4 Activity Cancelled With Registrations** | Admin cancels an activity that has registered students | Students left without an activity | Status set to cancelled. All registrations archived as cancelled. Students see closure reason on Closed Activities page |

---

## 4. Date Validation Rules (Enforced at Activity Creation and Edit)

These are not runtime edge cases. They are caught by form validation when an admin saves an activity. Invalid combinations are rejected before reaching the database.

| Rule | Violation | Error Message |
| :--- | :--- | :--- |
| Deadline before activity date | registration_deadline >= starts_at | "Registration deadline must be before the activity date." |
| Formation cutoff after deadline | formation_cutoff <= registration_deadline | "Formation cutoff must be after the registration deadline." |
| Formation cutoff before activity | formation_cutoff >= starts_at | "Formation cutoff must be before the activity date." |
| Positive duration | duration_minutes <= 0 | "Duration must be at least 1 minute." |
| Positive group size | group_size <= 0 | "Group size must be at least 1." |
| Capacity fits a group | capacity < group_size when set | "Capacity must be at least the group size." |

**Required date order:**
```
now  <  registration_deadline  <  formation_cutoff  <  starts_at
```

---

## 5. Data Integrity Edge Cases

| Edge Case | Condition | System Impact | Handling |
| :--- | :--- | :--- | :--- |
| **5.1 Capacity Race Condition** | Two students register simultaneously for the last available slot | Both pass the capacity check before either commits | Row-level locking ensures only one succeeds. The other receives "Activity is now full" |
| **5.2 Student in Two Groups** | Bug causes a student to appear in two groups for the same activity | Student sees contradictory assignments | Application checks before each insert. DB constraint ensures a student is in at most one finalised group per activity |
| **5.3 Partial Group Save Failure** | DB error occurs mid-way through saving a batch of groups | Some groups saved, some not — inconsistent state | All group saves for an activity are wrapped in a single transaction. Any failure rolls back everything. No partial groups are ever visible |
