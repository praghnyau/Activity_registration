/**
 * State & Persistence Store
 * Manages Students, Activities, Registrations, and Group Assignments with strict business validation.
 */

const { SEED_STUDENTS, SEED_PAST_ACTIVITIES, SEED_ACTIVITIES } = require('../seedData');
const groupEngine = require('./groupFormationEngine');

class ActivitySystemStore {
  constructor() {
    this.resetToSeed();
  }

  resetToSeed() {
    this.students = JSON.parse(JSON.stringify(SEED_STUDENTS));
    this.pastActivities = JSON.parse(JSON.stringify(SEED_PAST_ACTIVITIES));
    this.activities = JSON.parse(JSON.stringify(SEED_ACTIVITIES));
    this.groups = {};
    this.remainders = {};
    this.auditLogs = [];
  }

  getStudents() {
    return this.students;
  }

  getStudentById(id) {
    return this.students.find(s => s.id === id);
  }

  getActivities() {
    return this.activities;
  }

  getActivityById(id) {
    return this.activities.find(a => a.id === id);
  }

  createActivity(activityData) {
    const { title, description, category, activityDate, regDeadline, groupCutoffDate, groupSize, attachments } = activityData;

    const regDate = new Date(regDeadline);
    const cutoffDate = new Date(groupCutoffDate);
    const actDate = new Date(activityDate);

    if (cutoffDate < regDate) {
      throw new Error('Group formation cutoff date cannot be earlier than registration deadline.');
    }
    if (actDate < cutoffDate) {
      throw new Error('Activity date cannot be earlier than group formation cutoff date.');
    }
    if (!groupSize || groupSize < 1) {
      throw new Error('Group size must be at least 1.');
    }

    const newActivity = {
      id: `act_${Date.now()}`,
      title,
      description: description || '',
      category: category || 'General',
      activityDate,
      durationMinutes: activityData.durationMinutes || 120,
      regDeadline,
      groupCutoffDate,
      groupSize: parseInt(groupSize, 10),
      status: 'OPEN',
      attachments: attachments || [],
      registrations: []
    };

    this.activities.push(newActivity);
    this.logAction('CREATE_ACTIVITY', `Created activity '${title}'`);
    return newActivity;
  }

  registerStudent(activityId, studentId) {
    const activity = this.getActivityById(activityId);
    if (!activity) throw new Error('Activity not found.');

    const student = this.getStudentById(studentId);
    if (!student) throw new Error('Student not found.');

    if (activity.registrations.includes(studentId)) {
      throw new Error(`Student ${student.name} is already registered for '${activity.title}'.`);
    }

    const now = new Date();
    const regDeadline = new Date(activity.regDeadline);
    if (now > regDeadline && activity.status !== 'OPEN') {
      throw new Error('Registration deadline has passed for this activity.');
    }

    activity.registrations.push(studentId);

    if (activity.status === 'GROUPS_FORMED' || activity.status === 'REMAINDER_ATTENTION') {
      if (!this.remainders[activityId]) this.remainders[activityId] = [];
      this.remainders[activityId].push(studentId);
      activity.status = 'REMAINDER_ATTENTION';
      this.logAction('LATE_REGISTRATION', `Student ${student.name} registered post-formation for '${activity.title}'. Added to remainder queue.`);
    } else {
      this.logAction('STUDENT_REGISTERED', `Student ${student.name} registered for '${activity.title}'.`);
    }

    return { activity, student };
  }

  unregisterStudent(activityId, studentId) {
    const activity = this.getActivityById(activityId);
    if (!activity) throw new Error('Activity not found.');

    const regIdx = activity.registrations.indexOf(studentId);
    if (regIdx === -1) {
      throw new Error('Student is not registered for this activity.');
    }

    activity.registrations.splice(regIdx, 1);

    if (this.remainders[activityId]) {
      this.remainders[activityId] = this.remainders[activityId].filter(id => id !== studentId);
    }

    if (this.groups[activityId]) {
      this.groups[activityId].forEach(group => {
        const memberIdx = group.members.indexOf(studentId);
        if (memberIdx !== -1) {
          group.members.splice(memberIdx, 1);
          group.isIncomplete = group.members.length < activity.groupSize;
          activity.status = 'REMAINDER_ATTENTION';
          this.logAction('STUDENT_DROPOUT', `Student ${studentId} dropped out of Group '${group.name}' in '${activity.title}'. Group flagged incomplete.`);
        }
      });
    }

    return { activity, studentId };
  }

  triggerGroupFormation(activityId) {
    const activity = this.getActivityById(activityId);
    if (!activity) throw new Error('Activity not found.');

    const registeredStudentIds = activity.registrations || [];

    const result = groupEngine.formGroups(
      registeredStudentIds,
      activity.groupSize,
      this.pastActivities
    );

    activity.status = result.status;
    this.groups[activityId] = result.groups;
    this.remainders[activityId] = result.remainderStudents;

    this.assertSingleAssignment(activityId);

    this.logAction('GROUP_FORMATION_TRIGGERED', `Triggered group formation for '${activity.title}': ${result.message}`);
    return result;
  }

  resolveRemainder(activityId, strategy, params = {}) {
    const activity = this.getActivityById(activityId);
    if (!activity) throw new Error('Activity not found.');

    const currentGroups = this.groups[activityId] || [];
    const currentRemainder = this.remainders[activityId] || [];

    let resolutionResult;
    const matrix = groupEngine.buildCollaborationMatrix(this.pastActivities);

    if (strategy === 'AUTO_DISTRIBUTE') {
      resolutionResult = groupEngine.autoDistributeRemainder(currentGroups, currentRemainder, matrix);
    } else if (strategy === 'CREATE_PARTIAL') {
      resolutionResult = groupEngine.createPartialGroup(currentGroups, currentRemainder);
    } else if (strategy === 'MANUAL_ASSIGN') {
      resolutionResult = groupEngine.manualAssignStudent(currentGroups, currentRemainder, params.studentId, params.targetGroupId);
    } else {
      throw new Error(`Unknown resolution strategy: ${strategy}`);
    }

    this.groups[activityId] = resolutionResult.groups;
    this.remainders[activityId] = resolutionResult.remainderStudents;
    activity.status = resolutionResult.status;

    this.assertSingleAssignment(activityId);
    this.logAction('REMAINDER_RESOLVED', `Resolved remainder for '${activity.title}' via ${strategy}: ${resolutionResult.message}`);
    return resolutionResult;
  }

  assertSingleAssignment(activityId) {
    const groups = this.groups[activityId] || [];
    const assignedSet = new Set();

    groups.forEach(group => {
      group.members.forEach(stuId => {
        if (assignedSet.has(stuId)) {
          throw new Error(`INTEGRITY FAILURE: Student ${stuId} is assigned to multiple groups in activity ${activityId}!`);
        }
        assignedSet.add(stuId);
      });
    });
    return true;
  }

  logAction(type, details) {
    this.auditLogs.unshift({
      timestamp: new Date().toISOString(),
      type,
      details
    });
  }

  getStudentRegistrations(studentId) {
    return this.activities.filter(a => a.registrations.includes(studentId)).map(activity => {
      const activityGroups = this.groups[activity.id] || [];
      const assignedGroup = activityGroups.find(g => g.members.includes(studentId));
      const isRemainder = (this.remainders[activity.id] || []).includes(studentId);

      let statusLabel = 'REGISTERED';
      if (assignedGroup) statusLabel = 'GROUP_ASSIGNED';
      else if (isRemainder) statusLabel = 'REMAINDER_ATTENTION';

      return {
        activity,
        statusLabel,
        assignedGroup: assignedGroup || null,
        teammates: assignedGroup ? assignedGroup.members.filter(id => id !== studentId).map(id => this.getStudentById(id)) : []
      };
    });
  }
}

const store = new ActivitySystemStore();
module.exports = store;
