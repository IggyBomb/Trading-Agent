#!/usr/bin/env python3
"""
test_portfolio.py — running paper-tracking portfolio for /scan CONFIRMED
picks ("test" portfolio). Grows over time as new scans add tickers — this
is not a single day's snapshot, it accumulates.

Deliberately separate from trade_logger.py / logs/trades.jsonl: nothing
here is a real position, must never be read by disclosures.py or the
publishing track, and must never influence risk-manager sizing on the real
account.

Usage:
    python3 test_portfolio.py                  # show performance report (equal-weight %)
    python3 test_portfolio.py add TICKER ENTRY STOP TARGET SETUP F_SCORE RATING
        e.g. python3 test_portfolio.py add NVDA 185.0 177.0 197.0 breakout 62.1 Undervalued
        (uses today's date and tags the source as a manual add unless
        --source is passed) — for /scan CONFIRMED picks, which have a real
        technical stop/target.
    python3 test_portfolio.py add TICKER ENTRY STOP TARGET SETUP F_SCORE RATING --source "/scan 2026-09-10 CONFIRMED"
    python3 test_portfolio.py add-lt TICKER ENTRY DCF_BEAR DCF_BASE DCF_BULL RATING INVALIDATION
        e.g. python3 test_portfolio.py add-lt CATL 337.11 321.98 748.79 1597.97 QUALITY
             "ROIC drops below 13%, or a second YoY revenue decline"
        For long-term-analyst.md Deep-Dive picks — no stop-loss by design
        (per the framework: exit is thesis invalidation, not a price level).
        DCF Bear/Base/Bull replace Stop/Target as the tracked reference
        levels; INVALIDATION is the thesis-break condition, stored as text,
        not enforced automatically.
    python3 test_portfolio.py sim [--account 100000]
        Simulated €-sized portfolio: applies RISK.md's dynamic sizing tiers
        (same logic as trade_logger.py) to a notional account, converts
        USD/JPY positions to EUR, and reports position size, € P&L, and
        RISK.md violations (max 5 concurrent positions, oversize, no-stop
        — scan positions only; long-term positions never trigger NO_STOP,
        that's by design for this kind of entry, not an oversight).
        This is still paper — no real capital, same separation as above.
"""

import argparse
import json
import sys
from datetime import date

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

sys.path.insert(0, ".")
from trade_logger import dynamic_max_pct, load_sentiment_snapshot  # reuse RISK.md sizing logic — single source of truth

DATA_PATH = "./data/test_portfolio.json"

# Simple currency detection by ticker suffix — extend as the portfolio grows
# into other markets. Certificates/EU-suffixed tickers aren't handled here;
# this covers the US/JP names the scan currently produces.
def ticker_currency(ticker: str) -> str:
    if ticker.endswith(".T"):
        return "JPY"
    if any(ticker.endswith(s) for s in (".MI", ".PA", ".DE", ".AS", ".BR", ".MC", ".LS", ".VI", ".HE")):
        return "EUR"
    if any(ticker.endswith(s) for s in (".SZ", ".SS")):
        return "CNY"
    return "USD"


_fx_cache = {}
def fx_to_eur(currency: str) -> float:
    """EUR per 1 unit of `currency`'s quote (i.e. divide a price in that
    currency by this to get EUR). Cached per run."""
    if currency == "EUR":
        return 1.0
    if currency in _fx_cache:
        return _fx_cache[currency]
    pair = f"EUR{currency}=X"
    h = yf.Ticker(pair).history(period="5d")
    rate = float(h["Close"].iloc[-1])  # EURUSD=X style: units of `currency` per 1 EUR
    eur_per_unit = 1 / rate
    _fx_cache[currency] = eur_per_unit
    return eur_per_unit


def load_book():
    return json.load(open(DATA_PATH))


def save_book(book):
    with open(DATA_PATH, "w") as f:
        json.dump(book, f, indent=2)
        f.write("\n")


def fetch_price(ticker):
    h = yf.Ticker(ticker).history(period="5d")
    if h.empty:
        return None
    return float(h["Close"].iloc[-1])


def cmd_add(args):
    book = load_book()
    existing = {p["ticker"] for p in book["positions"]}
    if args.ticker.upper() in existing:
        print(f"  {args.ticker.upper()} is already in the test portfolio — not adding a duplicate.")
        print(f"  (edit {DATA_PATH} by hand if you mean to re-enter it.)")
        return 1

    entry = {
        "kind": "scan",
        "ticker": args.ticker.upper(),
        "entry_date": date.today().isoformat(),
        "entry_price": args.entry,
        "stop": args.stop,
        "target": args.target,
        "setup": args.setup,
        "f_score": args.f_score,
        "rating": args.rating,
        "source": args.source or f"manual add {date.today().isoformat()}",
    }
    book["positions"].append(entry)
    save_book(book)
    print(f"  Added {entry['ticker']} @ {entry['entry_price']} ({entry['source']})")
    return 0


def cmd_add_lt(args):
    book = load_book()
    existing = {p["ticker"] for p in book["positions"]}
    if args.ticker.upper() in existing:
        print(f"  {args.ticker.upper()} is already in the test portfolio — not adding a duplicate.")
        print(f"  (edit {DATA_PATH} by hand if you mean to re-enter it.)")
        return 1

    entry = {
        "kind": "long_term",
        "ticker": args.ticker.upper(),
        "entry_date": date.today().isoformat(),
        "entry_price": args.entry,
        "dcf_bear": args.dcf_bear,
        "dcf_base": args.dcf_base,
        "dcf_bull": args.dcf_bull,
        "rating": args.rating,
        "thesis_invalidation": args.invalidation,
        "source": args.source or f"long-term-analyst.md Deep-Dive {date.today().isoformat()}",
    }
    book["positions"].append(entry)
    save_book(book)
    print(f"  Added {entry['ticker']} @ {entry['entry_price']} (long-term, no stop by design — {entry['source']})")
    return 0


def cmd_show(args):
    book = load_book()
    positions = book["positions"]
    scan_positions = [p for p in positions if p.get("kind", "scan") == "scan"]
    lt_positions = [p for p in positions if p.get("kind") == "long_term"]

    print(f"\n{'='*96}")
    print(f"  TEST PORTFOLIO — {book.get('description', '')}")
    print(f"  Created {book['created']}, {len(positions)} position(s)")
    print(f"{'='*96}\n")

    all_returns = []

    if scan_positions:
        print(f"  -- /scan positions (technical stop/target) {'-'*(96-45)}")
        header = (f"  {'Ticker':<8}{'Entry date':<12}{'Entry':>10}{'Stop':>10}{'Target':>10}"
                  f"{'Price':>10}{'Return':>10}{'vs Stop':>10}{'vs Target':>10}")
        print(header)
        print(f"  {'-'*92}")

        for pos in scan_positions:
            t = pos["ticker"]
            entry = pos["entry_price"]
            stop = pos["stop"]
            target = pos["target"]
            price = fetch_price(t)
            if price is None:
                print(f"  {t:<8}{'NO DATA':>10}")
                continue
            ret = (price / entry - 1) * 100
            all_returns.append(ret)
            stop_dist = (price - stop) / price * 100
            target_dist = (target - price) / price * 100
            flag = ""
            if price <= stop:
                flag = "  ⚠ STOP HIT"
            elif price >= target:
                flag = "  ✓ TARGET HIT"
            print(f"  {t:<8}{pos['entry_date']:<12}{entry:>10.2f}{stop:>10.2f}{target:>10.2f}"
                  f"{price:>10.2f}{ret:>+9.2f}%{stop_dist:>+9.2f}%{target_dist:>+9.2f}%{flag}")
        print()

    if lt_positions:
        print(f"  -- long-term / Deep-Dive positions (no stop by design — thesis invalidation is the exit trigger) {'-'*0}")
        header = (f"  {'Ticker':<12}{'Entry date':<12}{'Entry':>11}{'Price':>11}{'Return':>10}"
                  f"{'vs Bear':>10}{'vs Base':>10}{'vs Bull':>10}")
        print(header)
        print(f"  {'-'*92}")

        for pos in lt_positions:
            t = pos["ticker"]
            entry = pos["entry_price"]
            bear, base, bull = pos["dcf_bear"], pos["dcf_base"], pos["dcf_bull"]
            price = fetch_price(t)
            if price is None:
                print(f"  {t:<12}{'NO DATA':>10}")
                continue
            ret = (price / entry - 1) * 100
            all_returns.append(ret)
            vs_bear = (price / bear - 1) * 100
            vs_base = (price / base - 1) * 100
            vs_bull = (price / bull - 1) * 100
            flag = ""
            if price <= bear:
                flag = "  ⚠ BELOW DCF BEAR — re-check thesis"
            elif price >= bull:
                flag = "  ✓ ABOVE DCF BULL"
            print(f"  {t:<12}{pos['entry_date']:<12}{entry:>11.2f}{price:>11.2f}{ret:>+9.2f}%"
                  f"{vs_bear:>+9.2f}%{vs_base:>+9.2f}%{vs_bull:>+9.2f}%{flag}")
            print(f"           rating: {pos['rating']:<20} invalidation: {pos['thesis_invalidation']}")
        print()

    if all_returns:
        avg = sum(all_returns) / len(all_returns)
        print(f"  Equal-weighted return across {len(all_returns)} position(s), all kinds: {avg:+.2f}%")

    print(f"\n{'='*96}\n")
    return 0


def cmd_sim(args):
    book = load_book()
    positions = book["positions"]
    account = args.account

    sd = load_sentiment_snapshot()
    max_pct, tier, reason = dynamic_max_pct(conviction="HIGH", sd=sd)  # every entry here came from a /scan CONFIRMED (High conviction) pick

    print(f"\n{'='*112}")
    print(f"  TEST PORTFOLIO — SIMULATED €{account:,.0f} ACCOUNT")
    print(f"  Sizing tier active: {tier} ({max_pct:.0f}% max/position) — {reason}")
    print(f"{'='*112}\n")

    header = (f"  {'Ticker':<12}{'Entry':>10}{'Ccy':>5}{'Shares':>8}{'Invested €':>13}"
              f"{'Price':>10}{'Value €':>12}{'P&L €':>12}{'P&L %':>9}{'% of ptf':>10}")
    print(header)
    print(f"  {'-'*108}")

    total_invested = 0.0
    total_value = 0.0
    violations = []
    n_positions = len(positions)

    if n_positions > 5:
        violations.append(f"MAX_POSITIONS: {n_positions} open positions — RISK.md caps concurrent positions at 5")

    for pos in positions:
        t = pos["ticker"]
        kind = pos.get("kind", "scan")
        ccy = ticker_currency(t)
        eur_rate = fx_to_eur(ccy)
        entry = pos["entry_price"]
        stop = pos.get("stop")  # absent for long_term entries — no stop by design

        target_value_eur = account * max_pct / 100
        entry_eur = entry * eur_rate
        shares = int(target_value_eur // entry_eur) if entry_eur > 0 else 0
        invested_eur = shares * entry_eur

        price = fetch_price(t)
        if price is None:
            print(f"  {t:<12}{'NO DATA':>10}")
            continue
        price_eur = price * eur_rate
        value_eur = shares * price_eur
        pnl_eur = value_eur - invested_eur
        pnl_pct = (price / entry - 1) * 100

        total_invested += invested_eur
        total_value += value_eur

        flag = ""
        if kind == "scan":
            if stop is not None and price <= stop:
                flag = "  ⚠ STOP HIT"
                violations.append(f"{t}: stop hit — should be closed in a real account")
        else:
            # long_term: no stop-loss by design (thesis invalidation is the exit trigger,
            # not a price level) — never flagged as NO_STOP, that's the intended shape.
            bear = pos.get("dcf_bear")
            if bear is not None and price <= bear:
                flag = "  ⚠ BELOW DCF BEAR — re-check thesis, not an automatic exit"
        if shares == 0:
            flag += "  ⚠ ZERO SHARES (position too small vs price)"
            violations.append(f"{t}: target size €{target_value_eur:,.0f} buys 0 whole shares at {ccy} price {entry} — position not really investable at this size")

        pct_of_ptf = invested_eur / account * 100
        print(f"  {t:<12}{entry:>10.2f}{ccy:>5}{shares:>8}{invested_eur:>12,.0f}€"
              f"{price:>10.2f}{value_eur:>11,.0f}€{pnl_eur:>+11,.0f}€{pnl_pct:>+8.2f}%{pct_of_ptf:>9.2f}%{flag}")

    cash_eur = account - total_invested
    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

    print(f"\n  {'-'*108}")
    print(f"  Investito: €{total_invested:,.0f}   Valore oggi: €{total_value:,.0f}   "
          f"P&L: €{total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)")
    print(f"  Cash residuo (non investito): €{cash_eur:,.0f}  "
          f"(atteso — RISK.md limita {max_pct:.0f}% a posizione, max 5 posizioni aperte: il resto resta cash by design)")

    if violations:
        print(f"\n  ⚠ RISK.md — {len(violations)} violazione/i:")
        for v in violations:
            print(f"    - {v}")

    print(f"\n{'='*112}\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("add", help="add a new ticker to the test portfolio")
    p.add_argument("ticker")
    p.add_argument("entry", type=float)
    p.add_argument("stop", type=float)
    p.add_argument("target", type=float)
    p.add_argument("setup")
    p.add_argument("f_score", type=float)
    p.add_argument("rating")
    p.add_argument("--source", default=None, help='e.g. "/scan 2026-09-14 CONFIRMED"')

    p = sub.add_parser("add-lt", help="add a long-term-analyst.md Deep-Dive pick (no stop/target by design)")
    p.add_argument("ticker")
    p.add_argument("entry", type=float, help="price at production of the Deep-Dive report")
    p.add_argument("dcf_bear", type=float)
    p.add_argument("dcf_base", type=float)
    p.add_argument("dcf_bull", type=float)
    p.add_argument("rating", help='e.g. COMPOUNDER / QUALITY / "QUALITY (vicino a COMPOUNDER)"')
    p.add_argument("invalidation", help="thesis-break condition, e.g. \"ROIC drops below 13%%\"")
    p.add_argument("--source", default=None, help='e.g. "Deep-Dive 2026-09-15"')

    p = sub.add_parser("sim", help="simulate a sized €-account portfolio using RISK.md tiers")
    p.add_argument("--account", type=float, default=100_000, help="notional account size in EUR (default 100,000)")

    args = ap.parse_args()
    if args.cmd == "add":
        return cmd_add(args)
    if args.cmd == "add-lt":
        return cmd_add_lt(args)
    if args.cmd == "sim":
        return cmd_sim(args)
    return cmd_show(args)


if __name__ == "__main__":
    raise SystemExit(main())
