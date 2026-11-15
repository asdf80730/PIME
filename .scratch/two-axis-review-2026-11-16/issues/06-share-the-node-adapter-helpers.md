# 06: One `resolve`/`fold` pair behind the two node adapter suites

**What to build:** the byte-identical `resolve()` and `fold()` helpers stop being
maintained twice, the Duplicated Code smell in the fixture loop.

Status: ready-for-agent
Category: enhancement
Blocked by: None

- [ ] `node/test/server.test.js` and `node/tests/nimeServer.test.js` reach one shared
      helper module, and the `return` key's boolean-versus-1/0 fold lives in that one place
- [ ] `node --test node/tests/nimeServer.test.js` and `node node/test/server.test.js`
      each still answer 23 fixture cases

## Comments

The go side keeps its own `wireFold`/`resolveWireValue`: a per-language pair is the
existing convention and stays.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
