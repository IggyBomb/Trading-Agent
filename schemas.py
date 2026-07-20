from typing import Literal
from pydantic import BaseModel, Field


class TickerSignal(BaseModel):
    """One record in market_data.json 'signals' — the fetch_data.py → watchlist_ranker.py contract."""

    ticker: str
    price: float = Field(allow_inf_nan=False)   # NaN price = corrupted fetch
    change_pct: float
    trend: Literal["up", "down", "sideways"]

    # volume / volatility
    volume_ratio: float
    avg_volume: int
    atr: float
    atr_pct: float

    # support / resistance
    support: float
    resistance: float
    dist_support_pct: float
    dist_resist_pct: float

    # setup + conviction
    setup: str
    conviction: Literal["High", "Medium", "Low"]

    # trade levels
    entry: float | None = None
    stop: float | None = None
    target: float

    # indicators — all required: any null here = rejected record
    ma50: float | None = None
    ma200: float
    week52_high: float = Field(alias="52w_high")   # "52w_high" is not a legal Python name
    rsi: float

    rr: float   

    # short side — string sentinels are inconsistent on purpose:
    # "none" (lowercase) vs "None" (capitalized) is what the live pipeline emits
    # and what downstream consumers match. Do NOT "fix" without updating them.
    short_setup: str | None = None
    short_conviction: str | None = None


class FundamentalRecord(BaseModel):
    """One record in fundamental_data.json 'fundamentals' — the fundamental_agent.py contract.

    NOTE: the container is a DICT keyed by ticker, not a list:
        {"summary": {...}, "fundamentals": {"AAPL": {...}, ...}}
    so validate with:  for rec in data["fundamentals"].values(): ...
    """

    ticker: str

    # composite scores — always computed, never null
    f_score: float        # 0-100: value*4 + quality*4 + growth*2
    value_score: float    # 0-10
    quality_score: float  # 0-10
    growth_score: float   # 0-10
    rating: Literal["Undervalued", "Fair", "Overvalued"]  # fundamental_rating()'s only 3 returns

    # raw valuation metrics — _safe() defaults to None when yfinance lacks the
    # field, so ALL of these can be null (pb/market_cap have no nulls in today's
    # data, but the code path allows it — schema follows the code)
    pe: float | None = None
    fwd_pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    peg: float | None = None

    # raw profitability/growth metrics — computed with `or 0` / default-0
    # fallbacks, so always a number
    roe: float
    profit_margin: float
    debt_equity: float
    revenue_growth: float
    earnings_growth: float
    fcf_positive: bool

    market_cap: int | None = None
    sector: str    # _safe() defaults to "Unknown", never null
    industry: str