/**
 * Master Test Suite Runner
 * Executes unit tests and full edge case verification matrix (TC-01 to TC-14).
 */

const { runEngineUnitTests } = require('./groupFormationEngine.test');
const { runEdgeCaseTests } = require('./edgeCases.test');

function runAllTests() {
  console.log('================================================================');
  console.log('  ACTIVITY REGISTRATION & GROUP FORMATION SYSTEM TEST RUNNER');
  console.log('================================================================');

  const startTime = Date.now();

  const engineResults = runEngineUnitTests();
  const edgeCaseResults = runEdgeCaseTests();

  const totalPassed = engineResults.passed + edgeCaseResults.passed;
  const totalFailed = engineResults.failed + edgeCaseResults.failed;
  const duration = Date.now() - startTime;

  console.log('\n================================================================');
  console.log('                      TEST SUMMARY REPORT                       ');
  console.log('================================================================');
  console.log(`  Total Test Cases Executed: ${totalPassed + totalFailed}`);
  console.log(`  Passed:                    ${totalPassed} ✅`);
  console.log(`  Failed:                    ${totalFailed} ❌`);
  console.log(`  Execution Time:            ${duration} ms`);
  console.log('----------------------------------------------------------------');

  if (totalFailed === 0) {
    console.log('  🎉 ALL TEST CASES PASSED SUCCESSFULLY! ALL EDGE CASES SOLVED.');
    console.log('================================================================\n');
    process.exit(0);
  } else {
    console.log('  ❌ SOME TEST CASES FAILED. PLEASE REVIEW LOGS ABOVE.');
    console.log('================================================================\n');
    process.exit(1);
  }
}

runAllTests();
