/**
 * Edge Case Verification Test Suite (TC-01 to TC-14)
 * Verifies system safeguards across division math, algorithm optimization, deadlines, and integrity rules.
 */

const assert = require('assert');
const store = require('../src/services/store');
const groupEngine = require('../src/services/groupFormationEngine');

function runEdgeCaseTests() {
  console.log('\n--- Running Complete Edge Case Verification Suite (TC-01 to TC-14) ---');
  let passed = 0;
  let failed = 0;

  function testCase(id, title, fn) {
    try {
      store.resetToSeed();
      fn();
      console.log(`  ✅ PASS [${id}]: ${title}`);
      passed++;
    } catch (err) {
      console.error(`  ❌ FAIL [${id}]: ${title}`);
      console.error(`     Error: ${err.message}`);
      failed++;
    }
  }

  testCase('TC-01', 'Zero Registrations at Cutoff Date (N=0)', () => {
    const act = store.createActivity({
      title: 'Empty Seminar',
      activityDate: '2026-12-01T10:00',
      regDeadline: '2026-11-25T23:59',
      groupCutoffDate: '2026-11-26T12:00',
      groupSize: 4
    });

    const result = store.triggerGroupFormation(act.id);
    assert.strictEqual(result.status, 'CANCELLED_NO_REGISTRATIONS');
    assert.strictEqual(result.groups.length, 0);
    assert.strictEqual(result.remainderStudents.length, 0);
  });

  testCase('TC-02', 'Underfilled Cohort (N < k)', () => {
    const act = store.createActivity({
      title: 'Small Lab',
      activityDate: '2026-12-01T10:00',
      regDeadline: '2026-11-25T23:59',
      groupCutoffDate: '2026-11-26T12:00',
      groupSize: 5
    });

    store.registerStudent(act.id, 'stu_01');
    store.registerStudent(act.id, 'stu_02');

    const result = store.triggerGroupFormation(act.id);
    assert.strictEqual(result.status, 'UNDERFILLED_COHORT');
    assert.strictEqual(result.groups.length, 0);
    assert.strictEqual(result.remainderStudents.length, 2);
  });

  testCase('TC-03', 'Single Leftover Student (N mod k = 1) & Auto-Distribute Resolution', () => {
    const result = store.triggerGroupFormation('act_101');

    assert.strictEqual(result.status, 'REMAINDER_ATTENTION');
    assert.strictEqual(result.groups.length, 3);
    assert.strictEqual(result.remainderStudents.length, 1);

    const resolved = store.resolveRemainder('act_101', 'AUTO_DISTRIBUTE');
    assert.strictEqual(resolved.status, 'GROUPS_FORMED');
    assert.strictEqual(resolved.remainderStudents.length, 0);
    const sizes = resolved.groups.map(g => g.members.length);
    assert.deepStrictEqual(sizes.sort(), [3, 3, 4]);
  });

  testCase('TC-04', 'Multiple Leftover Students (N mod k = 3) & Create Partial Group Resolution', () => {
    const result = store.triggerGroupFormation('act_102');

    assert.strictEqual(result.status, 'REMAINDER_ATTENTION');
    assert.strictEqual(result.groups.length, 2);
    assert.strictEqual(result.remainderStudents.length, 3);

    const resolved = store.resolveRemainder('act_102', 'CREATE_PARTIAL');
    assert.strictEqual(resolved.status, 'GROUPS_FORMED');
    assert.strictEqual(resolved.groups.length, 3);
    assert.strictEqual(resolved.groups[2].members.length, 3);
    assert.strictEqual(resolved.groups[2].isPartial, true);
  });

  testCase('TC-05', 'Single-Person Group Configuration (k = 1)', () => {
    const act = store.createActivity({
      title: 'Solo Presentation',
      activityDate: '2026-12-01T10:00',
      regDeadline: '2026-11-25T23:59',
      groupCutoffDate: '2026-11-26T12:00',
      groupSize: 1
    });

    store.registerStudent(act.id, 'stu_01');
    store.registerStudent(act.id, 'stu_02');
    store.registerStudent(act.id, 'stu_03');

    const result = store.triggerGroupFormation(act.id);
    assert.strictEqual(result.status, 'GROUPS_FORMED');
    assert.strictEqual(result.groups.length, 3);
    assert.strictEqual(result.groups[0].members.length, 1);
  });

  testCase('TC-06', 'Minimal Repeat Pairing Optimization', () => {
    const act = store.createActivity({
      title: 'Pair Coding Sprint',
      activityDate: '2026-12-01T10:00',
      regDeadline: '2026-11-25T23:59',
      groupCutoffDate: '2026-11-26T12:00',
      groupSize: 2
    });

    store.registerStudent(act.id, 'stu_01');
    store.registerStudent(act.id, 'stu_02');
    store.registerStudent(act.id, 'stu_03');
    store.registerStudent(act.id, 'stu_04');

    const result = store.triggerGroupFormation(act.id);
    assert.strictEqual(result.status, 'GROUPS_FORMED');

    const groupOf01 = result.groups.find(g => g.members.includes('stu_01'));
    assert.strictEqual(groupOf01.members.includes('stu_02'), false);
  });

  testCase('TC-07', 'Complete Clique / Dense History Fallback', () => {
    const students = ['stu_01', 'stu_02', 'stu_03', 'stu_04', 'stu_05', 'stu_06'];
    const pastActs = [
      { id: 'p1', groups: [{ members: students }] }
    ];

    const result = groupEngine.formGroups(students, 3, pastActs);
    assert.strictEqual(result.status, 'GROUPS_FORMED');
    assert.strictEqual(result.groups.length, 2);
  });

  testCase('TC-08', 'Cold-Start / New Student Integration', () => {
    const act = store.createActivity({
      title: 'Workshop',
      activityDate: '2026-12-01T10:00',
      regDeadline: '2026-11-25T23:59',
      groupCutoffDate: '2026-11-26T12:00',
      groupSize: 2
    });

    ['stu_01', 'stu_02', 'stu_13', 'stu_14'].forEach(s => store.registerStudent(act.id, s));

    const result = store.triggerGroupFormation(act.id);
    assert.strictEqual(result.status, 'GROUPS_FORMED');
    assert.strictEqual(result.groups.length, 2);
  });

  testCase('TC-09', 'Idempotency & Repeatability on Rerun', () => {
    const res1 = store.triggerGroupFormation('act_103');
    const groupsPass1 = JSON.stringify(res1.groups);

    const res2 = store.triggerGroupFormation('act_103');
    const groupsPass2 = JSON.stringify(res2.groups);

    assert.strictEqual(groupsPass1, groupsPass2);
  });

  testCase('TC-10', 'Student Dropout Post-Formation', () => {
    store.triggerGroupFormation('act_103');

    store.unregisterStudent('act_103', 'stu_06');
    const act = store.getActivityById('act_103');

    assert.strictEqual(act.status, 'REMAINDER_ATTENTION');
    assert.strictEqual(store.groups['act_103'][0].isIncomplete, true);
    assert.strictEqual(store.groups['act_103'][0].members.length, 1);
  });

  testCase('TC-11', 'Late Registration Post-Formation', () => {
    store.triggerGroupFormation('act_103');

    store.registerStudent('act_103', 'stu_01');
    const act = store.getActivityById('act_103');

    assert.strictEqual(act.status, 'REMAINDER_ATTENTION');
    assert.deepStrictEqual(store.remainders['act_103'], ['stu_01']);
  });

  testCase('TC-12', 'Deadline Inversion Form Validation', () => {
    assert.throws(() => {
      store.createActivity({
        title: 'Invalid Dates Activity',
        activityDate: '2026-10-10T10:00',
        regDeadline: '2026-10-15T23:59',
        groupCutoffDate: '2026-10-12T12:00',
        groupSize: 3
      });
    }, /Group formation cutoff date cannot be earlier than registration deadline/);
  });

  testCase('TC-13', 'Duplicate Registration Prevention', () => {
    const actId = 'act_101';
    assert.throws(() => {
      store.registerStudent(actId, 'stu_01');
    }, /is already registered/);
  });

  testCase('TC-14', 'Single-Assignment Integrity Assertion', () => {
    store.triggerGroupFormation('act_101');
    const isSingleAssignmentValid = store.assertSingleAssignment('act_101');
    assert.strictEqual(isSingleAssignmentValid, true);
  });

  return { passed, failed };
}

module.exports = { runEdgeCaseTests };
