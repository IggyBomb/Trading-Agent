#!/usr/bin/env python3
"""
pre_screen.py — Pre-deep-dive screening for the long-term analyst.

STANDALONE: reads data/watchlist.txt, writes only its own output file.
It does not import or modify any other module of the pipeline.

Purpose
-------
The long-term analyst agent is expensive in tokens, so this script runs first
and reduces the whole watchlist to a short, ranked list of names worth a deep
dive. The criteria are the ones selected on the Finviz screener (all strict,
AND logic):

    Market cap            > $50M  (Micro and above)
    P/E (trailing)        > 0     (profitable)
    Forward P/E           0 < x < 30
    EPS growth past 3Y    > 15%   (annualised)
    EPS growth past 4Y    > 10%   (annualised; 3Y span if Yahoo has only 4 points)
    EPS growth next 5Y    > 10%   (annualised, analyst estimate)
    Sales growth TTM      >= 10%
    Net profit margin     > 10%
    Institutional own.    > 10%
    Average volume        > 100K  (3-month)
    IPO date              > 5 years ago

Because every filter is an AND, evaluation order does not change the result,
so the script runs a funnel from cheap to expensive data calls:

    Stage 1  Ticker.info               market cap, P/E, fwd P/E, margin,
                                       inst. ownership, volume, IPO date
    Stage 2  income statements         EPS growth 3Y / 5Y, sales growth TTM
    Stage 3  growth estimates          EPS growth next 5Y

Only survivors of a stage pay for the next one.

Ranking (survivors only)
------------------------
Percentile-rank composite, equal weight inside each block:
    Quality 40%   net profit margin
    Growth  30%   EPS growth 3Y, EPS growth next 5Y
    Value   30%   forward P/E (lower is better), forward PEG (lower is better)
Change the WEIGHT_* constants below if you want a different balance.

Data caveats (yfinance is an unofficial source)
-----------------------------------------------
* Strict mode: a missing value counts as a failed filter. Institutional
  ownership and 5Y estimates are often blank outside the US, so European
  names are the most likely to drop out for "missing" rather than "fail".
  The funnel report shows the split. --lenient-missing lets a missing value
  pass, flagged with "?" in the table, for you to verify by hand.
* EPS growth "past 4Y" is the annualised growth over the longest span available,
  up to 4 years, minimum 3 (see the eps_5y_yrs column). Yahoo currently serves
  only 4 annual EPS points = 3 years of growth, so today this filter is
  implied by the 3Y > 15% one, i.e. it is NOT an independent test. A 4-year
  span needs 5 annual points.
* EPS growth "next 5Y" depends on Yahoo's long-term growth estimate, which is
  often absent. Strict mode then drops every name; use --lenient-missing.
* Lenient mode still drops tickers with no Yahoo data at all.
* Sales growth last 12 months uses the true TTM-vs-prior-TTM when 8 quarters are
  available, otherwise the latest-quarter YoY (info.revenueGrowth), otherwise
  the last fiscal year. The source is shown in the sales_src column.
* Market cap is converted to USD with live current_exchange_rates (rough fallback rates if the
  current_exchange_rates call fails). The threshold is low, so this only matters for tiny caps.

Usage
-----
    python3 pre_screen.py                       # whole watchlist
    python3 pre_screen.py --limit 30            # quick smoke test
    python3 pre_screen.py --tickers AXP,AZN.L   # specific names
    python3 pre_screen.py --top 15              # keep the best 15 only
    python3 pre_screen.py --lenient-missing     # missing data passes, flagged
"""

from __future__ import annotations

import argparse
import logging
import math
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("long_term_analysis")

ROOT = Path("C:\\Users\\marti\\trading_agent\\long_term_analysis").resolve()
DEFAULT_WATCHLIST = ROOT  / "watchlist.txt"
DEFAULT_OUT = ROOT / "long_term_candidates.txt"

# ── Finviz criteria (from the screenshot) ────────────────────────────────────
MIN_MCAP_USD = 50e6
MAX_FWD_PE = 30.0
MIN_EPS_3Y = 0.15
MIN_EPS_5Y = 0.10
MIN_EPS_NEXT_5Y = 0.10
MAX_SALES_TTM = 0.10
MIN_NET_MARGIN = 0.10
MIN_INST_OWN = 0.10
MIN_AVG_VOL = 100_000
MIN_IPO_YEARS = 5.0

# ── Ranking weights ──────────────────────────────────────────────────────────
WEIGHT_QUALITY = 0.40
WEIGHT_GROWTH = 0.30
WEIGHT_VALUE = 0.30

# ── Fetch behaviour ──────────────────────────────────────────────────────────
DEFAULT_WORKERS = 2
REQUEST_PAUSE = 0.2          # seconds, jittered, between calls per worker
RETRIES = 1

# key -> (label, predicate on a non-missing number)
CHECKS = {
    "mcap":        ("Market cap > $50M",      lambda v: v > MIN_MCAP_USD),
    "pe":          ("P/E > 0",                lambda v: v > 0),
    "fwd_pe":      ("Forward P/E 0-30",       lambda v: 0 < v < MAX_FWD_PE),
    "net_margin":  ("Net margin > 10%",       lambda v: v > MIN_NET_MARGIN),
    "inst_own":    ("Inst. ownership > 10%",  lambda v: v > MIN_INST_OWN),
    "avg_vol":     ("Avg volume > 100K",      lambda v: v > MIN_AVG_VOL),
    "ipo_years":   ("IPO > 5 years ago",      lambda v: v > MIN_IPO_YEARS),
    "eps_3y":      ("EPS growth 3Y > 15%",    lambda v: v > MIN_EPS_3Y),
    "eps_5y":      ("EPS growth past 4Y > 10%",    lambda v: v > MIN_EPS_5Y),
    "sales_last_12_months":   ("Sales growth last 12 months >= 10%", lambda v: v >= MAX_SALES_TTM),
    "eps_next5y":  ("EPS growth next 5Y > 10%", lambda v: v > MIN_EPS_NEXT_5Y),
}

STAGE1_KEYS = ["mcap", "pe", "fwd_pe", "net_margin", "inst_own", "avg_vol", "ipo_years"]
STAGE2_KEYS = ["eps_3y", "eps_5y", "sales_last_12_months"]
STAGE3_KEYS = ["eps_next5y"]

#DA CAPIRE COME SI POSSONO AGGIORNARE MANUALMENTE O AUTOMATICAMENTE, MAGARI ATTACARE API DI TIPO FOREX
# Rough fallback C (USD per unit), used only if the live C call fails.
FIXED_EXCHANGE_RATES = {"EUR": 1.15, "GBP": 1.30, "CHF": 1.10, "SEK": 0.10,
               "DKK": 0.155, "NOK": 0.095, "CAD": 0.72, "JPY": 0.0068,
               "BRL": 0.18}


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

#converts a string into a float, if it is not possible to convert it returns None
def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v

#converts the list of tickers in watchlist.txt into a list of strings
def load_watchlist(path) -> list:
    """One ticker per line; blanks and '#' comments skipped; order kept, deduped."""
    seen, out = set(), []
    watchlist_path = Path(path)
    try:
        watchlist_path.resolve(strict=True)
    except FileNotFoundError:
        log.error(f"Watchlist file not found: {watchlist_path}")
        return []
    for line in watchlist_path.read_text(encoding="utf-8-sig").splitlines():
        ticker = line.split("#", 1)[0].strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            out.append(ticker)
    return out


def calculate_annual_growth(values, years):
    """Annualised growth over `years` from an oldest→newest list.
    None if there are too few points or the base/last value is not positive."""
    if values is None or len(values) < years + 1:
        return None
    a, b = values[-(years + 1)], values[-1]
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return (b / a) ** (1.0 / years) - 1.0


def eps_growth_5y(values):
    """Longest-span annualised growth up to 4 years; needs >= 3 years of span.
    Returns (growth or None, years used)."""
    if not values:
        return None, 0
    n = min(4, len(values) - 1)
    if n < 3:
        return None, n
    return calculate_annual_growth(values, n), n

#this function receives three possible data sources and uses the best one available, in order of quality
def sales_growth_last_12_months(quarterly_revenues, info_rev_growth, annual_revenues):
    """(growth, source). True 4 last quarters vs prior 4 quarters when 8 quarters exist, else the
    latest-quarter YoY from info, else the last fiscal year."""
    if quarterly_revenues and len(quarterly_revenues) >= 8:
        cur, prev = sum(quarterly_revenues[-4:]), sum(quarterly_revenues[-8:-4])
        if prev > 0:
            return cur / prev - 1.0, "TTM - last 4 quarters added together"
    g = num(info_rev_growth)
    if g is not None:
        return g, "Most_Recent_Quarter_YoY"
    if annual_revenues and len(annual_revenues) >= 2 and annual_revenues[-2] > 0:
        return annual_revenues[-1] / annual_revenues[-2] - 1.0, "Fiscal_Year"
    return None, None


def check(metrics, key) -> str:
    """'pass' | 'fail' | 'missing' for one filter."""
    v = metrics.get(key)
    if v is None:
        return "missing"
    return "pass" if CHECKS[key][1](v) else "fail"


def apply_checks(metrics, keys, lenient=False):
    """Evaluate `keys` in order. Returns (survives, reason).
    reason = 'fail:<key>' or 'missing:<key>' for the first elimination, else None.
    In lenient mode a missing value passes and is recorded in metrics['unverified'],
    except for tickers flagged no_data (Yahoo returned nothing usable): those never pass."""
    if metrics.get("no_data"):
        return False, "missing:mcap"
    for k in keys:
        r = check(metrics, k)
        if r == "fail":
            return False, f"fail:{k}"
        if r == "missing":
            if not lenient:
                return False, f"missing:{k}"
            metrics.setdefault("unverified", []).append(k)
    return True, None


def pct_ranks(values, higher_is_better=True):
    """Percentile score in [0,1] for each value (ties share the mid-rank)."""
    n = len(values)
    if n == 1:
        return [1.0]
    out = []
    for v in values:
        worse = sum(1 for w in values if (w < v if higher_is_better else w > v))
        equal = sum(1 for w in values if w == v) - 1
        out.append((worse + 0.5 * equal) / (n - 1))
    return out


def rank_survivors(rows):
    """rows: list of metric dicts that passed every filter. Adds 'score' and
    returns the list sorted best → worst. Missing components (lenient mode)
    count as neutral 0.5."""
    if not rows:
        return rows
    for r in rows:
        nx = r.get("eps_next5y")
        r["peg"] = (r["fwd_pe"] / (nx * 100.0)) if (r.get("fwd_pe") and nx and nx > 0) else None

    def comp(key, higher):
        vals = [r.get(key) for r in rows]
        present = [v for v in vals if v is not None]
        if not present:
            return [0.5] * len(rows)
        ranks = iter(pct_ranks(present, higher))
        return [next(ranks) if v is not None else 0.5 for v in vals]

    q = comp("net_margin", True)
    g1, g2 = comp("eps_3y", True), comp("eps_next5y", True)
    v1, v2 = comp("fwd_pe", False), comp("peg", False)
    for i, r in enumerate(rows):
        quality = q[i]
        growth = (g1[i] + g2[i]) / 2
        value = (v1[i] + v2[i]) / 2
        r["score"] = round(100 * (WEIGHT_QUALITY * quality + WEIGHT_GROWTH * growth
                                  + WEIGHT_VALUE * value), 1)
    return sorted(rows, key=lambda r: r["score"], reverse=True)


# ═════════════════════════════════════════════════════════════════════════════
# Data access (yfinance)
# ═════════════════════════════════════════════════════════════════════════════

_yf = None


def yf():
    global _yf
    if _yf is None:
        import yfinance
        _yf = yfinance
    return _yf

#this class caches the foreign exchange rate between USD and other currencies (like USD to EURO)
#If no exchange rate is found than the class will use a fallback value, exctracted from a dictionary list of fixed values (dont love this solution, I need to review it).
class CurrencyExchangeRate:
    """USD per unit of currency, cached; thread-safe."""

    def __init__(self):
        self._c, self._lock = {"USD": 1.0}, threading.Lock()

    def rate(self, cur):
        if not cur:
            return None
        cur = {"GBp": "GBP", "GBX": "GBP"}.get(cur, cur)   # LSE quotes pence; mcap is in GBP
        with self._lock:
            if cur in self._c:
                return self._c[cur]
        r = None
        try:
            r = num(yf().Ticker(f"{cur}USD=X").fast_info["last_price"])
        except Exception as e:
            log.warning(f"C: failed to fetch {cur}USD=X - error: {e} {type(e).__name__}")
            r = None
        if r is None:
            r = FIXED_EXCHANGE_RATES.get(cur)
        with self._lock:
            self._c[cur] = r
        return r


def _series(df, names):
    """Oldest→newest list of floats for the first matching row label."""
    if df is None or getattr(df, "empty", True):
        return []
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna().sort_index()
            return [float(x) for x in s.values]
    return []


def _growth_estimate_5y(ge):
    if ge is None or getattr(ge, "empty", True):
        return None
    col = "stock" if "stock" in ge.columns else ge.columns[0]
    for label in ge.index:
        if str(label).strip().lower() in ("ltg", "+5y", "5y", "next 5 years (per annum)"):
            v = num(ge.loc[label, col])
            if v is not None and abs(v) > 5:      # came as percent, not fraction
                v /= 100.0
            return v
    return None


def _pause():
    time.sleep(REQUEST_PAUSE * (0.5 + random.random()))


#da rivedere, cosa fa e come, bisogna snellire
def stage1_worker(sym, currency_exchange_rate, lenient):
    """.info → market cap, P/E, fwd P/E, margin, inst. ownership, volume, IPO age."""
    _pause()
    t = yf().Ticker(sym)
    info = t.info or {}
    m = {"ticker": sym, "name": info.get("shortName") or info.get("longName") or sym,
         "sector": info.get("sector")}

    mc, rate = num(info.get("marketCap")), currency_exchange_rate.rate(info.get("currency"))
    m["mcap"] = mc * rate if (mc is not None and rate is not None) else None
    m["pe"] = num(info.get("trailingPE"))
    m["fwd_pe"] = num(info.get("forwardPE"))
    m["net_margin"] = num(info.get("profitMargins"))
    m["inst_own"] = num(info.get("heldPercentInstitutions"))
    m["avg_vol"] = num(info.get("averageVolume"))
    m["info_rev_growth"] = num(info.get("revenueGrowth"))
    m["no_data"] = all(m[k] is None for k in ("mcap", "pe", "fwd_pe", "net_margin",
                                              "inst_own", "avg_vol"))

    ok, _ = apply_checks(dict(m), [k for k in STAGE1_KEYS if k != "ipo_years"], lenient)
    if not ok:
        return m                       # eliminated anyway — skip the IPO lookup

    first = num(info.get("firstTradeDateMilliseconds"))
    first_s = first / 1000.0 if first is not None else num(info.get("firstTradeDateEpochUtc"))
    if first_s is None:                # fallback: first bar of the price history
        try:
            h = t.history(period="max", interval="1mo", auto_adjust=False)
            if not h.empty:
                first_s = h.index[0].to_pydatetime().timestamp()
        except Exception as e:
            first_s = None
            log.warning(f"Failed to fetch history for {sym} - error: {e} {type(e).__name__}")
    if first_s is not None:
        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(first_s, timezone.utc)).days
        m["ipo_years"] = age / 365.25
    else:
        m["ipo_years"] = None
    return m


def stage2_worker(m, lenient):
    """Annual + quarterly income statements → EPS growth 3Y/5Y, sales growth TTM."""
    _pause()
    t = yf().Ticker(m["ticker"])
    eps = _series(t.income_stmt, ["Diluted EPS", "Basic EPS"])
    m["eps_3y"] = calculate_annual_growth(eps, 3)
    m["eps_5y"], m["eps_5y_yrs"] = eps_growth_5y(eps)
    quarterly_revenues = _series(t.quarterly_income_stmt, ["Total Revenue", "Operating Revenue"])
    annual_revenues = _series(t.income_stmt, ["Total Revenue", "Operating Revenue"])
    m["sales_ttm"], m["sales_src"] = sales_growth_last_12_months(quarterly_revenues, m.get("info_rev_growth"), annual_revenues)
    return m


def stage3_worker(m, lenient):
    """Analyst long-term growth estimate → EPS growth next 5Y."""
    _pause()
    t = yf().Ticker(m["ticker"])
    try:
        ge = t.growth_estimates
    except Exception as e:
        ge = None
        log.warning(f"Failed to fetch growth estimates for {m['ticker']} - error: {e} {type(e).__name__}")
    m["eps_next5y"] = _growth_estimate_5y(ge)
    return m


def _with_retry(fn, *args):
    last = None
    for attempt in range(RETRIES + 1):
        try:
            return fn(*args)
        except Exception as e:                     # network / parsing / rate limit
            last = e
            label = args[0] if isinstance(args[0], str) else args[0]["ticker"]   
            log.warning("%s attempt %s/%s failed: %s: %s",                       
                        label, attempt + 1, RETRIES + 1, type(e).__name__, e)
            time.sleep(1.0 + attempt)
    raise last

# It takes a list of tickers
# runs one stage's download and filtering on all of them, and returns who passed, who was dropped, and who crashed.
def run_stage(title, items, worker, keys, lenient, workers, args_for):
    """Runs `worker` over items in parallel, applies `keys`, returns
    (survivors, eliminated Counter, errors list)."""
    survivors, reasons, errors = [], Counter(), []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_with_retry, worker, *args_for(it)): it for it in items}
        for f in as_completed(futs):
            done += 1
            it = futs[f]
            label = it if isinstance(it, str) else it["ticker"]
            try:
                m = f.result()
            except Exception as e:
                errors.append((label, f"{type(e).__name__}: {e}"[:120]))
                log.error(f"{title}: {label} failed: {type(e).__name__}: {e}", exc_info=True)
                continue
            ok, reason = apply_checks(m, keys, lenient)
            if ok:
                survivors.append(m)
            else:
                reasons[reason] += 1
            if done % 50 == 0 or done == len(items):
                print(f"  {title}: {done}/{len(items)} processed, {len(survivors)} passing",
                      file=sys.stderr, flush=True)
    return survivors, reasons, errors


# ═════════════════════════════════════════════════════════════════════════════
# Output
# ═════════════════════════════════════════════════════════════════════════════

def _pct(v, unverified=False):
    return "  n/a" if v is None else f"{v * 100:5.1f}"


def print_table(rows):
    hdr = (f"{'#':>3}  {'Ticker':<9} {'Score':>5}  {'FwdPE':>5} {'PEG':>5} {'Marg%':>6} "
           f"{'EPS3Y%':>6} {'EPS4Y%':>6} {'Nxt5Y%':>6} {'Sales%':>6} {'Inst%':>5}  Name")
    print(hdr)
    print("-" * len(hdr))
    for i, r in enumerate(rows, 1):
        flag = "?" if r.get("unverified") else " "
        peg = f"{r['peg']:5.2f}" if r.get("peg") is not None else "  n/a"
        fpe = f"{r['fwd_pe']:5.1f}" if r.get("fwd_pe") is not None else "  n/a"
        print(f"{i:>3}{flag} {r['ticker']:<9} {r['score']:>5.1f}  {fpe} {peg} "
              f"{_pct(r.get('net_margin')):>6} {_pct(r.get('eps_3y')):>6} "
              f"{_pct(r.get('eps_5y')):>6} {_pct(r.get('eps_next5y')):>6} "
              f"{_pct(r.get('sales_ttm')):>6} {_pct(r.get('inst_own')):>5}  {str(r['name'])[:28]}")
    if any((r.get("eps_5y_yrs") or 4) < 4 for r in rows):
        print("EPS4Y% = growth over the longest span Yahoo provides (eps_5y_yrs, usually 3), "
              "not a true 4-year figure.")


def print_funnel(stages, errors):
    print("\nFunnel (each name is counted at the FIRST filter it fails):")
    for title, n_in, n_out, reasons in stages:
        print(f"  {title}: {n_in} -> {n_out}")
        for reason, cnt in reasons.most_common():
            kind, key = reason.split(":")
            print(f"      {cnt:>4}  {kind:<7} {CHECKS[key][0]}")
    if errors:
        print(f"\n  {len(errors)} ticker(s) dropped on fetch errors (rerun to retry): "
              + ", ".join(t for t, _ in errors[:15]) + (" ..." if len(errors) > 15 else ""))


def main(argv=None):
    log_dir = ROOT.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-18s | %(filename)s:%(funcName)-14s:%(lineno)-4d | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(log_dir / "pre_screen.log", mode="w", encoding="utf-8"),
        ],
    )
    ap = argparse.ArgumentParser(description="Pre-deep-dive screening for the long-term analyst")
    ap.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST))
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="ranked ticker list, one per line")
    ap.add_argument("--tickers", help="comma-separated tickers instead of the watchlist")
    ap.add_argument("--limit", type=int, help="only the first N tickers (smoke test)")
    ap.add_argument("--top", type=int, help="keep only the best N in the output file")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--lenient-missing", action="store_true",
                    help="a missing value passes the filter and is flagged '?'")
    a = ap.parse_args(argv)

    symbols = ([t.strip().upper() for t in a.tickers.split(",") if t.strip()]
               if a.tickers else load_watchlist(a.watchlist))
    if a.limit:
        symbols = symbols[:a.limit]
    if not symbols:
        sys.exit("No tickers to screen.")

    log.info("Pre-deep-dive screen — %d tickers, %s on missing data",
             len(symbols), "lenient" if a.lenient_missing else "strict")
    currency_exchange_rate = CurrencyExchangeRate()
    t0 = time.time()

    s1, r1, e1 = run_stage("Stage 1 (info)", symbols, stage1_worker, STAGE1_KEYS,
                           a.lenient_missing, a.workers, lambda s: (s, currency_exchange_rate, a.lenient_missing))
    s2, r2, e2 = run_stage("Stage 2 (statements)", s1, stage2_worker, STAGE2_KEYS,
                           a.lenient_missing, a.workers, lambda m: (m, a.lenient_missing))
    s3, r3, e3 = run_stage("Stage 3 (estimates)", s2, stage3_worker, STAGE3_KEYS,
                           a.lenient_missing, a.workers, lambda m: (m, a.lenient_missing))

    ranked = rank_survivors(s3)
    if a.top:
        ranked = ranked[:a.top]

    errors = e1 + e2 + e3
    if errors:                                     # so they can be rerun on their own
        failed_path = ROOT / "pre_screen_failed.txt"
        failed_path.write_text("".join(t + "\n" for t, _ in errors), encoding="utf-8")
    wrote = bool(ranked)
    if wrote:                                      # never overwrite the list with nothing
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text("".join(r["ticker"] + "\n" for r in ranked), encoding="utf-8")

    print(f"\n{len(ranked)} candidates for the long-term deep dive "
          f"({time.time() - t0:.0f}s) — ranked best first:\n")
    if ranked:
        print_table(ranked)
    print_funnel([("Stage 1  info-based filters", len(symbols), len(s1), r1),
                  ("Stage 2  EPS growth 3Y/5Y, sales TTM", len(s1), len(s2), r2),
                  ("Stage 3  EPS growth next 5Y", len(s2), len(s3), r3)],
                 e1 + e2 + e3)
    msg = (f"Ranked list written to {a.out}" if wrote else
           f"0 candidates: {a.out} was NOT overwritten (previous list, if any, is intact)")
    red = sys.stdout.isatty()                       # colour only in a real terminal
    print("\n" + (f"\033[1;31m{msg}\033[0m" if red else msg))
    if errors:
        print(f"{len(errors)} ticker(s) failed to download (rate limit?). Wait 30-60 min, then:\n"
              f"  python3 pre_screen.py --tickers $(paste -sd, {ROOT / 'pre_screen_failed.txt'}) "
              f"--workers 1 --out retry_candidates.txt")
    if a.lenient_missing:
        print("'?' = at least one filter could not be verified (missing data).")


if __name__ == "__main__":
    main()
