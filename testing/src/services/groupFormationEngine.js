/**
 * Group Formation Engine
 * Solves novel-pairing optimization, remainder detection (N mod k != 0), and idempotent group generation.
 */

function buildCollaborationMatrix(pastActivities = []) {
  const matrix = {};

  pastActivities.forEach(activity => {
    (activity.groups || []).forEach(group => {
      const members = group.members || [];
      for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
          const u = members[i];
          const v = members[j];

          if (!matrix[u]) matrix[u] = {};
          if (!matrix[v]) matrix[v] = {};

          matrix[u][v] = (matrix[u][v] || 0) + 1;
          matrix[v][u] = (matrix[v][u] || 0) + 1;
        }
      }
    });
  });

  return matrix;
}

function calculateGroupCollisionPenalty(groupMembers = [], matrix = {}) {
  let penalty = 0;
  for (let i = 0; i < groupMembers.length; i++) {
    for (let j = i + 1; j < groupMembers.length; j++) {
      const u = groupMembers[i];
      const v = groupMembers[j];
      const count = (matrix[u] && matrix[u][v]) ? matrix[u][v] : 0;
      penalty += count;
    }
  }
  return penalty;
}

function calculateTotalPartitionPenalty(groups = [], matrix = {}) {
  return groups.reduce((total, group) => {
    return total + calculateGroupCollisionPenalty(group.members, matrix);
  }, 0);
}

function formGroups(registeredStudentIds = [], groupSize = 1, pastActivities = []) {
  if (!registeredStudentIds || registeredStudentIds.length === 0) {
    return {
      status: 'CANCELLED_NO_REGISTRATIONS',
      groups: [],
      remainderStudents: [],
      metrics: { totalRegistered: 0, requiredGroupSize: groupSize, totalGroups: 0, penaltyScore: 0 },
      message: 'No students registered for this activity at cutoff date.'
    };
  }

  const N = registeredStudentIds.length;
  const k = Math.max(1, groupSize);

  if (N < k) {
    return {
      status: 'UNDERFILLED_COHORT',
      groups: [],
      remainderStudents: [...registeredStudentIds],
      metrics: { totalRegistered: N, requiredGroupSize: k, totalGroups: 0, penaltyScore: 0 },
      message: `Registered cohort size (${N}) is smaller than required group size (${k}). Admin decision required.`
    };
  }

  if (k === 1) {
    const singleGroups = registeredStudentIds.map((stuId, index) => ({
      id: `group_${index + 1}`,
      groupNumber: index + 1,
      name: `Group ${index + 1}`,
      members: [stuId]
    }));
    return {
      status: 'GROUPS_FORMED',
      groups: singleGroups,
      remainderStudents: [],
      metrics: { totalRegistered: N, requiredGroupSize: 1, totalGroups: N, penaltyScore: 0 },
      message: `Formed ${N} individual groups.`
    };
  }

  const matrix = buildCollaborationMatrix(pastActivities);
  const sortedStudents = [...registeredStudentIds].sort();

  const numFullGroups = Math.floor(N / k);
  const remainderCount = N % k;

  const fullGroupPool = sortedStudents.slice(0, numFullGroups * k);
  const remainderStudents = sortedStudents.slice(numFullGroups * k);

  const groups = Array.from({ length: numFullGroups }, (_, i) => ({
    id: `group_${i + 1}`,
    groupNumber: i + 1,
    name: `Group ${i + 1}`,
    members: []
  }));

  fullGroupPool.forEach((stuId, index) => {
    const groupIdx = index % numFullGroups;
    groups[groupIdx].members.push(stuId);
  });

  let improved = true;
  let maxPasses = 50;
  while (improved && maxPasses > 0) {
    improved = false;
    maxPasses--;

    for (let g1 = 0; g1 < groups.length; g1++) {
      for (let g2 = g1 + 1; g2 < groups.length; g2++) {
        const groupA = groups[g1];
        const groupB = groups[g2];

        for (let i = 0; i < groupA.members.length; i++) {
          for (let j = 0; j < groupB.members.length; j++) {
            const memberA = groupA.members[i];
            const memberB = groupB.members[j];

            const currentCost = calculateGroupCollisionPenalty(groupA.members, matrix) +
                                calculateGroupCollisionPenalty(groupB.members, matrix);

            groupA.members[i] = memberB;
            groupB.members[j] = memberA;

            const newCost = calculateGroupCollisionPenalty(groupA.members, matrix) +
                            calculateGroupCollisionPenalty(groupB.members, matrix);

            if (newCost < currentCost) {
              improved = true;
            } else {
              groupA.members[i] = memberA;
              groupB.members[j] = memberB;
            }
          }
        }
      }
    }
  }

  const finalPenalty = calculateTotalPartitionPenalty(groups, matrix);
  const status = (remainderCount === 0) ? 'GROUPS_FORMED' : 'REMAINDER_ATTENTION';

  return {
    status,
    groups,
    remainderStudents,
    metrics: {
      totalRegistered: N,
      requiredGroupSize: k,
      totalGroups: numFullGroups,
      remainderCount,
      penaltyScore: finalPenalty
    },
    message: remainderCount > 0
      ? `Formed ${numFullGroups} groups of ${k}. ${remainderCount} student(s) remain unassigned.`
      : `Successfully formed ${numFullGroups} balanced groups with optimal member pairing.`
  };
}

function autoDistributeRemainder(groups = [], remainderStudents = [], matrix = {}) {
  const updatedGroups = groups.map(g => ({ ...g, members: [...g.members] }));

  remainderStudents.forEach(stuId => {
    let bestGroupIdx = 0;
    let minPenaltyIncrease = Infinity;

    updatedGroups.forEach((group, idx) => {
      const currentPenalty = calculateGroupCollisionPenalty(group.members, matrix);
      const tempGroup = [...group.members, stuId];
      const newPenalty = calculateGroupCollisionPenalty(tempGroup, matrix);
      const increase = newPenalty - currentPenalty;

      if (increase < minPenaltyIncrease) {
        minPenaltyIncrease = increase;
        bestGroupIdx = idx;
      }
    });

    updatedGroups[bestGroupIdx].members.push(stuId);
  });

  return {
    groups: updatedGroups,
    remainderStudents: [],
    status: 'GROUPS_FORMED',
    message: `Distributed ${remainderStudents.length} remainder student(s) into existing groups.`
  };
}

function createPartialGroup(groups = [], remainderStudents = []) {
  if (!remainderStudents || remainderStudents.length === 0) {
    return { groups, remainderStudents: [], status: 'GROUPS_FORMED' };
  }

  const newGroupId = `group_${groups.length + 1}`;
  const partialGroup = {
    id: newGroupId,
    groupNumber: groups.length + 1,
    name: `Group ${groups.length + 1} (Partial)`,
    members: [...remainderStudents],
    isPartial: true
  };

  return {
    groups: [...groups, partialGroup],
    remainderStudents: [],
    status: 'GROUPS_FORMED',
    message: `Created 1 partial group of ${remainderStudents.length} member(s).`
  };
}

function manualAssignStudent(groups = [], remainderStudents = [], studentId, targetGroupId) {
  const updatedRemainder = remainderStudents.filter(id => id !== studentId);
  const updatedGroups = groups.map(g => {
    if (g.id === targetGroupId && !g.members.includes(studentId)) {
      return { ...g, members: [...g.members, studentId] };
    }
    return g;
  });

  const allAssigned = updatedRemainder.length === 0;

  return {
    groups: updatedGroups,
    remainderStudents: updatedRemainder,
    status: allAssigned ? 'GROUPS_FORMED' : 'REMAINDER_ATTENTION',
    message: `Manually assigned student ${studentId} to ${targetGroupId}.`
  };
}

module.exports = {
  buildCollaborationMatrix,
  calculateGroupCollisionPenalty,
  calculateTotalPartitionPenalty,
  formGroups,
  autoDistributeRemainder,
  createPartialGroup,
  manualAssignStudent
};
