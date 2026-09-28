/**
 * Headless API Server & Test Service
 * Activity Registration & Group Formation System
 * Pure JSON REST API - No HTML / Frontend serving.
 */

const http = require('http');
const store = require('./src/services/store');
const { runEngineUnitTests } = require('./tests/groupFormationEngine.test');
const { runEdgeCaseTests } = require('./tests/edgeCases.test');

const PORT = process.env.PORT || 3000;

function parseRequestBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        resolve({});
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;
  const method = req.method;

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Content-Type', 'application/json');

  if (method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const jsonResponse = (statusCode, data) => {
    res.writeHead(statusCode);
    res.end(JSON.stringify(data, null, 2));
  };

  try {
    if (pathname === '/api/students' && method === 'GET') {
      return jsonResponse(200, { students: store.getStudents() });
    }

    if (pathname === '/api/activities' && method === 'GET') {
      const activities = store.getActivities().map(act => {
        const activityGroups = store.groups[act.id] || [];
        const activityRemainder = store.remainders[act.id] || [];
        return {
          ...act,
          groups: activityGroups,
          remainderStudents: activityRemainder,
          registeredStudents: act.registrations.map(id => store.getStudentById(id))
        };
      });
      return jsonResponse(200, { activities, pastActivities: store.pastActivities });
    }

    if (pathname.startsWith('/api/students/') && pathname.endsWith('/registrations') && method === 'GET') {
      const parts = pathname.split('/');
      const studentId = parts[3];
      const registrations = store.getStudentRegistrations(studentId);
      return jsonResponse(200, { studentId, registrations });
    }

    if (pathname === '/api/activities' && method === 'POST') {
      const body = await parseRequestBody(req);
      try {
        const newAct = store.createActivity(body);
        return jsonResponse(201, { success: true, activity: newAct });
      } catch (err) {
        return jsonResponse(400, { success: false, error: err.message });
      }
    }

    if (pathname.match(/^\/api\/activities\/[^/]+\/register$/) && method === 'POST') {
      const activityId = pathname.split('/')[3];
      const body = await parseRequestBody(req);
      try {
        const result = store.registerStudent(activityId, body.studentId);
        return jsonResponse(200, { success: true, ...result });
      } catch (err) {
        return jsonResponse(400, { success: false, error: err.message });
      }
    }

    if (pathname.match(/^\/api\/activities\/[^/]+\/unregister$/) && method === 'POST') {
      const activityId = pathname.split('/')[3];
      const body = await parseRequestBody(req);
      try {
        const result = store.unregisterStudent(activityId, body.studentId);
        return jsonResponse(200, { success: true, ...result });
      } catch (err) {
        return jsonResponse(400, { success: false, error: err.message });
      }
    }

    if (pathname.match(/^\/api\/activities\/[^/]+\/form-groups$/) && method === 'POST') {
      const activityId = pathname.split('/')[3];
      try {
        const result = store.triggerGroupFormation(activityId);
        return jsonResponse(200, { success: true, result });
      } catch (err) {
        return jsonResponse(400, { success: false, error: err.message });
      }
    }

    if (pathname.match(/^\/api\/activities\/[^/]+\/resolve-remainder$/) && method === 'POST') {
      const activityId = pathname.split('/')[3];
      const body = await parseRequestBody(req);
      try {
        const result = store.resolveRemainder(activityId, body.strategy, body.params || {});
        return jsonResponse(200, { success: true, result });
      } catch (err) {
        return jsonResponse(400, { success: false, error: err.message });
      }
    }

    if (pathname === '/api/run-tests' && method === 'GET') {
      store.resetToSeed();
      const engineRes = runEngineUnitTests();
      const edgeCaseRes = runEdgeCaseTests();

      return jsonResponse(200, {
        totalExecuted: engineRes.passed + engineRes.failed + edgeCaseRes.passed + edgeCaseRes.failed,
        passed: engineRes.passed + edgeCaseRes.passed,
        failed: engineRes.failed + edgeCaseRes.failed,
        status: (engineRes.failed + edgeCaseRes.failed === 0) ? 'PASSED' : 'FAILED'
      });
    }

    if (pathname === '/api/reset' && method === 'POST') {
      store.resetToSeed();
      return jsonResponse(200, { success: true, message: 'Reset data store to initial seed state.' });
    }

    jsonResponse(404, { error: 'Not Found', message: 'This server is a pure API endpoint service. No HTML pages are served.' });

  } catch (error) {
    console.error('Server error:', error);
    jsonResponse(500, { error: 'Internal Server Error', message: error.message });
  }
});

server.listen(PORT, () => {
  console.log(`Headless API Service running at http://localhost:${PORT}`);
});
