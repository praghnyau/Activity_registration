/**
 * Unit Tests for Group Formation Engine Algorithm
 */

const assert = require('assert');
const groupEngine = require('../src/services/groupFormationEngine');

function runEngineUnitTests() {
  console.log('\n--- Running Group Formation Engine Unit Tests ---');
  let passed = 0;
  let failed = 0;

  function test(name, fn) {
    try {
      fn();
      console.log(`  ✅ PASS: ${name}`);
      passed++;
    } catch (err) {
      console.error(`  ❌ FAIL: ${name}`);
      console.error(`     ${err.message}`);
      failed++;
    }
  }

  test('buildCollaborationMatrix correctly calculates pairwise co-occurrences', () => {
    const pastActs = [
      {
        id: 'act1',
        groups: [
          { id: 'g1', members: ['stu_01', 'stu_02', 'stu_03'] }
        ]
      }
    ];

    const matrix = groupEngine.buildCollaborationMatrix(pastActs);
    assert.strictEqual(matrix['stu_01']['stu_02'], 1);
    assert.strictEqual(matrix['stu_02']['stu_01'], 1);
    assert.strictEqual(matrix['stu_01']['stu_03'], 1);
    assert.strictEqual(matrix['stu_02']['stu_03'], 1);
    assert.strictEqual(matrix['stu_01']['stu_04'], undefined);
  });

  test('calculateGroupCollisionPenalty correctly sums past collisions', () => {
    const matrix = {
      'stu_01': { 'stu_02': 2, 'stu_03': 1 },
      'stu_02': { 'stu_01': 2, 'stu_03': 0 },
      'stu_03': { 'stu_01': 1, 'stu_02': 0 }
    };

    const penalty = groupEngine.calculateGroupCollisionPenalty(['stu_01', 'stu_02', 'stu_03'], matrix);
    assert.strictEqual(penalty, 3);
  });

  test('formGroups handles perfect division (N mod k == 0)', () => {
    const students = ['s1', 's2', 's3', 's4', 's5', 's6'];
    const result = groupEngine.formGroups(students, 3, []);

    assert.strictEqual(result.status, 'GROUPS_FORMED');
    assert.strictEqual(result.groups.length, 2);
    assert.strictEqual(result.remainderStudents.length, 0);
    assert.strictEqual(result.metrics.totalGroups, 2);
  });

  test('formGroups correctly identifies remainder (N mod k != 0)', () => {
    const students = ['s1', 's2', 's3', 's4', 's5', 's6', 's7'];
    const result = groupEngine.formGroups(students, 3, []);

    assert.strictEqual(result.status, 'REMAINDER_ATTENTION');
    assert.strictEqual(result.groups.length, 2);
    assert.strictEqual(result.remainderStudents.length, 1);
    assert.strictEqual(result.remainderStudents[0], 's7');
  });

  return { passed, failed };
}

module.exports = { runEngineUnitTests };
