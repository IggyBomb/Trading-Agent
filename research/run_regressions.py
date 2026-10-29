#!/usr/bin/env python3
"""
run_regressions.py — regress forward outcomes on the pipeline's scores,
using data/backtest/score_panel.csv from build_score_panel.py.

Usage (repo root):
  python3 research/run_regressions.py
  python3 research/run_regressions.py --y xret_60_w --x tech_score vol_score rsi
  python3 research/run_regressions.py --sample oos        # 2023+ only
  python3 research/run_regressions.py --region US

Needs: pip install statsmodels

Method notes
  - Date fixed effects (variables demeaned within each date): only the
    cross-sectional RANKING is tested, not whether the market went up.
  - Standard errors two-way clustered by date AND ticker: rows on the same
    date share shocks, and 20/60-day returns overlap across consecutive weekly
    rows of the same ticker. Plain OLS (or date-only clustering) gives
    t-stats that look significant on pure noise.
  - Fama-MacBeth as a robustness check: one cross-sectional regression per
    date, then t-stat of the average slope (Newey-West, lags = horizon/5).
"""
import argparse, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")   # rank-deficient single-date fits in FM are expected & skipped


def two_way(d):
    """Cluster by date AND ticker: date handles shared market shocks, ticker
    handles the overlap of 20/60-day returns across consecutive weekly rows."""
    return np.column_stack([pd.factorize(d["date"])[0], pd.factorize(d["ticker"])[0]])

ROOT  = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "backtest" / "score_panel.csv"


def load(path, sample, region):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["tradable"] == 1]
    if sample == "is":  df = df[df["insample"] == 1]
    if sample == "oos": df = df[df["insample"] == 0]
    if region:          df = df[df["region"] == region]
    return df


def design(df, x):
    """Numeric columns as-is; text columns (setup, trend, conviction, region)
    become dummies, first category dropped as the base."""
    num = [c for c in x if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in x if c not in num]
    X = df[num].astype(float)
    if cat:
        X = pd.concat([X, pd.get_dummies(df[cat], drop_first=True, dtype=float)], axis=1)
    return X


def ols_date_fe(df, y, x):
    d = df.dropna(subset=[y] + x)
    X = design(d, x)
    Y = d[y].astype(float)
    # within-date demeaning = date fixed effects
    g = d["date"]
    Xd = X - X.groupby(g).transform("mean")
    Yd = Y - Y.groupby(g).transform("mean")
    keep = Xd.std() > 0
    Xd = Xd.loc[:, keep]
    m = sm.OLS(Yd, Xd).fit(cov_type="cluster", cov_kwds={"groups": two_way(d)})
    return m, len(d), g.nunique()


def fama_macbeth(df, y, x, lags):
    d = df.dropna(subset=[y] + x)
    X = design(d, x)
    slopes = []
    for dt, idx in d.groupby("date").groups.items():
        Xi, Yi = X.loc[idx], d.loc[idx, y].astype(float)
        if len(Yi) < X.shape[1] + 10:
            continue
        Xi = Xi.loc[:, Xi.std() > 0]
        b = sm.OLS(Yi, sm.add_constant(Xi, has_constant="add")).fit().params
        slopes.append(b.rename(dt))
    B = pd.DataFrame(slopes)
    rows = []
    for c in B.columns:
        s = B[c].dropna()
        nw = sm.OLS(s.values, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        rows.append((c, s.mean(), nw.bse[0], s.mean() / nw.bse[0], len(s)))
    return pd.DataFrame(rows, columns=["var", "mean_slope", "nw_se", "t", "n_dates"]).set_index("var")


def rank_ic(df, y, score, lags):
    """Spearman correlation between score and outcome, per date, averaged;
    t-stat Newey-West because consecutive dates' ICs share overlapping returns."""
    d = df.dropna(subset=[y, score])
    ic = d.groupby("date").apply(lambda g: g[score].corr(g[y], method="spearman")
                                 if len(g) > 10 else np.nan, include_groups=False).dropna()
    nw = sm.OLS(ic.values, np.ones(len(ic))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return ic.mean(), ic.mean() / nw.bse[0], (ic > 0).mean(), len(ic)


def logit_target(df, x):
    d = df.dropna(subset=["target_hit"] + x)
    X = sm.add_constant(design(d, x))
    return sm.Logit(d["target_hit"].astype(float), X).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": two_way(d)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=str(PANEL))
    ap.add_argument("--y", default="xret_20_w", help="xret_5_w / xret_20_w / xret_60_w / trade_r ...")
    ap.add_argument("--x", nargs="+", default=["conviction", "tech_score", "vol_score"])
    ap.add_argument("--sample", choices=["all", "is", "oos"], default="all")
    ap.add_argument("--region", choices=["US", "EU", "JP", "CA", "BR"])
    a = ap.parse_args()

    df = load(a.panel, a.sample, a.region)
    horizon = int("".join(ch for ch in a.y if ch.isdigit()) or 20)
    print(f"\nPanel: {len(df):,} tradable rows, {df['ticker'].nunique()} tickers, "
          f"{df['date'].min().date()} -> {df['date'].max().date()}  [sample={a.sample}, region={a.region or 'all'}]")

    print(f"\n=== 1. Pooled OLS, date FE, SE two-way clustered (date, ticker):  {a.y} ~ {' + '.join(a.x)}")
    m, n, nd = ols_date_fe(df, a.y, a.x)
    print(m.summary2(title="").tables[1].round(5).to_string())
    print(f"N = {n:,}  dates = {nd}  within-R2 = {m.rsquared:.4f}")

    print(f"\n=== 2. Fama-MacBeth (Newey-West lags = {max(1, horizon // 5)})")
    print(fama_macbeth(df, a.y, a.x, max(1, horizon // 5)).round(5).to_string())

    print(f"\n=== 3. Rank IC vs {a.y}  (mean IC, t-stat, % dates IC>0, n dates)")
    for s in ["tech_score", "vol_score", "composite_px", "conv_num"]:
        mean, t, hit, k = rank_ic(df, a.y, s, max(1, horizon // 5))
        print(f"  {s:<14} IC={mean:+.4f}  t={t:+.2f}  pos={hit:.0%}  n={k}")
    print("  (an IC of +0.02 to +0.05, stable over time, is already a usable signal)")

    print(f"\n=== 4. Logit: P(target hit before {3.2}xATR stop)  [two-way clustered] ~ conviction + target_atr + setup")
    lg = logit_target(df, ["conviction", "target_atr", "setup"])
    print(lg.summary2(title="").tables[1].round(4).to_string())
    print("\nMeans by conviction:")
    print(df.groupby("conviction")[[a.y, "target_hit", "trade_r"]].mean().round(4).to_string())


if __name__ == "__main__":
    main()
