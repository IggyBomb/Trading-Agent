"""
test_trades_jsonl.py — the Trading-Agent loader.

    python -m pytest test_trades_jsonl.py -q

The scenario these tests exist for: trades.jsonl is a journal, not a position
record. It holds what was remembered, which is not what is held. Every test
below is about refusing to confuse the two.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from compliance_guard import ComplianceError
from disclosures import from_trades_jsonl, position_line


def _now():
    return datetime.now(timezone.utc)


def write(tmp_path, records):
    path = tmp_path / "trades.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path


OPEN_GLE = {
    "id": "20260830-A1B2C3", "status": "open", "ticker": "GLE.PA",
    "direction": "LONG", "entry_date": "2026-08-30", "entry_price": 72.40,
    "qty": 100, "position_value": 7240.0, "position_pct_account": 8.2,
    "stop_price": 65.0, "target_price": 84.0, "rr_planned": 1.6,
    "conviction": "MEDIUM", "setup_type": "turnaround",
    "exit_date": None, "exit_price": None, "pnl_eur": None,
    "pnl_pct": None, "r_multiple": None, "notes": "", "rule_violations": [],
}

CLOSED_AMZN = {**OPEN_GLE, "id": "20260701-Z9Y8X7", "status": "closed",
               "ticker": "AMZN", "exit_date": "2026-08-01", "exit_price": 220.0}


# ---------------------------------------------------------------------------
# Reading the schema
# ---------------------------------------------------------------------------

def test_open_long_is_read(tmp_path):
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE]), complete=True)
    assert book.quantity("GLE.PA") == 100
    assert "holds a long position" in position_line("GLE.PA", book, max_age_hours=99999)


def test_short_is_signed_negative(tmp_path):
    rec = {**OPEN_GLE, "direction": "SHORT"}
    book = from_trades_jsonl(write(tmp_path, [rec]), complete=True)
    assert book.quantity("GLE.PA") == -100


def test_closed_trades_are_ignored(tmp_path):
    book = from_trades_jsonl(write(tmp_path, [CLOSED_AMZN]), complete=True)
    assert book.quantity("AMZN") == 0


def test_multiple_open_trades_in_one_name_are_summed(tmp_path):
    second = {**OPEN_GLE, "id": "20260901-B2C3D4", "qty": 50}
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE, second]), complete=True)
    assert book.quantity("GLE.PA") == 150


def test_long_and_short_net_off(tmp_path):
    hedge = {**OPEN_GLE, "id": "20260902-C3D4E5", "direction": "SHORT", "qty": 40}
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE, hedge]), complete=True)
    assert book.quantity("GLE.PA") == 60


def test_exchange_suffix_normalises(tmp_path):
    """Journal says GLE.PA; the publication says GLE."""
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE]), complete=True)
    assert book.quantity("GLE") == 100


def test_blank_lines_are_tolerated(tmp_path):
    path = tmp_path / "trades.jsonl"
    path.write_text(json.dumps(OPEN_GLE) + "\n\n\n")
    assert from_trades_jsonl(path, complete=True).quantity("GLE.PA") == 100


def test_empty_file_is_readable_but_holds_nothing(tmp_path):
    path = tmp_path / "trades.jsonl"
    path.write_text("")
    book = from_trades_jsonl(path, complete=True)
    assert book.positions == {}


# ---------------------------------------------------------------------------
# The refusals — the reason this file exists
# ---------------------------------------------------------------------------

def test_missing_file_raises_rather_than_reporting_flat(tmp_path):
    """The current state of the repo: logs/ has only .gitkeep."""
    with pytest.raises(ComplianceError) as exc:
        from_trades_jsonl(tmp_path / "trades.jsonl")
    msg = str(exc.value)
    assert "does not exist" in msg
    assert "never 'no positions held'" in msg


def test_unreconciled_journal_refuses_to_infer_flat(tmp_path):
    """complete=False by default: absence is not evidence of flat."""
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE]))
    assert book.complete is False
    with pytest.raises(ComplianceError) as exc:
        position_line("AMZN", book, max_age_hours=99999)
    assert "not marked complete" in str(exc.value)


def test_reconciled_and_complete_permits_flat(tmp_path):
    book = from_trades_jsonl(
        write(tmp_path, [OPEN_GLE]), reconciled_at=_now(), complete=True,
    )
    assert "holds no position in AMZN" in position_line("AMZN", book)


def test_malformed_line_raises(tmp_path):
    path = tmp_path / "trades.jsonl"
    path.write_text(json.dumps(OPEN_GLE) + "\n{ this is not json\n")
    with pytest.raises(ComplianceError) as exc:
        from_trades_jsonl(path, complete=True)
    assert "not valid JSON" in str(exc.value)


def test_open_trade_without_qty_raises(tmp_path):
    rec = {**OPEN_GLE, "qty": None}
    with pytest.raises(ComplianceError) as exc:
        from_trades_jsonl(write(tmp_path, [rec]), complete=True)
    assert "no qty" in str(exc.value)


def test_open_trade_without_ticker_raises(tmp_path):
    rec = {**OPEN_GLE, "ticker": ""}
    with pytest.raises(ComplianceError) as exc:
        from_trades_jsonl(write(tmp_path, [rec]), complete=True)
    assert "no ticker" in str(exc.value)


def test_bad_direction_raises(tmp_path):
    rec = {**OPEN_GLE, "direction": "FLAT"}
    with pytest.raises(ComplianceError) as exc:
        from_trades_jsonl(write(tmp_path, [rec]), complete=True)
    assert "expected LONG or SHORT" in str(exc.value)


def test_closed_trade_with_bad_data_is_not_validated(tmp_path):
    """Only open trades matter; a messy closed record must not block publishing."""
    junk = {**CLOSED_AMZN, "qty": None, "direction": "???"}
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE, junk]), complete=True)
    assert book.quantity("GLE.PA") == 100


# ---------------------------------------------------------------------------
# Freshness semantics
# ---------------------------------------------------------------------------

def test_unreconciled_source_is_labelled_as_such(tmp_path):
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE]))
    assert "never reconciled" in book.source


def test_reconciled_source_names_the_timestamp(tmp_path):
    book = from_trades_jsonl(write(tmp_path, [OPEN_GLE]), reconciled_at=_now())
    assert "reconciled" in book.source
    assert "never" not in book.source


def test_old_reconciliation_trips_the_staleness_check(tmp_path):
    stale = _now() - timedelta(days=10)
    book = from_trades_jsonl(
        write(tmp_path, [OPEN_GLE]), reconciled_at=stale, complete=True,
    )
    with pytest.raises(ComplianceError) as exc:
        position_line("GLE.PA", book, max_age_hours=24)
    assert "old" in str(exc.value)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
