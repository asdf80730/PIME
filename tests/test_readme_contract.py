"""Keep README build steps in sync with the scripts that define them.

The README names the CMake generator, policy flag, build directories and
installer command. Those values live in build.bat and the CI scripts; this
test fails when one side moves without the other.

Generated with assistance from omp (deepseek-v4.1-flash).
"""

import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
README = os.path.join(ROOT, "README.md")
BUILD_BAT = os.path.join(ROOT, "build.bat")
APPVEYOR = os.path.join(ROOT, "appveyor.after_build.bat")


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


if __name__ == "__main__":
    unittest.main()
