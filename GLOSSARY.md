# PIME

A Windows text service (TSF) that forwards input to an out-of-process backend written in a
scripting language, so input methods can be developed without touching C++.

## Language

**Service**:
An input method module hosted by a backend, registered under a language-profile GUID, and
exporting `textReducer` and `response`.
_Avoid_: text service, IME module

**Backend**:
A process that hosts services and speaks the line protocol with the launcher; named in
`backends.json` (`python`, `node`, `go-backend`).
_Avoid_: server

**PIMETextService**:
The C++ TSF client DLL; the only component Windows loads into the host application.
_Avoid_: text service, client DLL

**Client**:
One pipe connection between `PIMETextService` and `PIMELauncher`, identified to the backend by a
freshly generated UUID.
_Avoid_: session, connection

**Init**:
The first request on every pipe connection; carries the language-profile GUID and the request that
resolves the GUID to a backend and a service.
_Avoid_: handshake, login

**Candidate**:
One completion item offered for the current composition or menu.
_Avoid_: suggestion, completion

**Candidate set**:
All candidates for the current composition or menu, before pagination.
_Avoid_: candidate list, candidate pool

**Candidate page**:
The subset of a candidate set shown at once.
_Avoid_: chunk, page candidates, candidate list

**Candidate cursor**:
The index of the highlighted candidate within the current candidate page.
_Avoid_: selection, selected index

**CandidateView**:
The paginated, selectable view of a candidate set: its page size, current page, and cursor.
_Avoid_: pager, candidate list model
