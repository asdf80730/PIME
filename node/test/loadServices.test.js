'use strict';

// Unit tests for the ime.json discovery helpers. They build a throwaway
// `input_methods` tree so the test never touches the bundled services and
// needs no Windows API.
//
// Generated with assistance from DeepSeek V4.1 Flash.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {loadServices, loadServiceById} = require('../loadServices');

const GUID = '{A1B2C3D4-E5F6-4789-9ABC-DEF012345678}';

function makeFixture() {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pime-load-services-'));
  const imeDir = path.join(baseDir, 'input_methods', 'demo');
  fs.mkdirSync(imeDir, {recursive: true});

  fs.writeFileSync(path.join(imeDir, 'ime.json'), JSON.stringify({
    name: 'Demo IME',
    guid: GUID,
    moduleName: 'demo_ime'
  }));
  fs.writeFileSync(path.join(imeDir, 'demo_ime.js'),
    'module.exports = {marker: "demo-service"};');

  // A plain file in input_methods must be ignored during discovery.
  fs.writeFileSync(path.join(baseDir, 'input_methods', 'README.txt'), 'not a service');

  return baseDir;
}

function main() {
  const baseDir = makeFixture();
  try {
    const services = loadServices(baseDir);
    assert.strictEqual(services.length, 1, 'only directories with ime.json are services');
    assert.strictEqual(services[0].name, 'Demo IME');
    assert.strictEqual(services[0].guid, GUID);
    assert.strictEqual(services[0].textService.marker, 'demo-service');

    const byId = loadServiceById(GUID.toLowerCase(), baseDir);
    assert.strictEqual(byId.marker, 'demo-service', 'GUID lookup is case-insensitive');
    assert.strictEqual(loadServiceById('{00000000-0000-0000-0000-000000000000}', baseDir), null);
  } finally {
    if (fs.rmSync) {
      fs.rmSync(baseDir, {recursive: true, force: true});
    } else {
      fs.rmdirSync(baseDir, {recursive: true});
    }
  }
}

main();
console.log('node backend: ime.json discovery keeps directory filtering and GUID lookup');
