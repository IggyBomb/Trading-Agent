#!/usr/bin/env python3
"""
publish.py — the public research track.

Three commands:

    python3 publish.py data   GLE.PA          what the pipeline knows (raw facts)
    python3 publish.py check  drafts/gle.md   scan a draft for personalisation
    python3 publish.py render drafts/gle.md   assemble the finished publication

`render` refuses if a required disclosure is missing, if the rating is not one
of the published definitions, if the body addresses the reader, or if the
position disclosure cannot be established. Add --save to write the publication
into publications/ and append it to recommendation_history.jsonl.

Nothing here writes to the parent repo. Your personal system is untouched.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from compliance_guard import ComplianceError, OutputValidator, Publication, Severity
from disclosures import from_trades_jsonl, live_position_disclosure, normalise

RULE = "─" * 72


# ---------------------------------------------------------------------------
# Draft files: front matter + body
# ---------------------------------------------------------------------------

TEMPLATE = """\
---
instrument: Société Générale SA (GLE FP)
ticker: GLE.PA
isin: FR0000130809
rating: BUY
target: EUR 88
horizon: 12 months
price_at_production: EUR 74.20
previous: none
basis: 0.9x tangible book on 2027E TBVPS of EUR 98, cross-checked against 7.5x
  P/E on 2027E EPS. Assumptions: ROTE 11.5%, CET1 held at 13.0%, cost of equity 11.0%.
sources:
  - Q2 2026 results release, 30 July 2026
  - H1 2026 interim report, 30 July 2026
# State the position either way. It must name this ticker, so a line copied
# from another draft is caught rather than published.
position: The author holds no position in GLE.PA as at the date of production.
---

Write the analysis here.

Four sections work well: what the instrument is priced at and against what; the
case for the rating, sourced; what the discount or premium is pricing, honestly;
and the level or event at which the thesis fails.

About the instrument, never about the reader. Sizing, entries and execution
plans belong to whoever is reading — leave them out entirely.
"""

_LIST_KEYS = {"sources"}


def parse_draft(path: Path) -> Dict[str, Any]:
    """Minimal front-matter parser. No dependencies."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ComplianceError(
            f"{path} has no front matter. Run `python3 publish.py new {path}` "
            f"to create a draft with the required fields."
        )

    _, fm, body = text.split("---", 2)

    meta: Dict[str, Any] = {}
    key: Optional[str] = None
    for raw in fm.splitlines():
        if not raw.strip():
            continue
        if raw.lstrip().startswith("- ") and key in _LIST_KEYS:
            meta.setdefault(key, []).append(raw.lstrip()[2:].strip())
            continue
        if ":" in raw and not raw.startswith((" ", "\t")):
            key, _, value = raw.partition(":")
            key = key.strip()
            value = value.strip()
            meta[key] = [] if key in _LIST_KEYS and not value else value
        elif key and isinstance(meta.get(key), str):
            meta[key] = (meta[key] + " " + raw.strip()).strip()

    meta["body"] = body.strip()
    return meta


# ---------------------------------------------------------------------------
# Reading the pipeline's own output (read-only)
# ---------------------------------------------------------------------------

def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        print(f"  ! {path.name} is not valid JSON ({exc})", file=sys.stderr)
        return None


def _find_ticker(blob: Any, ticker: str) -> Optional[Dict[str, Any]]:
    """Pipeline files use both dict-keyed and list-of-dicts shapes."""
    if isinstance(blob, dict):
        for key in ("fundamentals", "signals", "data", "results"):
            if key in blob:
                return _find_ticker(blob[key], ticker)
        if ticker in blob and isinstance(blob[ticker], dict):
            return blob[ticker]
    if isinstance(blob, list):
        for row in blob:
            if isinstance(row, dict) and str(row.get("ticker", "")).upper() == ticker.upper():
                return row
    return None


def show_data(ticker: str) -> int:
    """Print the neutral facts the pipeline holds. Material for the writer."""
    print(f"\n{RULE}\n  {ticker} — what the pipeline knows\n{RULE}")

    sources = [
        ("fundamentals", config.FUNDAMENTAL_PATH),
        ("market",       config.MARKET_DATA_PATH),
    ]
    found = False
    for label, path in sources:
        rec = _find_ticker(_load(path), ticker)
        if not rec:
            print(f"\n  {label}: no entry for {ticker} in {path.name}")
            continue
        found = True
        print(f"\n  {label} ({path.name}):")
        for k, v in rec.items():
            if isinstance(v, (str, int, float)) or v is None:
                print(f"    {k:<22} {v}")

    sentiment = _load(config.SENTIMENT_PATH)
    if isinstance(sentiment, dict):
        print(f"\n  market context ({config.SENTIMENT_PATH.name}):")
        for k in ("generated_at", "composite_score", "composite_label", "composite_delta"):
            if k in sentiment:
                print(f"    {k:<22} {sentiment[k]}")

    if not found:
        print(f"\n  Nothing found for {ticker}. Run the pipeline first, or check "
              f"the ticker spelling against data/fundamental_data.json.")

    print(f"\n{RULE}")
    print("  These are facts, not a publication. Anything forward-looking you")
    print("  write from them is opinion and must read that way.")
    print(f"{RULE}\n")
    return 0


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_new(path: Path) -> int:
    if path.exists():
        print(f"  {path} already exists — not overwriting.")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE, encoding="utf-8")
    print(f"  Created {path}. Edit it, then: python3 publish.py check {path}")
    return 0


FRONT_MATTER_FIELDS = (
    ("instrument",          "nome e ticker come compaiono in pagina"),
    ("ticker",              "usato per il controllo sulla posizione"),
    ("isin",                "identificativo dello strumento"),
    ("rating",              "BUY / HOLD / SELL, nient'altro"),
    ("target",              "prezzo obiettivo"),
    ("horizon",             "orizzonte del rating"),
    ("price_at_production", "prezzo al momento della stesura"),
    ("previous",            "rating precedente e data, oppure 'none'"),
    ("basis",               "metodologia E assunzioni"),
    ("position",            "OBBLIGO MAR — detieni o non detieni"),
)


def _front_matter_report(meta: Dict[str, Any]) -> int:
    """Print the state of every required field. Returns the number missing."""
    print("\n  FRONT MATTER")
    missing = 0

    for field, why in FRONT_MATTER_FIELDS:
        value = str(meta.get(field, "")).strip()
        if not value:
            print(f"    [ ! ]  {field:<20} MANCANTE — {why}")
            missing += 1
            continue
        shown = value if len(value) <= 44 else value[:41] + "…"
        print(f"    [ ok]  {field:<20} {shown}")

    sources = meta.get("sources") or []
    if sources:
        print(f"    [ ok]  {'sources':<20} {len(sources)} citate")
    else:
        print(f"    [ ! ]  {'sources':<20} MANCANTI — nessuna cifra è attribuibile")
        missing += 1

    # the copied-draft trap
    position, ticker = str(meta.get("position", "")).strip(), str(meta.get("ticker", "")).strip()
    if position and ticker:
        key = normalise(ticker)
        if key and key not in re.sub(r"[^A-Z0-9]", "", position.upper()):
            print(f"\n    [ ! ]  la riga `position` non nomina {ticker} — sembra copiata "
                  f"da un'altra bozza")
            missing += 1

    return missing


def _reminder(meta: Dict[str, Any]) -> None:
    ticker = str(meta.get("ticker", "questo titolo")).strip() or "questo titolo"
    days = getattr(config, "BLACKOUT_DAYS", 5)
    print(f"\n{RULE}\n  PRIMA DI PUBBLICARE — da controllare a mano ogni volta\n{RULE}\n")
    print(f"    [ ]  La riga `position` dice quello che detieni DAVVERO oggi.")
    print(f"         Guarda il portafoglio adesso, non ricordare.")
    print(f"    [ ]  Non hai comprato o venduto {ticker} negli ultimi {days} giorni,")
    print(f"         e non prevedi di farlo nei prossimi {days}.")
    print(f"    [ ]  Ogni cifra nel testo è attribuibile a una delle fonti elencate.")
    print(f"    [ ]  Il rating rispetta le definizioni pubblicate, non il tuo istinto.")
    print(f"    [ ]  Hai riletto il testo tu. Il controllo automatico non legge le intenzioni.")
    print()


def cmd_check(path: Path) -> int:
    is_draft = path.suffix == ".md"
    meta = parse_draft(path) if is_draft else {"body": path.read_text(encoding="utf-8")}

    print(f"\n{RULE}\n  {path.name}\n{RULE}")

    missing = _front_matter_report(meta) if is_draft else 0

    report = OutputValidator().check(meta["body"])
    print("\n  TESTO")
    if not report.findings:
        print("    nessuna corrispondenza — che non vuol dire 'conforme':")
        print("    una regex non legge le intenzioni.")
    for f in report.blocking:
        print(f"\n    [BLOCK] {f.rule_id}  {f.message}")
        print(f"            …{f.excerpt}…")
    for f in report.warnings:
        print(f"\n    [warn ] {f.rule_id}  {f.message}")
        print(f"            …{f.excerpt}…")

    print(f"\n{RULE}")
    problems = missing + len(report.blocking)
    if problems:
        print(f"  {missing} campi mancanti, {len(report.blocking)} blocchi nel testo "
              f"→ render si rifiuterà")
    else:
        print(f"  Nessun blocco. {len(report.warnings)} avvisi da leggere.")
    print(RULE)

    if is_draft:
        _reminder(meta)

    return 1 if problems else 0


def _manual_position(meta: Dict[str, Any]) -> str:
    """
    The position disclosure as stated in the draft.

    Required. MAR Article 20 obliges you to disclose any financial interest in
    the instrument you are writing about, and there is no default that is safe
    to assume — silence and "no position" are not the same sentence.

    The line must name the ticker. That single check is what catches the real
    failure mode: a draft copied from another name, with the previous
    instrument's disclosure left in place.
    """
    position = str(meta.get("position", "")).strip()
    ticker = str(meta.get("ticker", "")).strip()

    if not position:
        raise ComplianceError(
            "The draft has no `position:` line.\n\n"
            "  Every publication must state whether you hold the instrument.\n"
            "  Add one of these to the front matter:\n\n"
            f"    position: The author holds no position in {ticker} as at the date of production.\n"
            f"    position: The author holds a long position in {ticker} as at the date of production.\n\n"
            "  (If you later reconcile logs/trades.jsonl against your broker, set\n"
            "  POSITIONS_COMPLETE in config.py and this line can be generated instead.)"
        )

    key = normalise(ticker)
    haystack = re.sub(r"[^A-Z0-9]", "", position.upper())
    if key and key not in haystack:
        raise ComplianceError(
            f"The `position:` line does not name {ticker}:\n\n"
            f"    {position}\n\n"
            "  This usually means the draft was copied from another instrument and\n"
            "  the previous disclosure was left behind. Publishing someone else's\n"
            "  position line is worse than publishing none."
        )
    return position


def _position_callable(ticker: str, display: str):
    def loader():
        return from_trades_jsonl(
            config.TRADES_PATH,
            reconciled_at=config.POSITIONS_RECONCILED_AT,
            complete=config.POSITIONS_COMPLETE,
        )
    return live_position_disclosure(
        ticker, loader,
        display=display,
        max_age_hours=config.POSITION_MAX_AGE_HOURS,
        aliases=config.POSITION_ALIASES,
    )


def _check_entity() -> Optional[str]:
    """
    Refuse to render while PRODUCER or AUTHOR still contains a [placeholder].

    A provisional entity line is the kind of thing that gets left in and
    published. Identifying the producer is the first MAR Article 20 obligation,
    so a half-filled one is not a cosmetic problem.
    """
    gaps = [name for name in ("PRODUCER", "AUTHOR")
            if "[" in str(getattr(config, name, "")) or "]" in str(getattr(config, name, ""))]
    if not gaps:
        return None
    lines = "\n  ".join(f"{n} = {getattr(config, n)!r}" for n in gaps)
    return (
        f"config.py still has a placeholder in {' and '.join(gaps)}:\n\n  {lines}\n\n"
        f"  Every publication must identify its producer. Fill this in before\n"
        f"  rendering — a provisional address printed on a subscriber's copy is\n"
        f"  worse than no publication."
    )


def cmd_render(path: Path, save: bool, strict: bool) -> int:
    gap = _check_entity()
    if gap:
        print(f"\n{RULE}\n  WITHHELD\n{RULE}\n\n  {gap}\n")
        return 1

    meta = parse_draft(path)
    required = ("instrument", "ticker", "isin", "rating", "target",
                "horizon", "price_at_production", "previous", "basis")
    missing = [k for k in required if not str(meta.get(k, "")).strip()]
    if missing:
        print(f"\n  Draft is missing front-matter fields: {', '.join(missing)}\n")
        return 1

    pub = Publication(
        producer=config.PRODUCER,
        author=config.AUTHOR,
        instrument=meta["instrument"],
        isin=meta["isin"],
        rating=meta["rating"],
        price_target=meta["target"],
        horizon=meta["horizon"],
        price_at_production=meta["price_at_production"],
        previous=meta["previous"],
        valuation_basis=meta["basis"],
        sources=meta.get("sources", []),
        position_disclosure=(
            _position_callable(meta["ticker"], meta["instrument"])
            if config.POSITIONS_COMPLETE else _manual_position(meta)
        ),
        issuer_relationship=config.ISSUER_RELATIONSHIP,
        body=meta["body"],
    )

    try:
        text = pub.render(allow_warnings=not strict)
    except ComplianceError as exc:
        print(f"\n{RULE}\n  WITHHELD\n{RULE}\n\n  {exc}\n")
        return 1

    print("\n" + text + "\n")

    if save:
        stamp = datetime.now(timezone.utc)
        config.PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        out = config.PUBLICATIONS_DIR / f"{stamp:%Y-%m-%d}-{meta['ticker'].replace('.', '_')}.md"
        out.write_text(text, encoding="utf-8")

        with config.HISTORY_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "disseminated": stamp.isoformat(),
                "instrument": meta["instrument"],
                "ticker": meta["ticker"],
                "isin": meta["isin"],
                "rating": meta["rating"].upper(),
                "previous": meta["previous"],
                "price_target": meta["target"],
                "horizon": meta["horizon"],
                "price_at_production": meta["price_at_production"],
                "publication": out.name,
            }) + "\n")

        print(f"  Saved  : {out}")
        print(f"  Logged : {config.HISTORY_PATH.name}  (your 12-month history)\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="publish.py",
        description="Public research track — separate from the personal trading system.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("data", help="show what the pipeline knows about a ticker")
    p.add_argument("ticker")

    p = sub.add_parser("new", help="create a draft with the required front matter")
    p.add_argument("path", type=Path)

    p = sub.add_parser("check", help="scan a draft for personalisation")
    p.add_argument("path", type=Path)

    p = sub.add_parser("render", help="assemble the finished publication")
    p.add_argument("path", type=Path)
    p.add_argument("--save", action="store_true", help="write to publications/ and log it")
    p.add_argument("--strict", action="store_true", help="treat warnings as blockers")

    args = ap.parse_args()

    try:
        if args.cmd == "data":
            return show_data(args.ticker)
        if args.cmd == "new":
            return cmd_new(args.path)
        if args.cmd == "check":
            return cmd_check(args.path)
        if args.cmd == "render":
            return cmd_render(args.path, args.save, args.strict)
    except ComplianceError as exc:
        print(f"\n  {exc}\n", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"\n  File not found: {exc}\n", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
