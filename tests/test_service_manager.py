import os
import sys
import json
import shutil
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from serviceManager import TextServiceManager, TextServiceInfo, dir_path_to_import_path
from server import Server, Client


class ServiceManagerTests(unittest.TestCase):
    def setUp(self):
        self.test_root = os.path.join(ROOT, "scratch", f"test_im_dir_{os.getpid()}")
        os.makedirs(self.test_root, exist_ok=True)
        sys.path.insert(0, self.test_root)
        self._saved_modules = {
            k: v for k, v in sys.modules.items()
            if k == "input_methods" or k.startswith("input_methods.")
        }
        for k in self._saved_modules:
            del sys.modules[k]

    def tearDown(self):
        if self.test_root in sys.path:
            sys.path.remove(self.test_root)
        for k in list(sys.modules.keys()):
            if k == "input_methods" or k.startswith("input_methods."):
                del sys.modules[k]
        sys.modules.update(self._saved_modules)
        shutil.rmtree(self.test_root, ignore_errors=True)

    def _create_dummy_ime(self, subdir_name, guid, module_name="my_ime",
                          class_name="MyService"):
        pkg_dir = os.path.join(self.test_root, "input_methods")
        os.makedirs(pkg_dir, exist_ok=True)
        init_file = os.path.join(pkg_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                pass

        im_dir = os.path.join(pkg_dir, subdir_name)
        os.makedirs(im_dir, exist_ok=True)
        ime_json = os.path.join(im_dir, "ime.json")
        payload = {
            "name": "Test IME",
            "moduleName": module_name,
            "serviceName": class_name,
            "guid": guid,
        }
        with open(ime_json, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        py_file = os.path.join(im_dir, f"{module_name}.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(f"""class {class_name}:
    def __init__(self, client):
        self.client = client
""")
        return im_dir

    def test_init_is_empty(self):
        mgr = TextServiceManager()
        self.assertEqual(mgr.services, {})

    def test_load_nonexistent_directory_raises_oserror(self):
        mgr = TextServiceManager()
        with self.assertRaises(OSError):
            mgr.load(os.path.join(self.test_root, "nonexistent"))

    def test_load_from_directory_registers_services(self):
        guid = "{11111111-2222-3333-4444-555555555555}"
        self._create_dummy_ime("dummy1", guid)

        mgr = TextServiceManager()
        mgr.load(self.test_root)

        self.assertIn(guid.lower(), mgr.services)
        self.assertEqual(mgr.services[guid.lower()].name, "Test IME")

    def test_two_language_folders_resolve_to_their_own_service(self):
        # #481: the rime engine serves two Windows input languages, so it ships
        # one folder per language and each profile activates with its own GUID.
        # The dispatcher must know both, or the client gets no service.
        traditional = "{9c2d6c68-9ea6-4cfb-a769-7e619db7f267}"
        simplified = "{53C15256-7A5F-4B54-86E8-0636E0745C3E}"
        self._create_dummy_ime("dummy_tw", traditional,
                               module_name="tw_mod", class_name="TwClass")
        self._create_dummy_ime("dummy_cn", simplified,
                               module_name="cn_mod", class_name="CnClass")

        mgr = TextServiceManager()
        mgr.load(self.test_root)

        self.assertEqual([simplified.lower(), traditional.lower()],
                         sorted(mgr.services, key=str.lower)[:2])
        self.assertIsNot(mgr.services[traditional.lower()],
                         mgr.services[simplified.lower()],
                         "each folder carries its own info")
        for guid in (traditional, simplified):
            service = mgr.createService("dummy_client", guid)
            self.assertIsNotNone(service,
                                 "the profile GUID %s started no service" % guid)
            self.assertEqual(service.client, "dummy_client")

    def test_shipped_rime_manifests_register_both_profiles(self):
        # The synthetic fixture above proves the loader reads one guid per
        # manifest; this case drives the same dispatcher over the product's own
        # registration data, so a key a shipped manifest forgets — or a
        # dispatcher that stops reading it — reddens here instead of at the
        # first client that activates that locale.
        mgr = TextServiceManager()
        mgr.load(PYTHON_DIR)

        guids = {}
        for name, expected in (
                ("rime", "{9c2d6c68-9ea6-4cfb-a769-7e619db7f267}"),
                ("rime-cn", "{53c15256-7a5f-4b54-86e8-0636e0745c3e}")):
            with open(os.path.join(PYTHON_DIR, "input_methods", name,
                                   "ime.json"), encoding="utf-8") as fp:
                manifest = json.load(fp)
            guid = manifest["guid"].lower()
            # Pinned literally as well: the GUID DllRegisterServer hands to
            # AddLanguageProfile for this folder, so a silent rename in the
            # manifest is a finding.
            self.assertEqual(expected, guid)
            self.assertIn(guid, mgr.services,
                          "the shipped %s profile is unknown to the dispatcher"
                          % name)
            self.assertEqual(mgr.services[guid].guid, guid)
            self.assertNotIn("additionalProfiles", manifest,
                             "one manifest is one language profile")
            guids[name] = guid
        self.assertIsNot(mgr.services[guids["rime"]],
                         mgr.services[guids["rime-cn"]],
                         "the two folders are two infos, not one shared key")
        # Both profiles run the same engine, so the Simplified one is a second
        # window on one implementation: same module file name, same class name
        # (each folder's dotted module name is its own, per its directory).
        for field in ("moduleName", "serviceName"):
            self.assertEqual(getattr(mgr.services[guids["rime"]], field).split(".")[-1],
                             getattr(mgr.services[guids["rime-cn"]], field).split(".")[-1],
                             "the two rime folders load different %s" % field)

        # meow is the other IME this tree serves, and the one IME shipping in
        # all three backends: its own shipped key has to answer in this runner
        # too, under the same literal-pinned style as the rime pair above.
        with open(os.path.join(PYTHON_DIR, "input_methods", "meow", "ime.json"),
                  encoding="utf-8") as fp:
            meow_manifest = json.load(fp)
        meow_guid = meow_manifest["guid"].lower()
        # Pinned literally as well: the one GUID DllRegisterServer hands to
        # AddLanguageProfile for 喵喵輸入法 in this tree.
        self.assertEqual("{c5f37da0-274e-4837-9b7c-9bb79fe85d9d}", meow_guid)
        self.assertIn(meow_guid, mgr.services,
                      "the shipped meow profile is unknown to the dispatcher")
        meow_info = mgr.services[meow_guid]
        self.assertEqual(meow_info.name, "喵喵輸入法")
        self.assertEqual(meow_info.guid, meow_guid,
                         "the meow key is the info's own guid, not a neighbour's")

    def test_every_shipped_python_ime_is_resolvable_by_its_own_guid(self):
        # The per-file invariants in test_rime_registration_locale.py prove each
        # manifest is well-formed; this walks the same tree through the real
        # dispatcher: every shipped GUID is present as a key, every GUID of one
        # file names that file's own info object, and the shipped-directory
        # count is pinned. A duplicate primary across two files is invisible
        # here: the map holds one entry, so both files' lookups still pass.
        mgr = TextServiceManager()
        mgr.load(PYTHON_DIR)
        input_methods_dir = os.path.join(PYTHON_DIR, "input_methods")
        seen = 0
        for name in sorted(os.listdir(input_methods_dir)):
            path = os.path.join(input_methods_dir, name, "ime.json")
            if not os.path.isfile(path):
                continue
            seen += 1
            with open(path, encoding="utf-8") as fp:
                manifest = json.load(fp)
            guid = manifest["guid"].lower()
            with self.subTest(ime=name, guid=guid):
                self.assertIn(guid, mgr.services,
                              "a shipped profile GUID is unknown to the dispatcher")
                self.assertEqual(mgr.services[guid].guid, guid,
                                 "the key is the info's own guid, not a neighbour's")
                self.assertTrue(mgr.services[guid].name,
                                "a registered profile carries no display name")
        # 15 named cases today: the 12 cinbase/chewing IMEs, meow, and the two
        # rime language folders. An added directory has to show up here as its
        # own named lookup, so this count is the guard against a profile
        # slipping in unnamed.
        self.assertEqual(seen, 15, "the python tree ships 15 ime.json files")
        self.assertIsNone(mgr.createService(None, "{00000000-0000-0000-0000-000000000001}"),
                          "an id no shipped manifest names starts no service")

    def test_load_from_json_with_explicit_base_dir(self):
        guid = "{33333333-4444-5555-6666-777777777777}"
        im_dir = self._create_dummy_ime("dummy_explicit", guid, module_name="exp_mod", class_name="ExpClass")
        json_file = os.path.join(im_dir, "ime.json")

        info = TextServiceInfo()
        info.loadFromJson(json_file, self.test_root)

        self.assertEqual(info.moduleName, "input_methods.dummy_explicit.exp_mod")
        self.assertEqual(info.guid, guid.lower())

    def test_create_service_instance(self):
        guid = "{12345678-abcd-ef01-2345-6789abcdef01}"
        self._create_dummy_ime("dummy3", guid, module_name="test_mod", class_name="TestClass")

        mgr = TextServiceManager()
        mgr.load(self.test_root)
        service = mgr.createService("dummy_client", guid)

        self.assertIsNotNone(service)
        self.assertEqual(service.client, "dummy_client")

    def test_create_service_unknown_guid_returns_none(self):
        mgr = TextServiceManager()
        self.assertIsNone(mgr.createService(None, "{00000000-0000-0000-0000-000000000000}"))

    def test_server_delegates_to_service_manager(self):
        guid = "{fedcba98-7654-3210-fedc-ba9876543210}"
        self._create_dummy_ime("dummy4", guid, module_name="srv_mod", class_name="SrvClass")

        server = Server(self.test_root)

        client = Client(server)
        success = client.init({
            "id": guid,
            "isWindows8Above": True,
            "isMetroApp": False,
            "isUiLess": False,
            "isConsole": False,
        })

        self.assertTrue(success)
        self.assertIsNotNone(client.service)
        self.assertEqual(client.service.client, client)

    def test_dir_path_to_import_path_conversions(self):
        base = os.path.join(self.test_root, "base")
        sub_dir = os.path.join(base, "pkg", "subpkg")
        top_pkg = os.path.join(base, "pkg")

        test_cases = [
            ("sub_dir", sub_dir, "pkg.subpkg"),
            ("top_pkg", top_pkg, "pkg"),
            ("base_dir", base, ""),
        ]

        for name, path, expected in test_cases:
            with self.subTest(case=name, path=path):
                self.assertEqual(dir_path_to_import_path(path, base), expected)

    def test_dir_path_to_import_path_outside_base_raises(self):
        base = os.path.join(self.test_root, "base")
        outside = os.path.join(self.test_root, "outside")

        with self.assertRaises(ValueError):
            dir_path_to_import_path(outside, base)


if __name__ == "__main__":
    unittest.main()
