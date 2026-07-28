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
    
    
# ═══════════════════════════════════════════════════════════════════════════
#  ALT DATA — alt_data.json  (alt_data.py)
#
#  Container is a DICT keyed by ticker, like fundamental_data.json:
#      {"generated_at": ..., "tickers": {"PODD": {...}, ...}}
#  so validate with:  for rec in data["tickers"].values(): ...
#
#  Every sub-record has SEVERAL return shapes (OK / NO_API_KEY / NO_DATA /
#  UNAVAILABLE / ERROR). Fields only produced on the success path therefore
#  need defaults — otherwise a perfectly normal "no data" record is rejected.
#  All Literals below come from the CODE's reachable values, not from what the
#  current file happens to contain (the live file shows only a subset).
# ═══════════════════════════════════════════════════════════════════════════


class InsiderRecord(BaseModel):
    """insider — Form 4 open-market transactions via yfinance.
    Every path (success, _no_insider(), ERROR) returns all 8 fields."""

    cluster_signal: Literal[
        "STRONG_CLUSTER", "CLUSTER", "SINGLE_BUY_SIGNIFICANT",
        "SINGLE_BUY", "SELLING", "NONE", "ERROR",
    ]
    net_activity: Literal["BUY", "SELL", "MIXED", "NONE"]
    buyers_30d: int
    sellers_30d: int
    total_value_bought: int      # round() with no ndigits → int
    total_value_sold: int
    notable: list[str]
    interpretation: str


class InsiderSentimentRecord(BaseModel):
    """insider_sentiment — Finnhub MSPR. Has NO interpretation field (unlike
    every other section). months_used appears only on the OK path; error only
    on the ERROR path."""

    status: Literal["OK", "NO_API_KEY", "UNAVAILABLE", "NO_DATA", "ERROR"]
    avg_mspr: float | None = None
    trend: Literal["BULLISH", "NEUTRAL", "BEARISH", "UNKNOWN"]
    months_used: int | None = None
    error: str | None = None


class ShortInterestRecord(BaseModel):
    """short_interest — four fields off yfinance .info.
    The ERROR path returns ONLY signal/squeeze_watch/interpretation, so the
    three numeric fields must tolerate being absent as well as null."""

    short_pct_float: float | None = None
    days_to_cover: float | None = None
    mom_change_pct: float | None = None
    signal: Literal["LOW", "MODERATE", "HIGH", "EXTREME", "UNKNOWN", "ERROR"]
    squeeze_watch: bool
    interpretation: str


class AnalystTrendRecord(BaseModel):
    """analyst_trend — Finnhub recommendation counts. Everything below the
    first three fields exists only when status == "OK" (free plan is US-only,
    so non-US tickers never reach it)."""

    status: Literal["OK", "NO_API_KEY", "NO_DATA", "ERROR"]
    trend: Literal["IMPROVING", "STABLE", "DETERIORATING", "UNKNOWN"]
    interpretation: str

    bull_ratio_pct: float | None = None
    delta_pct: float | None = None
    period: str | None = None
    strong_buy: int | None = None
    buy: int | None = None
    hold: int | None = None
    sell: int | None = None
    strong_sell: int | None = None


class CongressionalRecord(BaseModel):
    """congressional — Quiver. Fetched and stored for reference but NOT scored
    (both free sources moved it behind paid plans). buys_count/sells_count
    exist only on the OK path."""

    status: Literal["OK", "NO_API_KEY", "NO_DATA", "ERROR"]
    net_direction: Literal["BUY", "SELL", "MIXED", "NONE", "UNKNOWN"]
    notable: list[str]
    recent_trades: list = []
    interpretation: str

    buys_count: int | None = None
    sells_count: int | None = None


class NewsSentimentRecord(BaseModel):
    """news_sentiment — VADER over yfinance headlines (Finnhub fallback).
    The VADER_UNAVAILABLE and ERROR paths return only status/label/
    interpretation, so the numeric fields need defaults."""

    status: Literal["OK", "NO_NEWS", "VADER_UNAVAILABLE", "ERROR"]
    sentiment_label: Literal["POSITIVE", "NEGATIVE", "NEUTRAL", "UNKNOWN"]
    interpretation: str

    sentiment_score: float | None = None
    velocity: Literal["RISING", "FALLING", "STABLE", "UNKNOWN"] | None = None
    article_count: int | None = None


class AltDataRecord(BaseModel):
    """One ticker in alt_data.json 'tickers' — the alt_data.py contract.

    NOTE the scoring floor: a record with no data anywhere still sums to
    9 + 2 + 10 + 10 + 10 = 41 points, so alt_data_score does not really run
    0-100. Check the status fields before trusting a mid-range score.
    """

    ticker: str
    alt_data_score: float = Field(allow_inf_nan=False)   # 0-100 after clamp
    alt_data_signal: Literal["BULLISH", "NEUTRAL", "BEARISH"]
    flags: list[str]

    insider: InsiderRecord
    insider_sentiment: InsiderSentimentRecord
    short_interest: ShortInterestRecord
    analyst_trend: AnalystTrendRecord
    congressional: CongressionalRecord
    news_sentiment: NewsSentimentRecord


class AltDataSnapshot(BaseModel):
    """The whole alt_data.json document."""

    generated_at: str
    total_tickers: int
    finnhub_enabled: bool
    quiver_enabled: bool
    vader_enabled: bool
    tickers: dict[str, AltDataRecord]