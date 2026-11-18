"""Checks on the source code itself, for rules that the Linux CI cannot catch by running it."""

from sbb_delays.paths import ROOT


def test_src_uses_replace_not_rename():
    # Path.rename does not overwrite on Windows (WinError 183) but does on Linux, so a test that
    # overwrites a file stays green in the CI. This text check fails on every system (issue #51).
    hits = [
        f"{path.relative_to(ROOT)}:{number}"
        for path in sorted((ROOT / "src").rglob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if ".rename(" in line
    ]
    assert hits == [], f"use Path.replace instead of Path.rename: {hits}"
