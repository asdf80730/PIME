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
                "PIMETextService/", "PIMELauncher/", "libIME2/")

# References that name a file which does not exist and is not meant to:
# an optional file the domain layout may or may not have, and a path template
# for a file the issue-tracker workflow creates at runtime.
OPTIONAL_REFERENCES = {
    # domain.md: "GLOSSARY-MAP.md at the repo root if it exists".
    "GLOSSARY-MAP.md",
    # issue-tracker.md: ".scratch/<effort>/map.md", created per effort.
    "map.md",
}


def agent_doc_files():
    """AGENTS.md plus every Markdown file under docs/agents/."""
    files = [os.path.join(ROOT, "AGENTS.md")]
    for name in sorted(os.listdir(AGENTS_DOCS_DIR)):
        if name.endswith(".md"):
            files.append(os.path.join(AGENTS_DOCS_DIR, name))
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


if __name__ == "__main__":
    unittest.main()
