# PIME Key Bridge

Type Chinese in windows that TSF never reaches — the Windows 11 taskbar
search box and its flyout among them.

The taskbar search box is a XAML island. It runs on its own thread with its
own `ITfThreadMgr` and drives its own document, so the PIME text service is
never advised for it: its key events stop at the island and the box takes the
raw Latin characters. This helper does the one thing that thread will not
do — it takes the keys off the keyboard and hands them to the PIME backend
itself, over the launcher pipe, exactly as the C++ client does.

## Run it

```
python/python3/python.exe -m keybridge
```

From an installed tree the interpreter and the package sit next to each
other:

```
%USERPROFILE%\pime-root\python\python3\python.exe -m keybridge
```

The bridge talks to `PIMELauncher.exe`, so the launcher has to be running.

Options:

| option | what it does |
|---|---|
| `--profile GUID` | the language profile of the backend (default: the chewing module) |
| `--target EXE` | an executable whose keys are forwarded; repeatable (default: `SearchHost.exe`, `TextInputHost.exe`) |
| `--debug` | print every key event and every reply |
| `--probe` | send a syllable straight over the pipe and print the replies, without touching the keyboard |

## What it does

- a low-level keyboard hook watches the keys of the target processes only;
  every other key reaches its application untouched;
- the keys go to the backend as the same JSON the C++ client sends, and the
  backend answers for each of them, so the backend composes as it does for
  a host it owns — and the keys the backend refuses (`Ctrl+C`, the arrow
  keys, `Escape`) reach the application;
- the composition is typed into the control that has the focus, and the
  committed text replaces it — what an IME does in a host it owns;
- a small window of the bridge's own shows the composition and the candidate
  list, the way a candidate window does.

## The keys

The backend decides what the keys mean, so the same keys work as in any
other host: with the chewing module, `ji5` composes ㄓㄨㄛ, Space selects
桌 and Enter commits it.

The input mode is the backend's too, the way the language bar button of the
C++ client owns it. `Ctrl+Space` asks the backend to switch between
Chinese and English, and the English letters then reach the application
untouched.

## Not a service

The bridge is a helper the user starts; it is not started by the installer
and it does not run in the background on its own.
