"""Earnings rule (2026-10-30): no ranking penalty; sessions-to-earnings helper
drives the swing/momentum halve + no-entry signals."""
from datetime import date, timedelta
import numpy as np
import watchlist_ranker as wr
from config import EARNINGS_EXIT_SESSIONS, EARNINGS_TRIM_STRATEGIES


def _cal(ticker, d):
    return [{"ticker": ticker, "earnings_date": d.isoformat()}]


def test_no_pre_earnings_penalty():
    base = wr.composite(70, 60, 50, dte=None, short_pct=None, volatility=85)
    for dte in (0, 1, 2, 3, 5, 7):
        assert wr.composite(70, 60, 50, dte=dte, short_pct=None, volatility=85) == base


def test_sessions_count_matches_busdays():
    for k in range(1, 12):
        ed = date.today() + timedelta(days=k)
        n, iso = wr.sessions_to_earnings("ABC", _cal("ABC", ed))
        assert n == int(np.busday_count(date.today() + timedelta(days=1), ed))
        assert iso == ed.isoformat()


def test_weekend_is_not_a_session():
    # find next Monday after a weekend: sessions between Friday and Monday = 0
    today = date.today()
    mon = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    n, _ = wr.sessions_to_earnings("ABC", _cal("ABC", mon))
    assert n == int(np.busday_count(today + timedelta(days=1), mon))


def test_past_or_missing_earnings():
    assert wr.sessions_to_earnings("ABC", _cal("ABC", date.today() - timedelta(days=1))) is None
    assert wr.sessions_to_earnings("ABC", _cal("XYZ", date.today() + timedelta(days=3))) is None
    assert wr.sessions_to_earnings("ABC", []) is None


def test_rule_scope():
    assert EARNINGS_EXIT_SESSIONS == 2
    assert EARNINGS_TRIM_STRATEGIES == {"SWING", "MOMENTUM"}
