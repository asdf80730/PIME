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
// The second TSF language profile of the same service (#481).
const EXTRA_GUID = '{53C15256-7A5F-4B54-86E8-0636E0745C3E}';

function makeFixture() {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pime-load-services-'));
  const imeDir = path.join(baseDir, 'input_methods', 'demo');
  fs.mkdirSync(imeDir, {recursive: true});

  fs.writeFileSync(path.join(imeDir, 'ime.json'), JSON.stringify({
    name: 'Demo IME',
    guid: GUID,
    moduleName: 'demo_ime',
    additionalProfiles: [
      {guid: EXTRA_GUID, locale: 'zh-CN', fallbackLocale: 'zh-CN'},
      {locale: 'no-guid'},
      null
    ]
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

    // The second TSF language profile of the same CLSID activates with its own
    // GUID (#481 round 2): the loader has to answer for it, or a client that
    // picks the Simplified-Chinese bucket gets no service at all.
    const byExtra = loadServiceById(EXTRA_GUID.toLowerCase(), baseDir);
    assert.strictEqual(byExtra, byId,
      'the additional profile GUID maps to the same module as the primary');
    // Both sides are lowercased, so the manifest's upper-case form and the
    // client's lower-case form meet in the middle.
    assert.strictEqual(loadServiceById(EXTRA_GUID, baseDir), byId,
      'additional profile lookup is case-insensitive on both sides');
    // An entry without a usable guid contributes no key: the locale-only and
    // null entries must not answer as ids.
    assert.strictEqual(loadServiceById('no-guid', baseDir), null,
      'a profile entry without a guid registers no key');
  } finally {
    if (fs.rmSync) {
      fs.rmSync(baseDir, {recursive: true, force: true});
    } else {
      fs.rmdirSync(baseDir, {recursive: true});
    }
  }

  // The shipped tree next to this file is what DllRegisterServer scans, so the
  // same two helpers have to answer for the product's own registration data:
  // every IME that ships under node/input_methods resolves by its own primary
  // GUID, and an id no shipped manifest names is still null. The shipped
  // modules are the real IME code and load with no Windows-only state, so the
  // module's own exported key pair is the marker asserted here.
  const shippedDir = path.join(__dirname, '..');
  const shippedServices = loadServices(shippedDir);
  // The two manifests committed next to this file. The three McBopomofo-family
  // names are copied into node/input_methods by build.bat from the
  // McBopomofoWeb, McFoximWeb and McTabimWeb submodules, so their presence
  // depends on whether the build has run yet — CI runs `npm test`
  // (build-and-sign.yaml) before `build.bat`, this box may have either order.
  const COMMITTED = ['emojime', '喵喵輸入法'];
  const BUILT_BY_BUILD_BAT =
    ['小麥注音 (PIME)', '小麥他命 (PIME)', '小麥族語 (PIME)'];
  const names = shippedServices.map((service) => service.name).sort();
  assert.deepStrictEqual(names.filter((name) => COMMITTED.includes(name)),
    [...COMMITTED].sort(),
    'the shipped tree registers exactly the two IMEs whose manifests are ' +
    'committed');
  for (const name of names) {
    assert.ok(COMMITTED.includes(name) || BUILT_BY_BUILD_BAT.includes(name),
      `unexpected service under node/input_methods: ${name}`);
  }
  // Pinned literally as well: the GUIDs DllRegisterServer hands to
  // AddLanguageProfile, so a silent rename in a shipped manifest is a finding.
  const MEOW_GUID = '{C5F37DA0-274E-4837-9B7C-9BB79FE85D9D}';
  const EMOJIME_GUID = '{A381D463-9338-4FBD-B83D-66FFB03523B3}';
  assert.deepStrictEqual(
    shippedServices.filter((service) => COMMITTED.includes(service.name))
      .map((service) => service.guid).sort(),
    [EMOJIME_GUID, MEOW_GUID],
    'each shipped IME is keyed by its own shipped guid');
  const shippedMeow = loadServiceById(MEOW_GUID.toLowerCase(), shippedDir);
  assert.ok(shippedMeow, 'the shipped meow primary GUID resolves to a module');
  assert.deepStrictEqual(Object.keys(shippedMeow), ['textReducer', 'response'],
    'the meow lookup returned the real IME module');
  const shippedEmojime = loadServiceById(EMOJIME_GUID.toLowerCase(), shippedDir);
  assert.ok(shippedEmojime, 'the shipped emojime primary GUID resolves to a module');
  assert.deepStrictEqual(Object.keys(shippedEmojime), ['textReducer', 'response'],
    'the emojime lookup returned the real IME module');
  assert.strictEqual(
    loadServiceById('{00000000-0000-0000-0000-000000000001}', shippedDir), null,
    'an id absent from every shipped manifest is null');
}

main();
console.log('node backend: ime.json discovery keeps directory filtering and GUID lookup');
// loadServices() requires every discovered module, and the McBopomofo-family
// bundles that build.bat copies in keep a handle open, so the process would sit
// on an empty event loop. The assertions are through: exit deterministically for
// both tree orders (before and after build.bat).
process.exit(0);
