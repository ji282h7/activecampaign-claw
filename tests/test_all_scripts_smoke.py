"""
Smoke tests parameterized over every script.

For every .py in scripts/ (excluding _ac_client and __init__), verifies:
  1. Module imports cleanly (no syntax errors, no top-level side effects)
  2. Module exposes a main() function
  3. `python3 <script> --help` exits 0 and prints usage

These are cheap structural tests — they don't validate business logic.
Deeper unit tests live in test_<script>.py files.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

# calibrate.py is the bootstrap and doesn't use argparse — skip the --help smoke
# (it has its own dedicated test suite at test_calibrate.py).
SKIP_HELP = {"calibrate.py"}

ALL_SCRIPTS = sorted(
    p.name for p in SCRIPTS_DIR.glob("*.py")
    if p.name not in ("__init__.py", "_ac_client.py")
)
HELP_SCRIPTS = [s for s in ALL_SCRIPTS if s not in SKIP_HELP]


@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_imports_clean(script):
    """Every script imports without raising."""
    path = SCRIPTS_DIR / script
    spec = importlib.util.spec_from_file_location(script.replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)
    # add scripts/ to path so _ac_client imports resolve
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec.loader.exec_module(mod)
    assert hasattr(mod, "main"), f"{script} must define main()"


@pytest.mark.parametrize("script", HELP_SCRIPTS)
def test_help_exits_clean(script):
    """`python3 <script> --help` exits 0."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), "--help"],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"{script} --help failed: {result.stderr.decode()[:500]}"
    )
    out = (result.stdout + result.stderr).decode().lower()
    assert "usage" in out, f"{script} --help missing usage text"


@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_module_docstring(script):
    """Every script has a module-level docstring."""
    path = SCRIPTS_DIR / script
    src = path.read_text()
    # very loose check — first triple-quote within the first 30 lines
    head = "\n".join(src.split("\n")[:30])
    assert '"""' in head or "'''" in head, f"{script} missing module docstring"


@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_uses_future_annotations_or_no_pep604(script):
    """Either declares `from __future__ import annotations` or doesn't use PEP 604.

    The skill's stated min Python is 3.9, so PEP 604 (`X | Y` types) requires
    the future-annotations import to evaluate lazily.
    """
    src = (SCRIPTS_DIR / script).read_text()
    has_future = "from __future__ import annotations" in src
    # cheap check for PEP 604 union in annotations: ` | None` is the common form
    uses_604 = " | None" in src or "| None" in src
    if uses_604:
        assert has_future, (
            f"{script} uses PEP 604 union syntax but missing "
            "`from __future__ import annotations`"
        )
