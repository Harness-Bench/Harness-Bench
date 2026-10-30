#!/usr/bin/env python3
"""Validate documentation that must live alongside code.

Read-only. Checks that:

1. Every package under ``src/harnessbench`` has a module docstring and a
   non-empty colocated ``index.md``.
2. Every test layer under ``tests`` has a non-empty ``index.md``.
3. Every top-level page in ``docs`` is linked from ``docs/index.md``.

Run from anywhere with ``python scripts/check_docs.py``. Exits non-zero when a
check fails.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "harnessbench"
DOCS_ROOT = ROOT / "docs"
TESTS_ROOT = ROOT / "tests"
MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_content(path: Path) -> bool:
    return path.is_file() and bool(_read(path).strip())


def _module_docstring(path: Path) -> str:
    tree = ast.parse(_read(path), filename=str(path))
    return ast.get_docstring(tree) or ""


def check_packages() -> list[str]:
    errors: list[str] = []
    for init in sorted(PACKAGE_ROOT.rglob("__init__.py")):
        package = init.parent
        relative = package.relative_to(ROOT)
        if not _module_docstring(init).strip():
            errors.append(f"{relative}/__init__.py: missing module docstring")
        if not _has_content(package / "index.md"):
            errors.append(f"{relative}: missing or empty index.md")
    return errors


def check_test_layers() -> list[str]:
    errors: list[str] = []
    for directory in sorted(path for path in TESTS_ROOT.iterdir() if path.is_dir()):
        if not _has_content(directory / "index.md"):
            errors.append(f"{directory.relative_to(ROOT)}: missing or empty index.md")
    return errors


def check_docs_index() -> list[str]:
    index = DOCS_ROOT / "index.md"
    if not _has_content(index):
        return ["docs/index.md: missing or empty"]

    targets = {
        target.split("#", 1)[0].strip()
        for target in MARKDOWN_LINK.findall(_read(index))
        if target.strip()
    }
    errors = [
        f"docs/{page.name}: not linked from docs/index.md"
        for page in sorted(DOCS_ROOT.glob("*.md"))
        if page.name != "index.md" and page.name not in targets
    ]
    return errors


def main() -> int:
    errors = check_packages() + check_test_layers() + check_docs_index()
    if errors:
        print("Documentation check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Documentation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
