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
// The Simplified twin of the same engine: its own folder, its own profile
// GUID (#481).
const CN_GUID = '{53C15256-7A5F-4B54-86E8-0636E0745C3E}';

function makeFixture() {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pime-load-services-'));
  const imeDir = path.join(baseDir, 'input_methods', 'demo');
  const imeCnDir = path.join(baseDir, 'input_methods', 'demo-cn');
  const noGuidDir = path.join(baseDir, 'input_methods', 'demo-no-guid');
  fs.mkdirSync(imeDir, {recursive: true});
  fs.mkdirSync(imeCnDir, {recursive: true});
  fs.mkdirSync(noGuidDir, {recursive: true});

  fs.writeFileSync(path.join(imeDir, 'ime.json'), JSON.stringify({
    name: 'Demo IME',
    guid: GUID,
    locale: 'zh-Hant-TW',
    fallbackLocale: 'zh-TW',
    moduleName: 'demo_ime'
  }));
  fs.writeFileSync(path.join(imeDir, 'demo_ime.js'),
    'module.exports = {marker: "demo-service"};');

  // One folder per Windows input language: the same engine, a second bucket.
  fs.writeFileSync(path.join(imeCnDir, 'ime.json'), JSON.stringify({
    name: 'Demo IME CN',
    guid: CN_GUID,
    locale: 'zh-CN',
    fallbackLocale: 'zh-CN',
    moduleName: 'demo_cn_ime'
  }));
  fs.writeFileSync(path.join(imeCnDir, 'demo_cn_ime.js'),
    'module.exports = {marker: "demo-cn-service"};');

  // A manifest without a guid registers no key: it cannot be activated.
  fs.writeFileSync(path.join(noGuidDir, 'ime.json'), JSON.stringify({
    name: 'Demo without a guid',
    locale: 'zh-Hant-TW',
    fallbackLocale: 'zh-TW',
    moduleName: 'demo_no_guid'
  }));
  fs.writeFileSync(path.join(noGuidDir, 'demo_no_guid.js'),
    'module.exports = {marker: "unreachable"};');

  // A plain file in input_methods must be ignored during discovery.
  fs.writeFileSync(path.join(baseDir, 'input_methods', 'README.txt'), 'not a service');

  return baseDir;
}

function main() {
  const baseDir = makeFixture();
  try {
    const services = loadServices(baseDir);
    assert.strictEqual(services.length, 3, 'only directories with ime.json are services');
    // Keyed by the manifest name so the readdir order does not matter: each
    // folder is keyed by its own guid, and a guid-less manifest has none.
    const byName = {};
    for (const service of services) {
      byName[service.name] = service;
    }
    assert.strictEqual(byName['Demo IME'].guid, GUID);
    assert.strictEqual(byName['Demo IME'].textService.marker, 'demo-service');
    assert.strictEqual(byName['Demo IME CN'].guid, CN_GUID);
    assert.strictEqual(byName['Demo IME CN'].textService.marker, 'demo-cn-service');
    assert.strictEqual(byName['Demo without a guid'].guid, undefined,
      'a manifest without a guid registers no key');

    const byId = loadServiceById(GUID.toLowerCase(), baseDir);
    assert.strictEqual(byId.marker, 'demo-service', 'GUID lookup is case-insensitive');
    assert.strictEqual(loadServiceById('{00000000-0000-0000-0000-000000000000}', baseDir), null);

    // The second Windows input language activates with its own GUID (#481
    // round 2): the loader has to answer for it, or a client that picks the
    // Simplified-Chinese bucket gets no service at all.
    const byCn = loadServiceById(CN_GUID.toLowerCase(), baseDir);
    assert.strictEqual(byCn.marker, 'demo-cn-service',
      'the Simplified folder resolves to its own module');
    assert.notStrictEqual(byCn, byId,
      'the two folders are two lookups, not one shared key');
    // Both sides are lowercased, so the manifest's upper-case form and the
    // client's lower-case form meet in the middle.
    assert.strictEqual(loadServiceById(CN_GUID, baseDir), byCn,
      'the Simplified lookup is case-insensitive on both sides');
    // A manifest without a guid contributes no key.
    assert.strictEqual(loadServiceById('demo-no-guid', baseDir), null,
      'a folder without a guid in its manifest registers no key');
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
