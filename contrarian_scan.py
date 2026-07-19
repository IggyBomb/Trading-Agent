#!/usr/bin/env python3
"""
contrarian_scan.py — Contrarian opportunity scanner.

Scans for high-quality stocks under temporary pressure:
- Down 20%+ from 52-week high
- RSI ≤ 35 (oversold)
- Fundamentals intact (revenue not collapsing)
- Volume exhaustion signal preferred (selling pressure fading)
- Short squeeze potential flagged if short % > 5%

Output: data/contrarian_data.json
"""

import json
import time
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.txt"
MARKET_DATA_FILE = DATA_DIR / "market_data.json"
OUTPUT_FILE = DATA_DIR / "contrarian_data.json"

# ── Contrarian thresholds ──────────────────────────────────────────────────
PCT_FROM_HIGH_THRESHOLD = -20.0   # minimum % below 52wH to qualify
RSI_THRESHOLD = 35.0              # RSI must be at or below this
MIN_REVENUE_GROWTH = -0.20        # revenue declining worse than -20% = broken, skip
VOLUME_EXHAUSTION_RATIO = 0.80    # 5d avg vol < 80% of 20d avg = exhaustion
VOLUME_DISTRIBUTION_RATIO = 1.50  # 5d avg vol > 150% of 20d avg = distribution (red flag)
MAX_TICKERS = 200                 # cap to keep runtime under 5 minutes


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    return float(rsi_series.iloc[-1])


def get_open_positions() -> list[str]:
    """Pull open position tickers from trade_logger."""
    try:
        result = subprocess.run(
            ["python3", str(BASE_DIR / "trade_logger.py"), "open"],
            capture_output=True, text=True, timeout=10
        )
        tickers = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts and parts[0].isupper() and len(parts[0]) <= 8:
                tickers.append(parts[0])
        return tickers
    except Exception:
        return []


def get_candidate_pool() -> list[str]:
    """
    Build a candidate pool from:
    1. market_data.json downtrend tickers (trend='down' or change_pct < -3%)
    2. Open positions (always include — they're often natural contrarian candidates)
    3. Command-line override via --tickers
    """
    pool = set()

    # From market_data.json
    if MARKET_DATA_FILE.exists():
        with open(MARKET_DATA_FILE) as f:
            md = json.load(f)
        signals = md.get("signals", [])
        for s in signals:
            if not isinstance(s, dict):
                continue
            trend = s.get("trend", "")
            chg = s.get("change_pct", 0) or 0
            # Include: downtrend, or down >3% today, or sideways with recent weakness
            if trend == "down" or chg < -3.0 or (trend == "sideways" and chg < -1.0):
                t = s.get("ticker", "")
                if t:
                    pool.add(t)

    # Open positions always included
    for t in get_open_positions():
        pool.add(t)

    tickers = list(pool)[:MAX_TICKERS]
    return tickers


def classify_narrative(sector: str, revenue_growth: float | None,
                        short_pct: float, pct_from_high: float,
                        trend_before: str) -> str:
    """
    Classify the likely reason for the price weakness.
    Returns one of: MACRO_FEAR | SINGLE_EVENT | SECTOR_CONTAGION |
                    CROWDED_SHORT | PROXY_COLLAPSE | GROWTH_DECELERATION | UNKNOWN
    """
    if short_pct and short_pct > 0.15:
        return "CROWDED_SHORT"

    sector = (sector or "").lower()
    if revenue_growth is not None and revenue_growth < -0.05:
        return "GROWTH_DECELERATION"

    if any(s in sector for s in ["energy", "materials", "mining", "commodity"]):
        return "MACRO_FEAR"

    if any(s in sector for s in ["technology", "communication", "software"]):
        if pct_from_high < -30:
            return "SECTOR_CONTAGION"
        return "SINGLE_EVENT"

    if any(s in sector for s in ["healthcare", "pharmaceutical", "biotech"]):
        return "SINGLE_EVENT"  # usually regulatory or trial news

    if any(s in sector for s in ["financial", "bank", "insurance"]):
        return "MACRO_FEAR"

    return "UNKNOWN"


def score_candidate(
    rsi: float,
    pct_from_high: float,
    vol_trend: str,
    revenue_growth: float | None,
    short_pct: float,
    forward_pe: float | None,
    trailing_pe: float | None,
    has_insider_buy: bool,
) -> tuple[int, list[str]]:
    """
    Score a contrarian candidate 0–12. Returns (score, reasons).
    """
    score = 0
    reasons = []

    # Volume signal — most important distinguisher
    if vol_trend == "exhaustion":
        score += 3
        reasons.append("Volume exhaustion — sellers running out")
    elif vol_trend == "distribution":
        score -= 3
        reasons.append("⚠ Distribution volume — smart money still exiting")

    # Fundamental integrity
    if revenue_growth is not None:
        if revenue_growth > 0.20:
            score += 3
            reasons.append(f"Revenue still growing strongly (+{revenue_growth*100:.0f}%)")
        elif revenue_growth > 0.05:
            score += 2
            reasons.append(f"Revenue intact (+{revenue_growth*100:.0f}%)")
        elif revenue_growth > -0.05:
            score += 1
            reasons.append(f"Revenue roughly flat ({revenue_growth*100:+.0f}%)")
        elif revenue_growth < -0.15:
            score -= 2
            reasons.append(f"⚠ Revenue declining ({revenue_growth*100:.0f}%) — not a contrarian")

    # Valuation sanity (not broken at current price)
    if forward_pe and 0 < forward_pe < 20:
        score += 2
        reasons.append(f"Cheap on fwd earnings (fwdPE {forward_pe:.1f}x)")
    elif forward_pe and 0 < forward_pe < 35:
        score += 1
        reasons.append(f"Reasonable valuation (fwdPE {forward_pe:.1f}x)")

    # Short interest — squeeze potential
    if short_pct:
        if short_pct > 0.20:
            score += 3
            reasons.append(f"High short interest ({short_pct*100:.0f}%) — squeeze potential")
        elif short_pct > 0.10:
            score += 2
            reasons.append(f"Elevated short interest ({short_pct*100:.0f}%) — squeeze possible")
        elif short_pct > 0.05:
            score += 1
            reasons.append(f"Moderate short interest ({short_pct*100:.0f}%)")

    # Insider buying (via yfinance .insider_transactions)
    if has_insider_buy:
        score += 2
        reasons.append("Insider open-market buying detected")

    # RSI depth bonus
    if rsi < 20:
        score += 2
        reasons.append(f"RSI={rsi:.0f} — extreme oversold")
    elif rsi < 25:
        score += 1
        reasons.append(f"RSI={rsi:.0f} — deeply oversold")

    # Price depth bonus (more discounted = more margin of safety)
    if pct_from_high < -40:
        score += 1
        reasons.append(f"{pct_from_high:.0f}% from 52wH — deep discount")

    return score, reasons


def analyse_ticker(ticker: str) -> dict | None:
    """
    Download 1yr of data for ticker and compute all contrarian signals.
    Returns a dict if the ticker qualifies, None otherwise.
    """
    try:
        df = yf.download(ticker, period="1y", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 30:
            return None

        close = float(df["Close"].iloc[-1])
        high_52w = float(df["High"].max())
        low_52w = float(df["Low"].min())
        pct_from_high = (close / high_52w - 1) * 100

        # ── Filter 1: price weakness ───────────────────────────────────────
        if pct_from_high > PCT_FROM_HIGH_THRESHOLD:
            return None

        # ── RSI ────────────────────────────────────────────────────────────
        rsi = compute_rsi(df["Close"])

        # ── Filter 2: oversold ─────────────────────────────────────────────
        if rsi > RSI_THRESHOLD:
            return None

        # ── Volume trend ───────────────────────────────────────────────────
        avg_vol_20d = float(df["Volume"].rolling(20).mean().iloc[-1])
        avg_vol_5d = float(df["Volume"].rolling(5).mean().iloc[-1])
        if avg_vol_20d > 0:
            vol_ratio = avg_vol_5d / avg_vol_20d
        else:
            vol_ratio = 1.0

        if vol_ratio < VOLUME_EXHAUSTION_RATIO:
            vol_trend = "exhaustion"
        elif vol_ratio > VOLUME_DISTRIBUTION_RATIO:
            vol_trend = "distribution"
        else:
            vol_trend = "neutral"

        # ── Price changes ──────────────────────────────────────────────────
        chg_1d = (close / float(df["Close"].iloc[-2]) - 1) * 100 if len(df) >= 2 else 0.0
        chg_5d = (close / float(df["Close"].iloc[-6]) - 1) * 100 if len(df) >= 6 else 0.0
        chg_20d = (close / float(df["Close"].iloc[-21]) - 1) * 100 if len(df) >= 21 else 0.0

        # ── Fundamentals ───────────────────────────────────────────────────
        info = yf.Ticker(ticker).info
        revenue_growth = info.get("revenueGrowth")
        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        short_pct = info.get("shortPercentOfFloat") or 0.0
        sector = info.get("sector", "")
        market_cap = info.get("marketCap") or 0
        company_name = info.get("shortName") or ticker

        # ── Filter 3: fundamentals not broken ─────────────────────────────
        if revenue_growth is not None and revenue_growth < MIN_REVENUE_GROWTH:
            return None

        # ── Insider buying check ───────────────────────────────────────────
        has_insider_buy = False
        try:
            tk = yf.Ticker(ticker)
            txns = tk.insider_transactions
            if txns is not None and not txns.empty:
                recent = txns[txns.get("Transaction", pd.Series()) == "Buy"] if "Transaction" in txns.columns else pd.DataFrame()
                if not recent.empty:
                    has_insider_buy = True
        except Exception:
            pass

        # ── MA context ─────────────────────────────────────────────────────
        ma20 = float(df["Close"].rolling(20).mean().iloc[-1])
        ma50 = float(df["Close"].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None

        # ── ATR ────────────────────────────────────────────────────────────
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs()
        ], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        atr_pct = (atr / close) * 100

        # ── Scoring ────────────────────────────────────────────────────────
        score, reasons = score_candidate(
            rsi=rsi,
            pct_from_high=pct_from_high,
            vol_trend=vol_trend,
            revenue_growth=revenue_growth,
            short_pct=short_pct,
            forward_pe=forward_pe,
            trailing_pe=trailing_pe,
            has_insider_buy=has_insider_buy,
        )

        # ── Conviction mapping ─────────────────────────────────────────────
        if score >= 7:
            conviction = "HIGH"
        elif score >= 4:
            conviction = "MEDIUM"
        elif score >= 1:
            conviction = "LOW"
        else:
            conviction = "SKIP"   # net negative score = distribution trap, skip

        if conviction == "SKIP":
            return None

        # ── Narrative classification ───────────────────────────────────────
        narrative = classify_narrative(sector, revenue_growth, short_pct, pct_from_high, "")

        # ── Suggested thesis ───────────────────────────────────────────────
        thesis = build_thesis(ticker, conviction, narrative, revenue_growth,
                              short_pct, vol_trend, pct_from_high, rsi)

        return {
            "ticker": ticker,
            "name": company_name,
            "sector": sector,
            "price": round(close, 2),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "pct_from_52wh": round(pct_from_high, 1),
            "rsi": round(rsi, 1),
            "atr_pct": round(atr_pct, 1),
            "chg_1d": round(chg_1d, 1),
            "chg_5d": round(chg_5d, 1),
            "chg_20d": round(chg_20d, 1),
            "ma20": round(ma20, 2),
            "ma50": round(ma50, 2) if ma50 else None,
            "above_ma50": bool(close > ma50) if ma50 else None,
            "vol_trend": vol_trend,
            "vol_ratio_5d_20d": round(vol_ratio, 2),
            "avg_vol_20d": int(avg_vol_20d),
            "revenue_growth": round(revenue_growth, 3) if revenue_growth else None,
            "trailing_pe": round(trailing_pe, 1) if trailing_pe else None,
            "forward_pe": round(forward_pe, 1) if forward_pe else None,
            "short_pct_float": round(short_pct * 100, 1),
            "market_cap_b": round(market_cap / 1e9, 1) if market_cap else None,
            "has_insider_buy": has_insider_buy,
            "narrative": narrative,
            "score": score,
            "conviction": conviction,
            "reasons": reasons,
            "thesis": thesis,
        }

    except Exception as e:
        return None


def build_thesis(ticker: str, conviction: str, narrative: str,
                 rev_growth: float | None, short_pct: float,
                 vol_trend: str, pct_from_high: float, rsi: float) -> str:
    """Generate a one-line thesis for manual validation."""
    parts = []

    if narrative == "CROWDED_SHORT":
        parts.append(f"Heavily shorted ({short_pct*100:.0f}%); if thesis is wrong, violent squeeze possible")
    elif narrative == "MACRO_FEAR":
        parts.append("Macro/sector fear dragging down a fundamentally sound name — validate that the fear is temporary")
    elif narrative == "SECTOR_CONTAGION":
        parts.append("Caught in sector selloff; check if company-specific fundamentals still intact vs peers")
    elif narrative == "SINGLE_EVENT":
        parts.append("One-off event punished the stock; validate that the issue is non-recurring and not thesis-breaking")
    elif narrative == "GROWTH_DECELERATION":
        parts.append("Revenue slowing — verify whether deceleration is cyclical (recoverable) or structural (permanent)")
    else:
        parts.append("Price weakness not explained by fundamentals — validate by checking latest earnings and guidance")

    if vol_trend == "exhaustion":
        parts.append("selling exhaustion supports a floor")
    elif vol_trend == "distribution":
        parts.append("⚠ but distribution volume is a red flag — confirm smart money is done selling before entering")

    if rev_growth and rev_growth > 0:
        parts.append(f"revenue still growing ({rev_growth*100:+.0f}%) while price is {pct_from_high:.0f}% below peak")

    return "; ".join(parts) + "."


def print_results(results: list[dict]) -> None:
    high = [r for r in results if r["conviction"] == "HIGH"]
    medium = [r for r in results if r["conviction"] == "MEDIUM"]
    low = [r for r in results if r["conviction"] == "LOW"]

    width = 80
    print("=" * width)
    print(f"  CONTRARIAN SCAN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {len(results)} candidates  |  HIGH: {len(high)}  MEDIUM: {len(medium)}  LOW: {len(low)}")
    print("=" * width)

    if not results:
        print("  No contrarian setups found in current pool.")
        print("  (Criteria: down ≥20% from 52wH + RSI ≤35 + revenue not collapsing)")
        print("=" * width)
        return

    for group, label in [(high, "HIGH"), (medium, "MEDIUM"), (low, "LOW")]:
        if not group:
            continue
        print(f"\n  ── {label} CONVICTION ─────────────────────────────────────────")
        for r in group:
            print(f"\n  {r['ticker']:8s}  {r['name'][:30]:<30}  [{r['sector'][:20]}]")
            print(f"  Price: ${r['price']:.2f}  |  {r['pct_from_52wh']:+.1f}% from 52wH (${r['high_52w']:.2f})")
            print(f"  RSI: {r['rsi']:.0f}  |  ATR%: {r['atr_pct']:.1f}%  |  1d: {r['chg_1d']:+.1f}%  5d: {r['chg_5d']:+.1f}%  20d: {r['chg_20d']:+.1f}%")

            vol_icon = "📉" if r["vol_trend"] == "exhaustion" else ("⚠" if r["vol_trend"] == "distribution" else "→")
            print(f"  Volume: {vol_icon} {r['vol_trend'].upper()}  (5d/20d ratio: {r['vol_ratio_5d_20d']:.2f}x)")

            fund_parts = []
            if r["revenue_growth"] is not None:
                fund_parts.append(f"RevGrowth={r['revenue_growth']*100:+.0f}%")
            if r["trailing_pe"]:
                fund_parts.append(f"PE={r['trailing_pe']:.1f}x")
            if r["forward_pe"]:
                fund_parts.append(f"fwdPE={r['forward_pe']:.1f}x")
            if r["short_pct_float"] > 0:
                fund_parts.append(f"Short={r['short_pct_float']:.0f}%")
            if r["has_insider_buy"]:
                fund_parts.append("✓ Insider buy")
            print(f"  Fundamentals: {' | '.join(fund_parts) if fund_parts else '[NO DATA]'}")

            print(f"  Narrative: {r['narrative']}")
            print(f"  Signals:")
            for reason in r["reasons"]:
                print(f"    • {reason}")
            print(f"  Thesis: {r['thesis']}")
            print(f"  Score: {r['score']}/12  Conviction: {r['conviction']}")
            print()

    print("=" * width)
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  ⚠  This output is for manual decision-making only. No automated routing.")
    print("=" * width)


def main():
    parser = argparse.ArgumentParser(description="Contrarian opportunity scanner")
    parser.add_argument("--tickers", nargs="+", help="Override ticker list")
    parser.add_argument("--min-conviction", choices=["HIGH", "MEDIUM", "LOW"],
                        default="LOW", help="Minimum conviction level to display")
    args = parser.parse_args()

    if args.tickers:
        candidates = [t.upper() for t in args.tickers]
    else:
        candidates = get_candidate_pool()

    if not candidates:
        print("⚠  No candidate tickers found. Run fetch_data.py first or provide --tickers.")
        return

    print(f"\n  Scanning {len(candidates)} tickers for contrarian setups...")
    print(f"  Criteria: ≥20% below 52wH + RSI≤35 + revenue not collapsing\n")

    results = []
    for i, ticker in enumerate(candidates):
        print(f"  [{i+1:3d}/{len(candidates)}] {ticker:<12s}", end="\r", flush=True)
        result = analyse_ticker(ticker)
        if result:
            results.append(result)
        # Rate limit courtesy pause every 10 tickers
        if (i + 1) % 10 == 0:
            time.sleep(1)

    print(" " * 60, end="\r")  # clear progress line

    # Sort: HIGH first, then by score desc
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    results.sort(key=lambda x: (order[x["conviction"]], -x["score"]))

    # Apply conviction filter for display
    min_order = order[args.min_conviction]
    display = [r for r in results if order[r["conviction"]] <= min_order]

    print_results(display)

    # Save full results to JSON
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_scanned": len(candidates),
        "total_contrarian": len(results),
        "high_conviction": len([r for r in results if r["conviction"] == "HIGH"]),
        "medium_conviction": len([r for r in results if r["conviction"] == "MEDIUM"]),
        "low_conviction": len([r for r in results if r["conviction"] == "LOW"]),
        "candidates": results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
