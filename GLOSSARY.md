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

**Phrase mode (聯想字)**:
The state after a character is committed in which the engine offers follow-on phrase
candidates keyed by the last committed string.
_Avoid_: association mode, autocomplete

**Wildcard pattern**:
A composition containing the wildcard character (`*` or `z`), which stands for one unknown key at
that position.
_Avoid_: mask, regex

**Wildcard query**:
The expansion of a wildcard pattern into the candidate set whose input codes match it.
_Avoid_: wildcard search, fuzzy lookup

**Character tier**:
The ordering class of a character in wildcard results: common, rare, or other.
_Avoid_: bucket, charset group

**Support floor**:
The oldest Windows release an installable artifact is allowed to run on, for every component that
artifact ships.
_Avoid_: minimum OS, minimum version, compatibility target

**Five-stroke keyset (五筆畫)**:
The five stroke classes used as input keys for stroke input — 橫、豎、撇、捺、點 folded into 橫豎撇捺折 — written with the home keys `h s p n z` and displayed as `一丨丿丶乙`.
_Avoid_: wubi (五筆 refers to the 五筆字型 shape method), five strokes (ambiguous with stroke count)

**Stroke table (筆畫表)**:
The chardefs mapping every stroke sequence, and every prefix of one, to the characters written with exactly those strokes; the sole table backing the stroke Service.
_Avoid_: stroke dictionary (a Rime artifact), stroke dict

**Capability roster (能力名冊)**:
The single declaration of which engine capabilities a Service may use; a Service outside the roster gets
neither the behaviour nor its 功能開關 menu items, whatever its own configuration package says. Today the
only rostered capability is Intelligent select.
_Avoid_: feature flag, capability flag, feature list, whitelist

**Intelligent select (智慧選字)**:
The engine capability that reorders the Candidate set for a composition key by the user's own selection
counts, optionally weighted by recent picks and the preceding character.
_Avoid_: learning mode, smart selection, frequency sorting
