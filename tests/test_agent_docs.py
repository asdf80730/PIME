"""Static checks for the agent-facing Markdown under docs/agents/.

AGENTS.md and docs/agents/*.md point each other at files: `docs/agents/issue-tracker.md`
names `triage-labels.md`, AGENTS.md names every file under `docs/agents/`, and the
research notes cite `docs/agents/verification.md` by section. Nothing checked that
those pointers still resolve, so renaming a file left a silently dangling reference.

These checks assert that every file reference in those documents resolves to a
file that exists. They run with the rest of the suite and from the paths-filtered
docs workflow.

Generated with assistance from DeepSeek V4.1 Flash.
"""

import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
AGENTS_DOCS_DIR = os.path.join(ROOT, "docs", "agents")

# A path reference inside backticks or a Markdown link target. Deliberately narrow:
# only tokens that look like a file path with a known extension count, so prose
# like `docs/adr/` (a directory that may legitimately not exist yet) is ignored.
PATH_REFERENCE = re.compile(
    r"`(?P<inline>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|sh|py|yaml|yml|nsi|ns))`"
    r"|\]\((?P<link>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|sh|py|yaml|yml|nsi|ns))[^)]*\)"
)

# Directories a bare or partial path may be relative to, besides the repo root.
# A document that says `cinbase/__init__.py` means the one under `python/`.
SOURCE_ROOTS = ("", "python/", "node/", "tests/", "go-backend/", "installer/",
                "PIMETextService/", "PIMELauncher/", "libIME2/",
                ".github/workflows/")

# References that name a file which does not exist and is not meant to:
# an optional file the domain layout may or may not have, and a path template
# for a file the issue-tracker workflow creates at runtime.
OPTIONAL_REFERENCES = {
    # domain.md: "GLOSSARY-MAP.md at the repo root if it exists".
    "GLOSSARY-MAP.md",
    # issue-tracker.md: ".scratch/<effort>/map.md", created per effort.
    "map.md",
    # issue-tracker.md: ".scratch/<name>/ARCHIVE.md", created when an archive lands.
    "ARCHIVE.md",
}


def agent_doc_files():
    """AGENTS.md plus every Markdown file under docs/agents/."""
    files = [os.path.join(ROOT, "AGENTS.md")]
    for name in sorted(os.listdir(AGENTS_DOCS_DIR)):
        if name.endswith(".md"):
            files.append(os.path.join(AGENTS_DOCS_DIR, name))
    return files


def citation_scanned_files():
    """Files whose AGENTS.md citations the stale-citation ban judges: the agent
    docs, the research notes, and the harness scripts whose comments and failure
    messages carry a citation to whoever reads one.
    """
    files = [os.path.join(ROOT, "AGENTS.md")]
    for subdir in (os.path.join(ROOT, "docs", "agents"),
                   os.path.join(ROOT, "docs", "research")):
        for name in sorted(os.listdir(subdir)):
            if name.endswith(".md"):
                files.append(os.path.join(subdir, name))
    tests_dir = os.path.join(ROOT, "tests")
    for name in sorted(os.listdir(tests_dir)):
        if name.endswith(".sh"):
            files.append(os.path.join(tests_dir, name))
    hooks_dir = os.path.join(tests_dir, "hooks")
    for name in sorted(os.listdir(hooks_dir)):
        files.append(os.path.join(hooks_dir, name))
    return files


def references(text):
    """Yield every file reference found in `text`."""
    for match in PATH_REFERENCE.finditer(text):
        value = match.group("inline") or match.group("link")
        if value.startswith(("http://", "https://", "mailto:")):
            continue
        yield value


def resolves(doc_path, reference):
    """True when `reference`, read from `doc_path`, names a file that exists.

    A reference may be relative to the document that mentions it (a sibling
    agent doc), relative to the repo root, or relative to one of the source
    directories above.
    """
    bases = [os.path.dirname(doc_path)]
    for source_root in SOURCE_ROOTS:
        bases.append(os.path.join(ROOT, source_root))
    for base in bases:
        candidate = os.path.normpath(os.path.join(base, reference))
        if os.path.isfile(candidate):
            return True
    return False


class AgentDocTests(unittest.TestCase):
    def test_agent_docs_exist(self):
        self.assertTrue(os.path.isdir(AGENTS_DOCS_DIR),
                        "expected docs/agents/ to hold the agent docs")

    def test_referenced_paths_resolve(self):
        for path in agent_doc_files():
            name = os.path.relpath(path, ROOT)
            with open(path, encoding="utf-8") as doc:
                text = doc.read()
            for reference in references(text):
                if reference in OPTIONAL_REFERENCES:
                    continue
                with self.subTest(doc=name, reference=reference):
                    self.assertTrue(
                        resolves(path, reference),
                        f"{name}: references {reference!r}, which names no "
                        f"existing file")

    def test_agents_md_names_every_agent_doc(self):
        """AGENTS.md is the index; an unreferenced doc is unreachable by an agent."""
        with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as agents:
            text = agents.read()
        named = set(references(text))
        for name in sorted(os.listdir(AGENTS_DOCS_DIR)):
            if not name.endswith(".md"):
                continue
            with self.subTest(doc=name):
                self.assertTrue(
                    any(os.path.basename(reference) == name for reference in named),
                    f"AGENTS.md does not reference docs/agents/{name}")

    def test_agents_md_is_cited_by_heading_not_by_number(self):
        """The rules prose moved to the standing rules of docs/agents/code-review.md
        on 2026-10-30, and the citations naming AGENTS.md by section or line number
        went dangling in one commit, caught only by hand. Cite headings by name:
        numbers and lines are banned in every file that carries a citation, so the
        next move reddens this check instead of stranding references silently.
        """
        pattern = re.compile(r"AGENTS\.md`?\s*§|AGENTS\.md:\d")
        offenders = []
        for path in citation_scanned_files():
            with open(path, encoding="utf-8") as doc:
                for number, line in enumerate(doc, 1):
                    if pattern.search(line):
                        offenders.append(
                            f"{os.path.relpath(path, ROOT)}:{number}: {line.strip()}")
        self.assertEqual([], offenders,
                         "cite AGENTS.md headings by name, never by section or "
                         "line number")

    def test_glossary_terms_follow_the_format(self):
        """GLOSSARY.md is a glossary: every term is **Term**: + definition + _Avoid_."""
        path = os.path.join(ROOT, "GLOSSARY.md")
        if not os.path.isfile(path):
            self.skipTest("no GLOSSARY.md yet")
        with open(path, encoding="utf-8") as glossary:
            lines = glossary.read().splitlines()
        term = None
        for number, line in enumerate(lines, start=1):
            if line.startswith("**") and line.endswith("**:"):
                self._require_avoid(term, number)
                term = (number, line[2:-2], False)
            elif line.startswith("_Avoid_:"):
                self.assertIsNotNone(
                    term, f"GLOSSARY.md:{number}: _Avoid_ without a **Term**: header")
                term = None
            elif line and not line.startswith(("#", "_", " ")) and term is not None:
                if not term[2]:
                    term = (term[0], term[1], True)
        self._require_avoid(term, len(lines) + 1)

    @staticmethod
    def _require_avoid(term, seen_at):
        if term is not None:
            raise AssertionError(
                f"GLOSSARY.md:{term[0]}: term {term[1]!r} has no _Avoid_ line "
                f"before line {seen_at}")


if __name__ == "__main__":
    unittest.main()
