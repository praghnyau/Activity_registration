# Comprehensive Edge Case Analysis: Activity Registration & Group Formation System

This document provides an exhaustive breakdown of all possible edge cases in the system, along with expected system behavior and resolution strategies.

---

## 1. Registration Math & Group Division Edge Cases

| Edge Case Scenario | Condition | System Impact | Proposed Handling / Resolution Strategy |
| :--- | :--- | :--- | :--- |
| **1.1 Zero Registrations** | $N = 0$ at cutoff date | Cannot form any groups. | Activity status transitions to `CANCELLED_NO_REGISTRATIONS`. Admin is notified. No groups generated. |
| **1.2 Insufficient Students ($N < k$)** | Total registrations $N$ is less than required group size $k$. | Cannot form even 1 full group. | Flagged as `UNDERFILLED_COHORT`. Admin prompted with 3 options: (1) Form 1 partial group of size $N$, (2) Extend deadline, (3) Cancel activity. |
| **1.3 Single Leftover Student ($R = N \pmod k = 1$)** | e.g. 10 students registered, group size $k=3$. | 1 student remains unassigned. | System flags activity with `REMAINDER_ATTENTION`. Admin options: Auto-distribute (+1 to a group of 3), Waitlist, Manual Assign. |
| **1.4 Multiple Leftover Students ($1 < R < k$)** | e.g. 11 students, group size $k=4$. | 3 students remain unassigned. | System flags activity. Admin options: Form Partial Group, Auto-distribute, Manual Drag-and-Drop. |
| **1.5 Single-Person Groups ($k = 1$)** | Group size explicitly set to 1. | Individual activity. | Algorithm creates $N$ individual "groups" of 1. Collaboration penalty calculation skipped. |

---

## 2. Past Collaboration & Algorithm Edge Cases

| Edge Case Scenario | Condition | System Impact | Proposed Handling / Resolution Strategy |
| :--- | :--- | :--- | :--- |
| **2.1 Complete Clique (Dense History)** | All $N$ registered students have already worked together in past activities. | Zero "fresh pairing" options. | Algorithm calculates minimum collision density and forms groups with minimal repeated pairings. |
| **2.2 Cold-Start / New Students** | Students with zero prior activity history join. | Collaboration matrix $C(u, v) = 0$. | New students are distributed evenly across groups to foster integration. |
| **2.3 Asymmetric / Uneven History** | Student A worked with B 5 times, but B never worked with C, D, E. | Risk of heavy repeat pairing. | Penalty matrix uses weighted costs to strongly isolate high-frequency pairs. |
| **2.4 Exact Tie-Breaker Conditions** | Multiple grouping combinations yield same cost. | Risk of non-deterministic output. | Deterministic sorting by student ID guarantees identical output given identical inputs. |

---

## 3. Temporal, Cutoff & Lifecycle Edge Cases

| Edge Case Scenario | Condition | System Impact | Proposed Handling / Resolution Strategy |
| :--- | :--- | :--- | :--- |
| **3.1 Dropout After Group Formation** | Student unregisters after groups formed. | Group size shrinks to $k-1$. | Group status set to `INCOMPLETE_GROUP`. Admin alerted to auto-pull replacement or merge. |
| **3.2 Late Registration Post-Formation** | Student registers after groups formed. | Student unassigned. | Added to `UNASSIGNED` queue for Admin review. |
| **3.3 Inverted Cutoff Dates** | Cutoff date earlier than reg deadline. | Conflict in lifecycle. | Validation rule enforces: `registrationDeadline <= groupCutoffDate <= activityDate`. |
| **3.4 Cancelled Activity** | Admin cancels activity with groups formed. | Orphaned assignments. | Status set to `CANCELLED`. Registrations and assignments archived. |

---

## 4. Concurrency & Data Integrity Edge Cases

| Edge Case Scenario | Condition | System Impact | Proposed Handling / Resolution Strategy |
| :--- | :--- | :--- | :--- |
| **4.1 Rapid Double-Click Registration** | Student clicks "Register" twice rapidly. | Duplicate rows. | Unique DB constraint `(activity_id, student_id)` + UI debounce. |
| **4.2 Re-Running Group Formation** | Admin clicks "Form Groups" again. | Risk of duplicate groups. | Idempotent execution: clears previous auto-generated groups for that activity first. |
| **4.3 Overwriting Manual Adjustments** | Admin made manual tweaks, then clicks re-run. | Loss of custom edits. | Warning confirmation modal: option to overwrite or lock manually assigned students. |
| **4.4 Multiple Group Assignment Contradiction** | Student assigned to Group 1 AND Group 2. | Duplicate assignment. | Integrity check during group assignment save assertions. |
