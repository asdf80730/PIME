"""Static checks for the handbook pages under docs/.

These checks catch broken anchors/assets and ARIA id references without a
browser. They run with the rest of the suite and from a paths-filtered
workflow when docs change.
"""

# Generated with assistance from DeepSeek V4.1 Flash.

import glob
import os
import unittest
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
DOCS_DIR = os.path.join(ROOT, "docs")

SKIPPED_SCHEMES = ("http://", "https://", "mailto:", "data:", "javascript:", "//")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []   # (attribute, value)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        for attribute in ("href", "src", "aria-controls", "aria-labelledby"):
            if attribute in values:
                self.references.append((attribute, values[attribute]))


def parse(path):
    parser = PageParser()
    with open(path, encoding="utf-8") as page:
        parser.feed(page.read())
    return parser


def html_pages():
    return sorted(glob.glob(os.path.join(DOCS_DIR, "**", "*.html"), recursive=True))


class DocsPageTests(unittest.TestCase):
    def test_pages_exist(self):
        self.assertTrue(html_pages(), "expected at least one page under docs/")

    def test_local_links_and_assets_resolve(self):
        for path in html_pages():
            page = os.path.relpath(path, ROOT)
            parser = parse(path)
            for attribute, value in parser.references:
                if attribute not in ("href", "src"):
                    continue
                if value.startswith(SKIPPED_SCHEMES):
                    continue
                with self.subTest(page=page, attribute=attribute, value=value):
                    if value.startswith("#"):
                        self.assertIn(value[1:], parser.ids,
                                      f"{page}: {attribute}={value!r} has no matching id")
                        continue

                    target = value.split("#", 1)[0].split("?", 1)[0]
                    self.assertTrue(target, f"{page}: empty local reference")
                    resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
                    self.assertTrue(os.path.exists(resolved),
                                    f"{page}: {attribute}={value!r} resolves to missing {resolved}")

    def test_ids_are_unique_and_aria_targets_exist(self):
        for path in html_pages():
            page = os.path.relpath(path, ROOT)
            parser = parse(path)

            duplicates = {value for value in parser.ids if parser.ids.count(value) > 1}
            self.assertEqual(duplicates, set(), f"{page}: duplicate ids {sorted(duplicates)}")

            for attribute, value in parser.references:
                if attribute.startswith("aria-"):
                    for target in value.split():
                        with self.subTest(page=page, attribute=attribute, target=target):
                            self.assertIn(target, parser.ids,
                                          f"{page}: {attribute}={value!r} points at a missing id")


if __name__ == "__main__":
    unittest.main()
