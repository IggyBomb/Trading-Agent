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

    rr: float            # true R:R at the ATR_STOP_MULT stop
    target_atr: float    # target distance in ATRs — scan.md Steps 5-9 gate (>= 1.5)

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


# ═══════════════════════════════════════════════════════════════════════════
#  SENTIMENT — sentiment_data.json  (sentiment_agent.py)
#
#  ONE document, not a per-ticker dict: market-wide sentiment for a single run.
#  Every fetch_*() wraps its body in try/except and returns None on failure, so
#  EVERY top-level section is `... | None`. A null section is a NORMAL run —
#  main() logs which ones are missing and computes the composite without them.
#  Inside a section, any field computed with pct_change() is `float | None`,
#  because pct_change() returns None whenever it lacks two non-zero points.
# ═══════════════════════════════════════════════════════════════════════════

VixLabel = Literal["complacency", "calm", "elevated", "fear", "extreme_fear"]
# label_vix() also returns "unknown", but only for v is None — unreachable here,
# since every caller passes a rounded float or the section fails to None.

RiskLabel = Literal["Risk-On", "Mild Risk-On", "Neutral", "Mild Risk-Off", "Risk-Off"]


class FearGreedRecord(BaseModel):
    """cnn_fear_greed — CNN graphdata endpoint. Single return shape: either all
    nine fields or the whole section is null. Nothing partial."""

    score: float
    rating: Literal["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
    raw_rating: str          # CNN's own wording, not ours — do NOT Literal it
    prev_1_week: float
    prev_1_month: float
    prev_1_year: float
    weekly_delta: float
    monthly_delta: float
    interpretation: str


class VixRecord(BaseModel):
    """vix — ^VIX plus the ^VIX9D / ^VIX3M term structure. The 9D/3M legs go
    None on empty history, which also nulls both spreads and forces
    term_structure="unknown"."""

    spot: float
    prev_close: float
    change_1d: float | None = None       # pct_change()
    ma_20: float
    ma_50: float
    vs_ma20: float
    vix_9d: float | None = None
    vix_3m: float | None = None
    vix9d_spread: float | None = None
    vix3m_spread: float | None = None
    term_structure: Literal["backwardation", "contango", "flat", "unknown"]
    percentile_1y: float
    label: VixLabel
    interpretation: str


class IndexRecord(BaseModel):
    """One US index inside market_internals (SPY/QQQ/IWM)."""

    price: float
    ma_50: float
    ma_200: float
    ma_125: float | None = None
    above_ma50: bool
    above_ma200: bool
    above_ma125: bool | None = None      # None when ma_125 is None
    pct_from_ma200: float | None = None
    label: str


class RatioRecord(BaseModel):
    """qqq_spy_ratio / iwm_spy_ratio — ratio_data() always returns all five
    keys, but every number is None when the series is too short."""

    label: str
    ratio: float | None = None
    delta_5d: float | None = None
    delta_20d: float | None = None
    trend_5d: Literal["↑", "↓", "→"]   # up / down / flat arrows


class MarketInternals(BaseModel):
    """market_internals — a MIXED dict: three sub-records under their own ticker
    keys, plus two ratios and a note. All three tickers are required: any one
    failing raises and takes the whole section to None."""

    SPY: IndexRecord
    QQQ: IndexRecord
    IWM: IndexRecord
    breadth_note: str
    qqq_spy_ratio: RatioRecord
    iwm_spy_ratio: RatioRecord


class EtfRecord(BaseModel):
    """One ETF leg inside safe_haven or credit — identical four fields."""

    price: float
    ret_5d: float | None = None
    ret_20d: float | None = None
    label: str


class SafeHavenRecord(BaseModel):
    """safe_haven — TLT/GLD/UUP. Each leg is skipped (`continue`) on empty
    history, so all three are optional; interpretation is always written."""

    TLT: EtfRecord | None = None
    GLD: EtfRecord | None = None
    UUP: EtfRecord | None = None
    interpretation: str


class CreditRecord(BaseModel):
    """credit — HYG/LQD/JNK, same skip-on-empty rule as safe_haven."""

    HYG: EtfRecord | None = None
    LQD: EtfRecord | None = None
    JNK: EtfRecord | None = None
    interpretation: str


class PutCallRecord(BaseModel):
    """put_call — SPY front-expiry open interest. Returns None rather than a
    partial record when there are no expiries or zero call OI, so every field
    here is required."""

    ratio: float
    calls_oi: int
    puts_oi: int
    label: str
    expiry_used: str
    interpretation: str


class EuIndexRecord(BaseModel):
    """One EU index inside eu_internals. ma_50/ma_200 come from ma(), which
    returns None on a short series — and that nulls the above_* flags too."""

    label: str
    price: float
    ma_50: float | None = None
    ma_200: float | None = None
    above_ma50: bool | None = None
    above_ma200: bool | None = None
    pct_from_ma200: float | None = None
    ret_5d: float | None = None
    ret_1m: float | None = None


class VstoxxRecord(BaseModel):
    """eu_internals.VSTOXX — ^V2TX with ^VDAX fallback; absent if both empty."""

    spot: float
    prev: float
    change_1d: float
    percentile: float
    label: VixLabel


class EurUsdRecord(BaseModel):
    """eu_internals.EURUSD — EURUSD=X; absent if no history."""

    price: float
    ret_5d: float | None = None
    ret_20d: float | None = None
    trend: Literal["strengthening", "weakening", "stable"]


class EuInternals(BaseModel):
    """eu_internals — every index / VSTOXX / EURUSD leg has its OWN try/except
    and is simply omitted on failure, so all of them are optional. Only the
    three breadth keys are guaranteed.

    Yahoo symbols are not legal Python names, hence the aliases (same trick as
    TickerSignal.week52_high). The MIB key is "FTSEMIB.MI" — ^FTSEMIB is not
    available on Yahoo free. Fetch, breadth, composite scoring and display all
    iterate sentiment_agent.EU_INDEX_SYMBOLS, so the keys stay in sync.
    """

    dax:     EuIndexRecord | None = Field(default=None, alias="^GDAXI")
    ftse:    EuIndexRecord | None = Field(default=None, alias="^FTSE")
    cac:     EuIndexRecord | None = Field(default=None, alias="^FCHI")
    ftsemib: EuIndexRecord | None = Field(default=None, alias="FTSEMIB.MI")

    VSTOXX: VstoxxRecord | None = None
    EURUSD: EurUsdRecord | None = None

    eu_breadth: str
    eu_bull_regime: bool | None = None   # None when no EU index was tracked
    interpretation: str


class RatesRecord(BaseModel):
    """rates — ^TNX 10Y yield. change_5d/change_20d need 6/21 closes; these are
    yield DIFFERENCES in points, not percent changes."""

    yield_10y: float
    prev_close: float
    change_1d: float
    change_5d: float | None = None
    change_20d: float | None = None
    ma_20: float
    trend: Literal["rising", "falling", "stable"]
    interpretation: str


class SchemaError(BaseModel):
    """One entry in schema_errors — written by sentiment_agent's own validation
    pass, so it never appears in the dict being validated."""

    field: str
    error: str


class SentimentSnapshot(BaseModel):
    """The whole sentiment_data.json document.

    Validated in main() BEFORE schema_valid/schema_errors are attached, so those
    two carry defaults: the file on disk always has them, the validated dict
    never does.
    """

    generated_at: str
    composite_score: float
    composite_label: RiskLabel
    composite_delta: float | None = None     # None on the first ever run

    cnn_fear_greed:   FearGreedRecord | None = None
    vix:              VixRecord       | None = None
    market_internals: MarketInternals | None = None
    safe_haven:       SafeHavenRecord | None = None
    credit:           CreditRecord    | None = None
    put_call:         PutCallRecord   | None = None
    rates:            RatesRecord     | None = None

    eu_internals:       EuInternals | None = None
    eu_composite_score: float | None = None   # None when eu_internals is null

    # RiskLabel plus "N/A", which eu_composite_score() returns when eu is null.
    # Spelled flat rather than `RiskLabel | Literal["N/A"]` to keep it obvious.
    eu_composite_label: Literal[
        "Risk-On", "Mild Risk-On", "Neutral", "Mild Risk-Off", "Risk-Off", "N/A"
    ]

    schema_valid:  bool | None = None
    schema_errors: list[SchemaError] = []