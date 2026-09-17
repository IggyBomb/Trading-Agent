"""
test_publish_parser.py — regression test for `parse_draft`'s front-matter
parser in publish.py.

Covers a real bug found while drafting: a "- " list item (sources, positions)
that wraps onto a second, indented line had its continuation silently
dropped — the draft would check and render clean, but ship a truncated
citation with no error anywhere. That is exactly the failure mode this
publishing track exists to prevent, so it gets a named regression test.
"""

import pytest

from publish import parse_draft

FRONT_MATTER = """\
---
instrument: Example SA (EXA FP)
ticker: EXA.PA
isin: FR0000000000
rating: HOLD
target: EUR 50
horizon: 12 months
price_at_production: EUR 45
previous: none
basis: single-line basis, no wrapping.
sources:
  - Short source, one line.
  - A much longer source citation that wraps onto a second,
    indented line because it would not fit in one.
position: The author holds no position in EXA.PA as at the date of
  production.
---

Body text here.
"""


def test_short_list_items_parse_unchanged(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text(FRONT_MATTER, encoding="utf-8")
    meta = parse_draft(p)
    assert meta["sources"][0] == "Short source, one line."


def test_wrapped_source_citation_is_not_truncated(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text(FRONT_MATTER, encoding="utf-8")
    meta = parse_draft(p)
    assert meta["sources"][1] == (
        "A much longer source citation that wraps onto a second, "
        "indented line because it would not fit in one."
    )
    assert len(meta["sources"]) == 2          # the wrap must not become a 3rd item


def test_wrapped_position_line_is_not_truncated(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text(FRONT_MATTER, encoding="utf-8")
    meta = parse_draft(p)
    assert meta["position"] == (
        "The author holds no position in EXA.PA as at the date of production."
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
