"""
disclosures.py — live position disclosure, resolved at publication time.

Why this exists
---------------
`position_disclosure` must state what the author held **as at the date of
production**. If the line is typed by hand when a draft is written, it is wrong
the moment anything trades — a piece drafted Monday and published Wednesday
discloses Monday's book. So the line is not a string you pass in. It is a
callable resolved when the publication renders, reading the live position store.

The safety principle throughout
-------------------------------
Unknown never becomes "no position". A missing file, a stale feed, an ambiguous
symbol or an incomplete book all raise. The only thing that produces a
"holds no position" line is a fresh, complete book that genuinely does not
contain the instrument.

A silent false "no position" is the worst output this module can produce, and it
is indistinguishable from the correct one unless the code refuses to guess.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Union

from compliance_guard import ComplianceError

__all__ = [
    "PositionBook",
    "normalise",
    "position_line",
    "live_position_disclosure",
    "from_mapping",
    "from_json",
    "from_csv",
    "from_sqlite",
    "from_trades_jsonl",
    "DEFAULT_MAX_AGE_HOURS",
]

DEFAULT_MAX_AGE_HOURS = 24


# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------

_EQUITY_SUFFIX = re.compile(r"\s+(?:[A-Z]{2}\s+)?EQUITY$", re.IGNORECASE)
_EXCHANGE_DOT = re.compile(r"\.(?:O|N|OQ|L|PA|DE|MI|AS|BR|MC|SW|TO|AX)$", re.IGNORECASE)


def normalise(symbol: str) -> str:
    """
    Reduce a symbol to a comparable key.

        "AMZN"              -> "AMZN"
        "AMZN US Equity"    -> "AMZN"
        "AMZN.O"            -> "AMZN"
        "  amzn  "          -> "AMZN"

    Deliberately conservative: it strips vendor decoration, not meaning. It will
    not map a company name to a ticker — pass an alias map for that.
    """
    s = symbol.strip().upper()
    s = _EQUITY_SUFFIX.sub("", s)
    s = _EXCHANGE_DOT.sub("", s)
    return re.sub(r"[^A-Z0-9]", "", s)


# ---------------------------------------------------------------------------
# The book
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionBook:
    """
    A point-in-time snapshot of what the author holds.

    positions : normalised symbol -> signed quantity (negative = short)
    as_of     : when the snapshot was taken, timezone-aware UTC
    source    : human-readable origin, quoted in error messages
    complete  : True if this book lists every position held. Only a complete
                book permits "holds no position" to be inferred from absence.
                A hand-maintained list or a partial export is NOT complete.
    """

    positions: Mapping[str, float]
    as_of: datetime
    source: str
    complete: bool = True

    def age(self, now: Optional[datetime] = None) -> timedelta:
        now = now or datetime.now(timezone.utc)
        as_of = self.as_of if self.as_of.tzinfo else self.as_of.replace(tzinfo=timezone.utc)
        return now - as_of

    def require_fresh(self, max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
                      now: Optional[datetime] = None) -> None:
        age = self.age(now)
        if age > timedelta(hours=max_age_hours):
            hours = age.total_seconds() / 3600
            raise ComplianceError(
                f"Position book from {self.source} is {hours:.1f}h old "
                f"(limit {max_age_hours}h). A feed that stopped updating looks "
                f"identical to a flat book. Refusing to publish a position "
                f"disclosure from stale data."
            )

    def quantity(self, symbol: str, aliases: Optional[Mapping[str, str]] = None) -> float:
        """
        Signed quantity held. Raises rather than guessing.
        """
        key = normalise(symbol)
        if aliases:
            for raw, target in aliases.items():
                if normalise(raw) == key:
                    key = normalise(target)
                    break

        matches = {k: v for k, v in self.positions.items() if normalise(k) == key}

        if len(matches) > 1:
            distinct = set(matches.values())
            if len(distinct) > 1:
                raise ComplianceError(
                    f"Symbol {symbol!r} matches several entries in {self.source} "
                    f"with different quantities ({matches}). Resolve the symbology "
                    f"before publishing — an ambiguous lookup must not silently "
                    f"pick one."
                )
            return float(next(iter(distinct)))

        if matches:
            return float(next(iter(matches.values())))

        if not self.complete:
            raise ComplianceError(
                f"{symbol!r} is absent from {self.source}, and that book is not "
                f"marked complete, so absence does not mean flat. Supply a "
                f"complete position export or state the position explicitly."
            )
        return 0.0


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def from_mapping(positions: Mapping[str, float], as_of: Optional[datetime] = None,
                 source: str = "in-memory mapping", complete: bool = True) -> PositionBook:
    return PositionBook(
        positions=dict(positions),
        as_of=as_of or datetime.now(timezone.utc),
        source=source,
        complete=complete,
    )


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def from_json(path: Union[str, Path], complete: bool = True) -> PositionBook:
    """
    Accepts either shape:

        {"as_of": "2026-08-29T07:00:00Z", "positions": {"AMZN": 10, "GLE": -50}}
        [{"symbol": "AMZN", "quantity": 10}, {"symbol": "GLE", "quantity": -50}]

    When `as_of` is absent, the file's modification time is used — so a feed that
    silently stopped writing will trip the staleness check rather than pass as a
    flat book.
    """
    path = Path(path)
    if not path.exists():
        raise ComplianceError(
            f"Position file {path} does not exist. Refusing to publish rather "
            f"than assert a position that may be wrong."
        )

    raw = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(raw, dict) and "positions" in raw:
        positions = {str(k): float(v) for k, v in raw["positions"].items()}
        stamp = raw.get("as_of")
        as_of = _parse_stamp(stamp) if stamp else _mtime(path)
    elif isinstance(raw, list):
        positions = {}
        for row in raw:
            sym = str(row.get("symbol") or row.get("ticker") or "").strip()
            if not sym:
                raise ComplianceError(f"Row without a symbol in {path}: {row!r}")
            positions[sym] = float(row.get("quantity", row.get("qty", 0)))
        as_of = _mtime(path)
    elif isinstance(raw, dict):
        positions = {str(k): float(v) for k, v in raw.items()}
        as_of = _mtime(path)
    else:
        raise ComplianceError(f"Unrecognised position file shape in {path}")

    return PositionBook(positions, as_of, str(path), complete)


def from_csv(path: Union[str, Path], symbol_col: str = "symbol",
             quantity_col: str = "quantity", complete: bool = True) -> PositionBook:
    """Broker exports. `as_of` comes from the file's modification time."""
    path = Path(path)
    if not path.exists():
        raise ComplianceError(
            f"Position file {path} does not exist. Refusing to publish rather "
            f"than assert a position that may be wrong."
        )

    positions: Dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or symbol_col not in reader.fieldnames:
            raise ComplianceError(
                f"{path} has no {symbol_col!r} column (found: {reader.fieldnames})"
            )
        for row in reader:
            sym = (row.get(symbol_col) or "").strip()
            if not sym:
                continue
            try:
                positions[sym] = float(row.get(quantity_col) or 0)
            except ValueError as exc:
                raise ComplianceError(
                    f"Non-numeric quantity for {sym!r} in {path}: {row.get(quantity_col)!r}"
                ) from exc

    return PositionBook(positions, _mtime(path), str(path), complete)


def from_trades_jsonl(path: Union[str, Path], *,
                      reconciled_at: Optional[datetime] = None,
                      complete: bool = False) -> PositionBook:
    """
    Load open positions from Trading-Agent's ``./logs/trades.jsonl``.

    One JSON object per line. Only records with ``status == "open"`` count.
    ``direction`` signs the quantity (LONG positive, SHORT negative) and
    multiple open trades in the same ticker are summed.

    Only three fields are read: ticker, direction, qty. The rest of the trade
    record — stop_price, target_price, rr_planned, conviction,
    position_pct_account — is your own position management and has no business
    anywhere near published text.

    Two arguments you have to think about
    -------------------------------------
    ``complete`` defaults to **False**, because a trade journal is not a
    position record. It contains what you remembered to log, which is not the
    same as what you hold. While it is False, a ticker absent from the file
    raises instead of producing "holds no position" — the correct behaviour
    when the journal has not been reconciled against the broker.

    Set it True only once every position you actually hold is logged here.

    ``reconciled_at`` is when the journal was last checked against the broker.
    Without it, freshness falls back to the file's modification time, which for
    a journal means "when you last logged a trade" — not "when this was last
    known accurate". A quiet fortnight would then read as stale, and a journal
    that silently drifted from the broker would read as fresh. Pass the real
    reconciliation timestamp and the staleness check becomes meaningful.
    """
    path = Path(path).expanduser()
    if not path.exists():
        raise ComplianceError(
            f"{path} does not exist. In Trading-Agent this file is created on "
            f"the first trade_logger.py entry, so 'missing' means 'nothing has "
            f"been logged' — never 'no positions held'. Refusing to build a "
            f"position disclosure from it."
        )

    positions: Dict[str, float] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ComplianceError(
                f"{path}:{lineno} is not valid JSON ({exc}). An unparseable "
                f"line may be hiding a position, so the whole book is unusable "
                f"until it is fixed."
            ) from exc

        if str(rec.get("status", "")).strip().lower() != "open":
            continue

        trade_id = rec.get("id", f"line {lineno}")

        ticker = str(rec.get("ticker") or "").strip()
        if not ticker:
            raise ComplianceError(f"{path}:{lineno} open trade {trade_id!r} has no ticker.")

        direction = str(rec.get("direction") or "").strip().upper()
        if direction not in ("LONG", "SHORT"):
            raise ComplianceError(
                f"{path}:{lineno} open trade {trade_id!r} has direction "
                f"{direction!r}; expected LONG or SHORT."
            )

        qty_raw = rec.get("qty")
        if qty_raw is None:
            raise ComplianceError(
                f"{path}:{lineno} open trade {trade_id!r} has no qty. An open "
                f"trade of unknown size cannot be disclosed."
            )
        try:
            qty = float(qty_raw)
        except (TypeError, ValueError) as exc:
            raise ComplianceError(
                f"{path}:{lineno} open trade {trade_id!r} has non-numeric qty "
                f"{qty_raw!r}."
            ) from exc

        positions[ticker] = positions.get(ticker, 0.0) + (qty if direction == "LONG" else -qty)

    if reconciled_at is None:
        as_of = _mtime(path)
        source = f"{path} (open trades; mtime — never reconciled to broker)"
    else:
        as_of = reconciled_at if reconciled_at.tzinfo else reconciled_at.replace(tzinfo=timezone.utc)
        source = f"{path} (open trades; reconciled {as_of:%Y-%m-%d %H:%M UTC})"

    return PositionBook(positions, as_of, source, complete)


def from_sqlite(path: Union[str, Path],
                query: str = "SELECT symbol, quantity FROM positions",
                complete: bool = True) -> PositionBook:
    """Query must return two columns: symbol, signed quantity."""
    path = Path(path)
    if not path.exists():
        raise ComplianceError(f"Position database {path} does not exist.")

    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = con.execute(query).fetchall()
    finally:
        con.close()

    positions = {str(sym): float(qty) for sym, qty in rows}
    return PositionBook(positions, _mtime(path), str(path), complete)


def _parse_stamp(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ComplianceError(f"Unparseable as_of timestamp: {value!r}") from exc
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# The disclosure line
# ---------------------------------------------------------------------------

def position_line(symbol: str, book: PositionBook, *,
                  display: Optional[str] = None,
                  max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
                  aliases: Optional[Mapping[str, str]] = None,
                  now: Optional[datetime] = None) -> str:
    """
    Build the disclosure sentence from a live book.

        >>> book = from_mapping({"AMZN": 10}, source="broker export")
        >>> position_line("AMZN", book)
        'The author holds a long position in AMZN as at the date of production.'
    """
    book.require_fresh(max_age_hours, now=now)
    qty = book.quantity(symbol, aliases=aliases)
    name = display or symbol

    if qty > 0:
        return f"The author holds a long position in {name} as at the date of production."
    if qty < 0:
        return f"The author holds a short position in {name} as at the date of production."
    return f"The author holds no position in {name} as at the date of production."


def live_position_disclosure(symbol: str, loader: Callable[[], PositionBook], *,
                             display: Optional[str] = None,
                             max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
                             aliases: Optional[Mapping[str, str]] = None) -> Callable[[], str]:
    """
    Returns a callable for `Publication(position_disclosure=...)`.

    The loader runs when the publication renders, not when it is constructed, so
    a position opened after the draft was written is still disclosed correctly.

        pub = Publication(
            ...,
            position_disclosure=live_position_disclosure(
                "AMZN", lambda: from_csv("~/Trading-Agent/data/positions.csv")
            ),
        )
    """
    def resolve() -> str:
        return position_line(
            symbol, loader(), display=display,
            max_age_hours=max_age_hours, aliases=aliases,
        )
    return resolve
