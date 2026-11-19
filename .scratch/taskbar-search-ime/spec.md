# Spec: the taskbar search box and its flyout under TSF

Status: resolved (2026-11-16 — both shapes answered from a live per-instance
trace on this box; the two tickets carry the tables).

The Windows 11 taskbar hosts its search field and its flyout as XAML islands.
Each island runs on its own thread with its own `ITfThreadMgr`, and a host can
activate the text service without ever delivering
`ITfActiveLanguageProfileNotifySink::OnActivated`. Two consequences, one per
ticket:

- `issues/01` — the `Client` is built only from `onActivate()`, so a service
  activated without `OnActivated` keeps a null client and every key handler
  returns `false` at its guard. The fix builds the client in `onActivate()` and
  gives it the manager's focus document.
- `issues/02` — the flyout's `Edit` receives no key events at all, because the
  keystroke manager dispatches only to the sink owning the focused document of
  *that* thread's manager. Per-instance trace names the `this`, the thread id
  and `GetFocus()` for each island.

## Evidence

`.scratch/taskbar-flyout-probe4.ps1` and `.scratch/uia-tops.ps1` are the two
instruments; `docs/agents/verification.md` names how to run each and what their
`CHECK_*` fields mean. The source read for the XAML-island behaviour is
`tsf-xaml-island-sources.md` beside this file.

Out of scope: the #883 ruler shape (`.scratch/two-axis-review-2026-11-16/`),
the launcher's pipe protocol, and any candidate-window work.
