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
        flag = "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
        expected = self.build_bat.count(flag)
        self.assertGreater(expected, 0)
        self.assertEqual(self.readme.count(flag), expected)

    def test_build_directories_are_documented(self):
        directories = set(re.findall(r"-B(build\w*)", self.build_bat))
        self.assertTrue(directories, "build.bat has no build directories")
        for directory in sorted(directories):
            with self.subTest(directory=directory):
                self.assertIn(f"-B{directory}", self.readme)

    def test_installer_command_matches_ci(self):
        self.assertIn(r"makensis installer\installer.nsi", self.readme)
        self.assertIn(r"installer\installer.nsi", read(APPVEYOR))

    def test_stale_build_instructions_are_gone(self):
        for stale in ("Visual Studio 16 2019", "pywin32"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, self.readme)


if __name__ == "__main__":
    unittest.main()
