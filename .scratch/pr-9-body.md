refactor(go): one wire reply shape in pime.Response.WireMap

No separate issue; the reply shape is the whole story.

The go backend spelled the reply keys twice — once in the shipped server and
once in the package-local serialiser — and the two drifted on which key the
C++ client reads. One shape now answers every adapter.

- `go-backend/pime/protocol.go` carries the reply shape once in
  `pime.Response.WireMap`, used by both the shipped server and the
  package-local `ToJSON`, so the wire key the C++ client reads ("return") is
  the same key everywhere.
- `go-backend/server.go` marshals through that one shape;
  `go-backend/pime/protocol_test.go` resolves `$guid` and `$unknownGuid`
  before marshalling a request.
- `node/test/server.test.js` and `node/tests/nimeServer.test.js` resolve the
  same request/reply set at every depth, and the launcher builds its frame
  from the resolved request in `PIMELauncher/src/protocol.rs`.

Validation:

- `go test ./...` in `go-backend`: the four packages stay green and the
  reply shape resolves from the one place.
- `python/python3/python.exe` `-m unittest discover -s tests -p "test_server_protocol.py"`
  on the integration tree carrying this diff.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
