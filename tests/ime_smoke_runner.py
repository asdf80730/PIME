"""Smoke-runs the Python input methods that can load on Linux.

Executed by test_input_methods_smoke.py inside a throwaway working directory:
the services create their user config under the literal ``%APPDATA%`` path,
which stays inside that directory on Linux. Results are written as JSON so the
services' own prints cannot corrupt the report.
"""

# Generated with assistance from DeepSeek V4.1 Flash.

import ctypes
import errno
import importlib
import json
import sys
import traceback
import types

SERVICES = [
    ("braille_chewing", "input_methods.braille_chewing.braille_chewing_ime"),
    ("chearray", "input_methods.chearray.chearray_ime"),
    ("checj", "input_methods.checj.checj_ime"),
    ("chedayi", "input_methods.chedayi.chedayi_ime"),
    ("cheeng", "input_methods.cheeng.cheeng_ime"),
    ("cheez", "input_methods.cheez.cheez_ime"),
    ("cheliu", "input_methods.cheliu.cheliu_ime"),
    ("chephonetic", "input_methods.chephonetic.chephonetic_ime"),
    ("chepinyin", "input_methods.chepinyin.chepinyin_ime"),
    ("chesimplex", "input_methods.chesimplex.chesimplex_ime"),
    ("chewing", "input_methods.chewing.chewing_ime"),
    ("meow", "input_methods.meow.ime_meow"),
    ("rime", "input_methods.rime.rime_ime"),
]

# Environment problems, not product failures: the bundled Python bindings need
# the libchewing/librime builds that ship with PIME, which are not in a Linux
# checkout's system paths in a matching version.
SKIP_MARKERS = (
    ("set_autoLearn", "system libchewing does not match the bundled binding"),
    ("libchewing.so", "libchewing is not installed"),
    # #988 made a failed context creation raise; the DLLs this checkout ships
    # are Windows builds, so the context cannot be created here.
    ("Failed to create chewing context", "libchewing cannot create a context on Linux"),
    ("librime.so", "librime is not installed"),
    ("Rime.dll", "rime.dll is Windows-only"),
)

BASE_EVENT = {
    "charCode": 0,
    "keyCode": 0,
    "repeatCount": 1,
    "scanCode": 0,
    "isExtended": False,
    "keyStates": [0] * 256,
}


class FakeDLL:
    """Returns a no-op for every Win32 function the services call at load time."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: 0


class FakeClient:
    isWindows8Above = True
    isMetroApp = False
    isUiLess = False
    isConsole = False


def install_windows_shims():
    if sys.platform == "win32":
        return
    sys.modules.setdefault(
        "winsound",
        types.SimpleNamespace(PlaySound=lambda *args, **kwargs: None, SND_ASYNC=1),
    )
    if not hasattr(ctypes, "windll"):
        ctypes.windll = FakeDLL()
    if not hasattr(ctypes, "WinDLL"):
        ctypes.WinDLL = lambda *args, **kwargs: FakeDLL()


def opencc_available():
    """True when the opencc shared library can be loaded.

    The cinbase family imports opencc at module scope, so a machine without
    ``libopencc.so`` errors on import instead of failing an assertion; the
    tests skip on this probe rather than reporting a missing library as a bug.
    """
    try:
        ctypes.CDLL("libopencc.so")
        return True
    except OSError:
        return False


def under_wine():
    """True for Wine's Win32 emulation, which lacks calls real Windows has.

    Wine ships ntdll's ``wine_get_version`` export, so this separates the two
    without touching a Win32 function itself.
    """
    if sys.platform != "win32":
        return False
    try:
        return hasattr(ctypes.windll.ntdll, "wine_get_version")
    except OSError:
        return False


def service_class(module):
    classes = [
        value for value in vars(module).values()
        if isinstance(value, type)
        and value.__module__ == module.__name__
        and value.__name__.endswith("TextService")
    ]
    if not classes:
        raise LookupError(f"no TextService subclass defined in {module.__name__}")
    return classes[0]


def key_event(method, char_code):
    event = dict(BASE_EVENT)
    event.update(method=method, charCode=char_code, keyCode=char_code, seqNum=1)
    return event


def import_service(module_name, attempts=2):
    """Import a service module, retrying the importer's own EBADF.

    This checkout has failed ``os.listdir`` inside importlib with EBADF; the
    path in the error is the package directory, and no service code has run
    yet, so one retry cannot hide a product failure.
    """
    for attempt in range(attempts):
        try:
            return importlib.import_module(module_name)
        except OSError as error:
            if attempt + 1 == attempts or error.errno != errno.EBADF:
                raise


def run_service(module_name):
    module = import_service(module_name)
    service = service_class(module)(FakeClient())

    reply = service.handleRequest({"method": "onActivate", "isKeyboardOpen": True, "seqNum": 1})
    if not reply.get("success"):
        raise RuntimeError(f"onActivate failed: {reply}")

    for char_code in (ord("a"), ord("1"), ord(" ")):
        for method in ("filterKeyDown", "onKeyDown"):
            reply = service.handleRequest(key_event(method, char_code))
            if not reply.get("success"):
                raise RuntimeError(f"{method}({char_code}) failed: {reply}")


def classify(error):
    text = str(error)
    for marker, reason in SKIP_MARKERS:
        if marker in text:
            return "skipped", f"{reason}: {text}"
    return "error", "".join(traceback.format_exception_only(type(error), error)).strip()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: ime_smoke_runner.py RESULTS_JSON")
    install_windows_shims()

    results = []
    for name, module_name in SERVICES:
        try:
            run_service(module_name)
            results.append({"service": name, "status": "ok", "detail": ""})
        except Exception as error:  # noqa: BLE001 - every failure is a result row
            status, detail = classify(error)
            results.append({"service": name, "status": status, "detail": detail})

    with open(sys.argv[1], "w", encoding="utf-8") as output:
        json.dump(results, output, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
