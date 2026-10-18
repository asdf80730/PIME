'use strict';

// Regression test for EasyIME/PIME#937: a request that arrives while no
// service is resolved must fail the request, not kill the backend process.
//
// Speaks the launcher -> backend protocol directly ("<client_id>|<json>"),
// so it needs no Windows and runs on the bundled Node runtime as well as CI.
//
// Generated with assistance from OMP (deepseek-v4.1-flash).

const assert = require('assert');
const path = require('path');
const { spawn } = require('child_process');

const NODE_DIR = path.join(__dirname, '..');
const CLIENT_ID = 'test-client-1';
const UNKNOWN_GUID = '00000000-0000-0000-0000-000000000000';
const TIMEOUT_MS = 5000;

function startServer() {
  const child = spawn(process.execPath, ['server.js'], {
    cwd: NODE_DIR,
    stdio: ['pipe', 'pipe', 'pipe']
  });

  const state = {replies: [], pending: '', stderr: ''};

  child.stdout.setEncoding('utf8');
  child.stderr.setEncoding('utf8');

  child.stdout.on('data', (chunk) => {
    state.pending += chunk;
    let newline;
    while ((newline = state.pending.indexOf('\n')) !== -1) {
      const line = state.pending.slice(0, newline).trim();
      state.pending = state.pending.slice(newline + 1);
      // Other stdout lines (debug output, "Finished") are not replies.
      if (line.indexOf('PIME_MSG|') === 0) {
        state.replies.push(line);
      }
    }
  });

  child.stderr.on('data', (chunk) => {
    state.stderr += chunk;
  });

  return {child, state};
}

function send(child, payload) {
  child.stdin.write(CLIENT_ID + '|' + JSON.stringify(payload) + '\n');
}

function waitFor(check, description) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();
    const timer = setInterval(() => {
      if (check()) {
        clearInterval(timer);
        resolve();
      } else if (Date.now() - startedAt > TIMEOUT_MS) {
        clearInterval(timer);
        reject(new Error('timed out waiting for ' + description));
      }
    }, 20);
  });
}

function payloadOf(reply) {
  return JSON.parse(reply.split('|', 3)[2]);
}

async function main() {
  const {child, state} = startServer();

  try {
    // First frame: init naming a GUID that no service is registered under.
    send(child, {
      method: 'init',
      id: UNKNOWN_GUID,
      seqNum: 0,
      isWindows8Above: true,
      isMetroApp: false,
      isUiLess: false,
      isConsole: false
    });
    // Any follow-up request used to dereference the null service and throw.
    send(child, {method: 'filterKeyDown', seqNum: 1, charCode: 0x41, keyCode: 0x41});

    await waitFor(() => state.replies.length >= 2, 'two replies');

    assert.strictEqual(state.replies.length, 2);
    const initReply = payloadOf(state.replies[0]);
    const keyReply = payloadOf(state.replies[1]);

    assert.strictEqual(initReply.success, false);
    assert.strictEqual(initReply.seqNum, 0);
    assert.strictEqual(keyReply.success, false);
    assert.strictEqual(keyReply.seqNum, 1);
    assert.strictEqual(child.exitCode, null, 'server must stay alive');
  } catch (err) {
    assert.fail((err.stack || err.message) +
      (state.stderr ? '\nserver stderr:\n' + state.stderr : ''));
  } finally {
    child.stdin.end();
    child.kill();
  }
}

main().then(
  () => console.log('node backend: pre-init and unknown-service requests survive'),
  (err) => {
    console.error(err.message);
    process.exit(1);
  }
);
