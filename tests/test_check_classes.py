"""Unit tests for check-classes.py: the dead-class checker.

Covers the pure functions directly (escape, is_resolved) and the CLI
behaviour end-to-end via subprocess against small fixture directories, so
a change to the script's exit-code contract or file-argument handling
gets caught the same way a change to its logic would.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from htmlkit import ROOT
from pyscripts import load

check_classes = load("check-classes.py")
SCRIPT = f"{ROOT}/check-classes.py"


# ---------------------------------------------------------------------------
# escape()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cls,expected",
    [
        ("p-8", "p-8"),  # nothing to escape
        ("md:p-8", r"md\:p-8"),  # responsive variant colon
        ("hover:shadow-md", r"hover\:shadow-md"),  # pseudo-class colon
        ("w-1/2", r"w-1\/2"),  # fraction slash
        ("bg-[#fff]", r"bg-\[\#fff\]"),  # arbitrary-value brackets and hash
        ("scale-(--x)", r"scale-\(--x\)"),  # parens
        ("opacity-50%", r"opacity-50\%"),  # percent
        ("sm:grid-cols-3,md:flex", r"sm\:grid-cols-3\,md\:flex"),  # comma
        ("first!", r"first\!"),  # important marker
    ],
)
def test_escape_matches_tailwind_convention(cls, expected):
    assert check_classes.escape(cls) == expected


# ---------------------------------------------------------------------------
# is_resolved()
# ---------------------------------------------------------------------------

def test_is_resolved_true_for_an_exact_rule():
    assert check_classes.is_resolved("p-8", ".p-8 { padding: 2rem; }")


def test_is_resolved_false_when_css_has_no_matching_rule():
    assert not check_classes.is_resolved("p-8", ".p-6 { padding: 1.5rem; }")


def test_is_resolved_false_on_empty_css():
    assert not check_classes.is_resolved("p-8", "")


def test_is_resolved_does_not_false_positive_on_a_longer_selector():
    # Regression test: ".p-8" is a literal substring of ".p-80", so a naive
    # `needle in css` check calls "p-8" resolved even though no ".p-8" rule
    # exists — this was a real bug that hid two live dead classes (see the
    # commit that added this test).
    assert not check_classes.is_resolved("p-8", ".p-80 { padding: 20rem; }")


def test_is_resolved_still_matches_before_a_pseudo_class():
    # ".hover\:shadow-md:hover" — the class's own selector is immediately
    # followed by an unescaped pseudo-class, not by more of the class name.
    css = r".hover\:shadow-md:hover { box-shadow: 0 0 0; }"
    assert check_classes.is_resolved("hover:shadow-md", css)


def test_is_resolved_matches_in_a_compound_selector():
    assert check_classes.is_resolved("foo", ".foo.bar { color: red; }")


def test_is_resolved_matches_inside_a_media_query():
    css = "@media (min-width: 768px) { .md\\:p-8 { padding: 2rem; } }"
    assert check_classes.is_resolved("md:p-8", css)


# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------

def _run(cwd, *args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_cli_exits_zero_when_everything_resolves(tmp_path):
    (tmp_path / "style.css").write_text(".ok { color: red; }")
    (tmp_path / "index.html").write_text('<p class="ok">hi</p>')
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "All classes resolve" in result.stdout


def test_cli_exits_one_and_names_only_the_missing_class(tmp_path):
    (tmp_path / "style.css").write_text(".ok { color: red; }")
    (tmp_path / "index.html").write_text('<p class="ok broken">hi</p>')
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "index.html: 1 unresolved -> broken" in result.stdout


def test_cli_skips_tpi_prefixed_classes(tmp_path):
    (tmp_path / "style.css").write_text("")
    (tmp_path / "index.html").write_text('<p class="tpi-hero">hi</p>')
    result = _run(tmp_path)
    assert result.returncode == 0


def test_cli_skips_ignored_marker_classes(tmp_path):
    (tmp_path / "style.css").write_text("")
    (tmp_path / "index.html").write_text('<p class="not-prose group lead">hi</p>')
    result = _run(tmp_path)
    assert result.returncode == 0


def test_cli_with_explicit_file_argument_checks_only_that_file(tmp_path):
    (tmp_path / "style.css").write_text(".ok { color: red; }")
    (tmp_path / "good.html").write_text('<p class="ok">hi</p>')
    (tmp_path / "bad.html").write_text('<p class="broken">hi</p>')

    result = _run(tmp_path, "good.html")
    assert result.returncode == 0

    result = _run(tmp_path, "bad.html")
    assert result.returncode == 1
    assert "bad.html" in result.stdout
