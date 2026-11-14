import pandas as pd

from scan_shadow_breakout import parse_trigger, decide, run_trade


# ---------------------------------------------------------------- parser (real reasons)
def test_new_format_trigger():
    r = ("Fair, defensive leader ... under resistance $247.40; trigger: close >= 1% above $247.40 "
         "(>= $249.87 / EUR 226.4) on >= 1.5x volume, or two consecutive closes above")
    assert parse_trigger(r, "WM")[:3] == (247.40, "PRICE", "TEXT")


def test_ma200_with_number():
    r = "below MA200 $26.08 with R:R to MA200 0.62; trigger: close above MA200 $26.08 (EUR 23.6)"
    assert parse_trigger(r, "VICI")[:3] == (26.08, "MA200", "TEXT")


def test_ma_without_number_needs_prices():
    assert parse_trigger("enter on a close > MA200", "SGO.PA")[:3] == (None, "MA200", "NEEDS_MA")


def test_eur_conversion_of_usd_level_ignored():
    r = "close > MA50 (EUR 121.8) with Brent >= $95"
    assert parse_trigger(r, "COP")[:3] == (None, "MA50", "NEEDS_MA")


def test_other_tickers_trigger_skipped():
    r = "wait for SMH close >= MA20 $599.6 (EUR 537) and NVDA close > MA20 $227.5"
    assert parse_trigger(r, "NVDA")[:2] == (227.5, "MA20")
    assert parse_trigger("bubble invalidation pending - wait for SMH close >= MA20 $599.6", "AMAT")[1] is None


def test_bracketed_stale_trigger_skipped():
    r = ("Oct 30 trigger (close > $254.13) met on price but not on volume; "
         "buy a close above $258.82 on >= 1.2x vol")
    assert parse_trigger(r, "STLD")[0] == 258.82


def test_pence_and_eur_formats():
    assert parse_trigger("buy a close above 4,110p", "SHEL.L")[0] == 4110.0
    assert parse_trigger("buy a close > EUR82.35 on >=1.2x volume", "G24.DE")[0] == 82.35
    assert parse_trigger("buy a post-Q3 close > MA20 (~$233) on >=1.2x volume", "IEX")[0] == 233.0


def test_no_number_volume_not_taken():
    r = "trigger: reversal day at $166.70 support, then close >= 1% above that day's high on >= 1.5x volume"
    assert parse_trigger(r, "FSLR")[1] is None


# ---------------------------------------------------------------- breakout decision
def hist(closes, vols, start="2026-10-01"):
    idx = pd.bdate_range(start, periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"Open": c, "High": c * 1.005, "Low": c * 0.995, "Close": c,
                         "Volume": pd.Series(vols, index=idx, dtype=float)})


BASE = [98.0] * 25                 # 25 quiet sessions under the 100 level
VOL = [1_000_000] * 25


def scan_and_window(df, n_base=25):
    scan = df.index[n_base - 1].strftime("%Y-%m-%d")
    return scan, (df.index[n_base - 1] + pd.Timedelta(days=14)).strftime("%Y-%m-%d")


def test_strong_breakout_confirmed_day1():
    df = hist(BASE + [101.5, 102], VOL + [1_600_000, 1_000_000])
    scan, we = scan_and_window(df)
    f = decide(df, scan, 100.0, we, "SWING", 95.0)
    assert f["b_decision"] == "CONFIRMED_DAY1"
    assert f["a_entry"] == f["b_entry"] == 101.5


def test_marginal_breakout_bought_on_day2():
    df = hist(BASE + [100.4, 100.9], VOL + [1_100_000, 900_000])   # +0.4% on 1.1x
    scan, we = scan_and_window(df)
    f = decide(df, scan, 100.0, we, "SWING", 95.0)
    assert f["b_decision"] == "CONFIRMED_DAY2"
    assert (f["a_entry"], f["b_entry"]) == (100.4, 100.9)


def test_marginal_breakout_that_fails_is_rejected():
    df = hist(BASE + [100.4, 99.2] + [99.0] * 5, VOL + [1_100_000] * 7)
    scan, we = scan_and_window(df)
    f = decide(df, scan, 100.0, we, "SWING", 95.0)
    assert f["b_decision"] == "REJECTED_FAILED" and "b_entry" not in f
    assert f["failed_5d"] == 1


def test_waiting_for_day2_is_pending():
    df = hist(BASE + [100.4], VOL + [1_100_000])
    scan, we = scan_and_window(df)
    assert decide(df, scan, 100.0, we, "SWING", 95.0)["b_decision"] == "AWAITING_DAY2"


def test_below_ma200_needs_rr_to_ma200():
    # 200 sessions at 110 put MA200 near 110; breakout of 100 at 101.5 on volume.
    closes = [110.0] * 200 + [98.0] * 25 + [101.5]
    vols = [1_000_000] * 225 + [1_600_000]
    df = hist(closes, vols, start="2025-12-01")
    scan, we = scan_and_window(df, n_base=225)
    # MA200 at the breakout = (174*110 + 25*98 + 101.5) / 200 = 108.46
    # stop 96: R:R to MA200 = (108.46-101.5)/5.5 = 1.27 -> allowed
    assert decide(df, scan, 100.0, we, "SWING", 96.0)["b_decision"] == "CONFIRMED_DAY1"
    # stop 92: R:R = 6.96/9.5 = 0.73 -> rejected
    assert decide(df, scan, 100.0, we, "SWING", 92.0)["b_decision"] == "REJECTED_MA200"
    # TURNAROUND is exempt
    assert decide(df, scan, 100.0, we, "TURNAROUND", 92.0)["b_decision"] == "CONFIRMED_DAY1"


def test_no_cross_after_window():
    df = hist(BASE + [99.0] * 12, VOL + [1_000_000] * 12)
    scan, we = scan_and_window(df)
    assert decide(df, scan, 100.0, we, "SWING", 95.0)["status"] == "NO_CROSS"


def test_run_trade_invalid_when_fill_above_target():
    df = hist(BASE + [101.5], VOL + [1_600_000])
    assert run_trade(df, df.index[-1].strftime("%Y-%m-%d"), 101.5, 95, 101, "SWING")["outcome"] == "INVALID"
