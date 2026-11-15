"""Keep README build steps in sync with the scripts that define them.

The README names the CMake generator, policy flag, build directories and
installer command. Those values live in build.bat and the CI scripts; this
test fails when one side moves without the other.

Generated with assistance from omp (deepseek-v4.1-flash).
"""

import json
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
README = os.path.join(ROOT, "README.md")
BUILD_BAT = os.path.join(ROOT, "build.bat")
APPVEYOR = os.path.join(ROOT, "appveyor.after_build.bat")
GO_README = os.path.join(ROOT, "go-backend", "README.md")
WIRE_FIXTURES = os.path.join(ROOT, "tests", "wire-fixtures.json")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class ReadmeBuildContractTests(unittest.TestCase):
    def setUp(self):
        self.readme = read(README)
        self.build_bat = read(BUILD_BAT)

    def test_cmake_generator_matches_build_bat(self):
        generators = set(re.findall(r'-G\s+"([^"]+)"', self.build_bat))
        self.assertTrue(generators, "build.bat has no CMake generator")
        for generator in generators:
            with self.subTest(generator=generator):
                self.assertIn(generator, self.readme)

    def test_cmake_policy_flag_matches_build_bat(self):
        flags = set(re.findall(r"-DCMAKE_POLICY_VERSION_MINIMUM=\S+", self.build_bat))
        self.assertTrue(flags, "build.bat has no CMake policy flag")
        for flag in sorted(flags):
            with self.subTest(flag=flag):
                self.assertEqual(self.readme.count(flag), self.build_bat.count(flag))

    def test_build_directories_are_documented(self):
        directories = set(re.findall(r"-B(build\w*)", self.build_bat))
        self.assertTrue(directories, "build.bat has no build directories")
        for directory in sorted(directories):
            with self.subTest(directory=directory):
                self.assertIn(f"-B{directory}", self.readme)

    def test_installer_command_matches_ci(self):
        match = re.search(r"([\w.\\-]*installer\.nsi)", read(APPVEYOR))
        self.assertIsNotNone(match, "appveyor script has no installer script")
        script = match.group(1)
        self.assertIn(f"makensis {script}", self.readme)

    def test_install_section_uses_the_installer(self):
        install = self.readme.split("# Install", 1)[1].split("# Uninstall", 1)[0]
        self.assertIn("setup.exe", install)
        self.assertNotIn("Copy `PIMETextService.dll`", install)

    def test_uninstall_section_uses_the_uninstaller(self):
        uninstall = self.readme.split("# Uninstall", 1)[1]
        self.assertIn("Uninstall.exe", uninstall)
        self.assertNotIn("regsvr32 /u", uninstall)

    def test_stale_build_instructions_are_gone(self):
        for stale in ("Visual Studio 16 2019", "pywin32"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, self.readme)


class GoReadmeReplyShapeTests(unittest.TestCase):
    """The go README's sample reply uses the keys the backend really writes.

    `go-backend/pime/protocol.go` builds every reply through
    `Response.WireMap()`, whose key set is the one declared in
    `tests/wire-fixtures.json` (`replyKeys` plus `extraKeys`, `INV-10`), so a
    sample naming an undeclared key is a stale example the next agent trusts.
    """

    def _sample_keys(self):
        with open(GO_README, encoding="utf-8") as handle:
            text = handle.read()
        blocks = re.findall(r"```json\n(.*?)```", text, re.S)
        for block in blocks:
            if '"success"' in block:
                return set(re.findall(r'^\s*"(\w+)"\s*:', block, re.M))
        self.fail("go-backend/README.md has no response sample")

    def test_sample_reply_uses_only_declared_keys(self):
        with open(WIRE_FIXTURES, encoding="utf-8") as handle:
            fixture = json.load(handle)
        declared = set(fixture["replyKeys"]) | set(fixture["extraKeys"])
        keys = self._sample_keys()
        self.assertTrue(keys, "the response sample names no key")
        for key in sorted(keys - declared):
            self.fail("the go README sample replies with the undeclared key %r; "
                      "WireMap writes %s" % (key, sorted(declared)))

    def test_sample_reply_names_the_folded_return_key(self):
        # The C++ client reads "return" for the eaten/not-eaten answer; the
        # folded integer form is not a wire key of its own.
        self.assertIn("return", self._sample_keys())


if __name__ == "__main__":
    unittest.main()
