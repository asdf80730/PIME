# 06: One `resolve`/`fold` pair behind the two node adapter suites

**What to build:** the byte-identical `resolve()` and `fold()` helpers stop being
maintained twice, the Duplicated Code smell in the fixture loop.

Status: resolved
Category: enhancement
Blocked by: None

- [x] `node/test/server.test.js` and `node/tests/nimeServer.test.js` reach one shared
      helper module, and the `return` key's boolean-versus-1/0 fold lives in that one place
- [x] `node --test node/tests/nimeServer.test.js` and `node node/test/server.test.js`
      each still answer 23 fixture cases

## Answer

`3592ebe` (`refactor(node): share the resolve/fold fixture helpers behind one module`)
adds `node/wireHelpers.js` and reduces both suites to requiring it; the `return`-key
boolean/1-0 fold exists once, in that module. The two suites keep their own runners, which
is the layer `spec.md` row 9 pins through `tests/wire-fixtures.json`.

Settling, 2026-11-16, on this tree:

- `./.tools/node/node.exe --test node/tests/nimeServer.test.js` → TAP `# pass 23`,
  `# fail 0`, rc 0.
- `node node/test/server.test.js` → `node backend: 23 wire fixture case(s) answered`, rc 0.
- `node node/test/loadServices.test.js` → `node backend: ime.json discovery keeps directory
  filtering and GUID lookup`, rc 0.

The go side keeps its own `wireFold`/`resolveWireValue`: a per-language pair is the
existing convention and stays.

## Comments

The go side keeps its own `wireFold`/`resolveWireValue`: a per-language pair is the
existing convention and stays.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
