"""
test_disclosures.py

    python -m pytest test_disclosures.py -q

The governing assertion in this file: unknown never becomes "no position".
Every path that cannot establish the true holding must raise.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from compliance_guard import ComplianceError, Publication
from disclosures import (
    PositionBook,
    from_csv,
    from_json,
    from_mapping,
    live_position_disclosure,
    normalise,
    position_line,
)


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("AMZN", "AMZN"),
    ("  amzn ", "AMZN"),
    ("AMZN US Equity", "AMZN"),
    ("AMZN.O", "AMZN"),
    ("GLE FP Equity", "GLE"),
    ("BRK.B", "BRKB"),
])
def test_normalise(raw, expected):
    assert normalise(raw) == expected


# ---------------------------------------------------------------------------
# The line itself
# ---------------------------------------------------------------------------

def test_long_position():
    book = from_mapping({"AMZN": 10}, source="test")
    assert "holds a long position in AMZN" in position_line("AMZN", book)


def test_short_position():
    book = from_mapping({"GLE": -50}, source="test")
    assert "holds a short position in GLE" in position_line("GLE", book)


def test_flat_when_complete_book_omits_it():
    book = from_mapping({"AMZN": 10}, source="test", complete=True)
    assert "holds no position in GLE" in position_line("GLE", book)


def test_zero_quantity_reads_as_flat():
    book = from_mapping({"AMZN": 0}, source="test")
    assert "holds no position" in position_line("AMZN", book)


def test_vendor_decorated_symbol_still_matches():
    """The dangerous case: book says 'AMZN US Equity', publication says 'AMZN'."""
    book = from_mapping({"AMZN US Equity": 10}, source="test")
    assert "holds a long position" in position_line("AMZN", book)


def test_display_name_used_in_the_sentence():
    book = from_mapping({"AMZN": 10}, source="test")
    line = position_line("AMZN", book, display="Amazon.com Inc (AMZN)")
    assert "Amazon.com Inc (AMZN)" in line


def test_alias_maps_name_to_ticker():
    book = from_mapping({"AMZN": 10}, source="test")
    line = position_line("Amazon", book, aliases={"Amazon": "AMZN"})
    assert "holds a long position" in line


# ---------------------------------------------------------------------------
# Everything that must refuse rather than guess
# ---------------------------------------------------------------------------

def test_incomplete_book_refuses_to_infer_flat():
    book = from_mapping({"AMZN": 10}, source="watchlist", complete=False)
    with pytest.raises(ComplianceError) as exc:
        position_line("GLE", book)
    assert "not marked complete" in str(exc.value)


def test_stale_book_is_refused():
    old = _now() - timedelta(hours=72)
    book = from_mapping({"AMZN": 10}, as_of=old, source="dead feed")
    with pytest.raises(ComplianceError) as exc:
        position_line("AMZN", book, max_age_hours=24)
    assert "old" in str(exc.value)


def test_fresh_book_passes_the_age_check():
    recent = _now() - timedelta(hours=2)
    book = from_mapping({"AMZN": 10}, as_of=recent, source="broker")
    assert "long position" in position_line("AMZN", book, max_age_hours=24)


def test_ambiguous_symbol_with_conflicting_quantities_raises():
    book = PositionBook(
        positions={"AMZN": 10, "AMZN.O": 25},
        as_of=_now(), source="merged export",
    )
    with pytest.raises(ComplianceError) as exc:
        position_line("AMZN", book)
    assert "several entries" in str(exc.value)


def test_ambiguous_symbol_with_same_quantity_is_fine():
    book = PositionBook(
        positions={"AMZN": 10, "AMZN US Equity": 10},
        as_of=_now(), source="merged export",
    )
    assert "long position" in position_line("AMZN", book)


def test_missing_file_raises(tmp_path):
    with pytest.raises(ComplianceError) as exc:
        from_json(tmp_path / "nope.json")
    assert "does not exist" in str(exc.value)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def test_from_json_with_explicit_stamp(tmp_path):
    path = tmp_path / "positions.json"
    path.write_text(json.dumps({
        "as_of": _now().isoformat(),
        "positions": {"AMZN": 10, "GLE": -50},
    }))
    book = from_json(path)
    assert book.quantity("AMZN") == 10
    assert book.quantity("GLE") == -50


def test_from_json_list_shape(tmp_path):
    path = tmp_path / "positions.json"
    path.write_text(json.dumps([
        {"symbol": "AMZN", "quantity": 10},
        {"ticker": "GLE", "qty": -50},
    ]))
    book = from_json(path)
    assert book.quantity("AMZN") == 10
    assert book.quantity("GLE") == -50


def test_from_csv(tmp_path):
    path = tmp_path / "positions.csv"
    path.write_text("symbol,quantity\nAMZN,10\nGLE,-50\n")
    book = from_csv(path)
    assert book.quantity("AMZN") == 10
    assert "holds a short position" in position_line("GLE", book)


def test_from_csv_wrong_column_raises(tmp_path):
    path = tmp_path / "positions.csv"
    path.write_text("instrument,units\nAMZN,10\n")
    with pytest.raises(ComplianceError) as exc:
        from_csv(path)
    assert "no 'symbol' column" in str(exc.value)


def test_from_csv_non_numeric_quantity_raises(tmp_path):
    path = tmp_path / "positions.csv"
    path.write_text("symbol,quantity\nAMZN,ten\n")
    with pytest.raises(ComplianceError):
        from_csv(path)


# ---------------------------------------------------------------------------
# Wired into Publication — the point of the whole exercise
# ---------------------------------------------------------------------------

def _pub(position_disclosure):
    return Publication(
        producer="Example Research Ltd, Dublin",
        author="A. Analyst",
        instrument="Amazon.com Inc (AMZN)",
        isin="US0231351067",
        rating="BUY",
        price_target="USD 260",
        horizon="12 months",
        price_at_production="USD 214.00",
        previous="none",
        valuation_basis="18x 2027E EBITDA. Assumptions: AWS growth 19%, margin 37%.",
        sources=["Q2 2026 results, 31 July 2026"],
        position_disclosure=position_disclosure,
        body="The shares trade at 18x forward EBITDA. Below USD 180 the thesis breaks.",
    )


def test_callable_is_resolved_at_render_not_construction():
    """A position opened after drafting must still be disclosed."""
    book = {"AMZN": 0.0}
    pub = _pub(live_position_disclosure(
        "AMZN", lambda: from_mapping(book, source="live book")
    ))

    assert "holds no position" in pub.render()

    book["AMZN"] = 10.0                      # bought after the draft was written
    assert "holds a long position" in pub.render()


def test_plain_string_still_works():
    pub = _pub("The author holds no position in AMZN as at production.")
    assert "holds no position in AMZN" in pub.render()


def test_callable_failure_stops_the_publication(tmp_path):
    """A dead position source must block, never fall through to 'no position'."""
    pub = _pub(live_position_disclosure(
        "AMZN", lambda: from_json(tmp_path / "missing.json")
    ))
    with pytest.raises(ComplianceError) as exc:
        pub.render()
    assert "does not exist" in str(exc.value)
    assert "no position" not in str(exc.value)


def test_stale_source_stops_the_publication():
    old = _now() - timedelta(days=5)
    pub = _pub(live_position_disclosure(
        "AMZN", lambda: from_mapping({"AMZN": 10}, as_of=old, source="dead feed")
    ))
    with pytest.raises(ComplianceError):
        pub.render()


def test_callable_returning_blank_is_rejected():
    pub = _pub(lambda: "   ")
    with pytest.raises(ComplianceError) as exc:
        pub.render()
    assert "returned nothing" in str(exc.value)


def test_empty_string_still_blocks_render():
    with pytest.raises(ComplianceError) as exc:
        _pub("").render()
    assert "position_disclosure" in str(exc.value)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
