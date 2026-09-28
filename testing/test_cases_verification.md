# Test Case Verification Matrix: Activity Registration & Group Formation System

This document outlines the complete test suite to verify that every identified edge case is properly solved and handled by the system logic.

---

## 1. Registration Math & Group Division Test Suite

### TC-01: Zero Registrations at Cutoff Date ($N=0$)
- **Category**: Division Math
- **Expected Outcome**: Status set to `CANCELLED_NO_REGISTRATIONS`; zero groups created.

### TC-02: Insufficient Students ($N < k$)
- **Category**: Division Math
- **Expected Outcome**: Status set to `UNDERFILLED_COHORT`; Admin prompted with partial group / deadline / cancel options.

### TC-03: Single Leftover Student ($R = N \pmod k = 1$)
- **Category**: Remainder Handling
- **Expected Outcome**: Creates $M$ full groups + 1 leftover student; Auto-distribute strategy expands 1 group to size $k+1$.

### TC-04: Multiple Leftover Students ($1 < R < k$)
- **Category**: Remainder Handling
- **Expected Outcome**: Creates $M$ full groups + $R$ leftover students; Partial group strategy creates group of size $R$.

### TC-05: Single-Person Group Configuration ($k = 1$)
- **Category**: Boundary Test
- **Expected Outcome**: Creates $N$ individual 1-person groups without collision check overhead.

---

## 2. Past Collaboration Algorithm Test Suite

### TC-06: Minimal Repeat Pairing Optimization
- **Category**: Algorithm Quality
- **Expected Outcome**: Separates past teammates into different groups whenever novel pairing alternatives exist.

### TC-07: Complete Clique / Dense History Fallback
- **Category**: Algorithm Boundary
- **Expected Outcome**: Minimizes repeat collisions without error or lockup.

### TC-08: Cold-Start / New Student Integration
- **Category**: Diversity / Cold-Start
- **Expected Outcome**: Distributes new students evenly across groups.

### TC-09: Idempotency & Repeatability
- **Category**: Algorithm Safety
- **Expected Outcome**: Re-running group formation produces identical output and replaces previous groups cleanly.

---

## 3. Temporal, Cutoff & Lifecycle Test Suite

### TC-10: Student Unregisters Post-Formation (Dropout)
- **Category**: Lifecycle Edge Case
- **Expected Outcome**: Student set to `UNREGISTERED`; group flagged `INCOMPLETE`.

### TC-11: Late Registration Post-Formation
- **Category**: Lifecycle Edge Case
- **Expected Outcome**: Student registered in `UNASSIGNED` queue for Admin review.

### TC-12: Deadline Inversion Validation
- **Category**: Admin Form Validation
- **Expected Outcome**: Form validation throws error if `groupCutoffDate < regDeadline`.

---

## 4. Data Integrity & Concurrency Test Suite

### TC-13: Duplicate Registration Prevention
- **Category**: Data Integrity
- **Expected Outcome**: Rejects duplicate registration attempt with handled validation error.

### TC-14: Single-Assignment Assertion
- **Category**: Data Integrity
- **Expected Outcome**: Asserts that every registered student appears in EXACTLY one group (or remainder queue).

---

## Verification Summary Checklist

| Test ID | Edge Case Description | Automated Check | Status |
| :--- | :--- | :---: | :---: |
| **TC-01** | Zero Registrations ($N=0$) | ✅ | Solved |
| **TC-02** | Underfilled Cohort ($N < k$) | ✅ | Solved |
| **TC-03** | Single Leftover ($R=1$) | ✅ | Solved |
| **TC-04** | Multiple Leftovers ($1 < R < k$) | ✅ | Solved |
| **TC-05** | Single-Person Groups ($k=1$) | ✅ | Solved |
| **TC-06** | Novel Pairing Optimization | ✅ | Solved |
| **TC-07** | Complete Clique / Dense History | ✅ | Solved |
| **TC-08** | Cold-Start Integration | ✅ | Solved |
| **TC-09** | Idempotency / Safe Rerun | ✅ | Solved |
| **TC-10** | Post-Formation Dropout | ✅ | Solved |
| **TC-11** | Post-Formation Registration | ✅ | Solved |
| **TC-12** | Deadline Inversion Validation | ✅ | Solved |
| **TC-13** | Duplicate Registration Prevention | ✅ | Solved |
| **TC-14** | Single-Assignment Assertion | ✅ | Solved |
