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
#  SENTIMENT — sentiment_data.json  (sentiment_agent.py)
#
#  DIFFERENT SHAPE from the two schemas above: this file is ONE market-wide
#  document, not a collection of per-ticker records. So there is no per-record
#  quarantine — validation is a single call on the whole document.
#
#  Every top-level section is Optional because each fetch_*() returns None on
#  failure and composite_score() explicitly tolerates that ("flag, never
#  block"). A partial run is a VALID run — making sections required would
#  reject good data whenever Yahoo hiccups.
# ═══════════════════════════════════════════════════════════════════════════

# Shared label vocabularies (see label_vix / fng_label / composite_score)
RiskLabel = Literal["Risk-On", "Mild Risk-On", "Neutral", "Mild Risk-Off", "Risk-Off"]
VixLabel  = Literal["unknown", "complacency", "calm", "elevated", "fear", "extreme_fear"]


class FearGreedRecord(BaseModel):
    """cnn_fear_greed — CNN Fear & Greed index. Built all-or-nothing."""
    score: float
    rating: Literal["unknown", "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
    raw_rating: str          # CNN's own wording, passed through unmapped
    prev_1_week: float
    prev_1_month: float
    prev_1_year: float
    weekly_delta: float
    monthly_delta: float
    interpretation: str


class VixRecord(BaseModel):
    """vix — spot VIX plus term structure. ^VIX9D / ^VIX3M are often
    unavailable on Yahoo, hence the optional 9d/3m fields."""
    spot: float
    prev_close: float
    change_1d: float | None = None      # pct_change() returns None if prev is 0
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
    """One US index inside market_internals (SPY / QQQ / IWM)."""
    price: float
    ma_50: float
    ma_200: float
    ma_125: float
    above_ma50: bool
    above_ma200: bool
    above_ma125: bool | None = None      # None when ma_125 is unavailable
    pct_from_ma200: float | None = None
    label: str


class RatioRecord(BaseModel):
    """qqq_spy_ratio / iwm_spy_ratio — leadership ratios; every numeric
    field is guarded by a length/zero check in ratio_data()."""
    label: str
    ratio: float | None = None
    delta_5d: float | None = None
    delta_20d: float | None = None
    trend_5d: str                        # arrow glyph, not a stable vocabulary


class MarketInternals(BaseModel):
    """market_internals — SPY/QQQ/IWM are required here: fetch_market_internals()
    builds all three or raises and returns None for the whole section."""
    SPY: IndexRecord
    QQQ: IndexRecord
    IWM: IndexRecord
    breadth_note: str
    qqq_spy_ratio: RatioRecord
    iwm_spy_ratio: RatioRecord


class EtfReturnRecord(BaseModel):
    """One ETF inside safe_haven / credit — price plus trailing returns."""
    price: float
    ret_5d: float | None = None
    ret_20d: float | None = None
    label: str


class SafeHaven(BaseModel):
    """safe_haven — each symbol is skipped (`continue`) when its history is
    empty, so any of the three can be absent from an otherwise-valid section."""
    TLT: EtfReturnRecord | None = None
    GLD: EtfReturnRecord | None = None
    UUP: EtfReturnRecord | None = None
    interpretation: str


class Credit(BaseModel):
    """credit — same skip-on-empty behaviour as SafeHaven."""
    HYG: EtfReturnRecord | None = None
    LQD: EtfReturnRecord | None = None
    JNK: EtfReturnRecord | None = None
    interpretation: str


class PutCall(BaseModel):
    """put_call — SPY option-chain open interest. Built all-or-nothing."""
    ratio: float
    calls_oi: int
    puts_oi: int
    label: str
    expiry_used: str
    interpretation: str


class Rates(BaseModel):
    """rates — 10Y Treasury (^TNX)."""
    yield_10y: float
    prev_close: float
    change_1d: float
    change_5d: float | None = None       # needs >= 6 bars
    change_20d: float | None = None      # needs >= 21 bars
    ma_20: float
    trend: Literal["rising", "falling", "stable"]
    interpretation: str


class EuIndexRecord(BaseModel):
    """One EU index inside eu_internals."""
    label: str
    price: float
    ma_50: float
    ma_200: float
    above_ma50: bool | None = None
    above_ma200: bool | None = None
    pct_from_ma200: float | None = None
    ret_5d: float | None = None
    ret_1m: float | None = None


class VstoxxRecord(BaseModel):
    """eu_internals.VSTOXX — ^V2TX with ^VDAX fallback; absent if neither loads."""
    spot: float
    prev: float
    change_1d: float
    percentile: float
    label: VixLabel


class EurUsdRecord(BaseModel):
    """eu_internals.EURUSD."""
    price: float
    ret_5d: float | None = None
    ret_20d: float | None = None
    trend: Literal["strengthening", "weakening", "stable"]


class EuInternals(BaseModel):
    """eu_internals — every index is wrapped in its own try/continue, so all
    four are optional. The Yahoo symbols start with '^' or contain '.', which
    are not legal Python names, so each uses an alias (same trick as 52w_high)."""
    gdaxi: EuIndexRecord | None = Field(default=None, alias="^GDAXI")
    ftse: EuIndexRecord | None = Field(default=None, alias="^FTSE")
    fchi: EuIndexRecord | None = Field(default=None, alias="^FCHI")
    ftsemib: EuIndexRecord | None = Field(default=None, alias="FTSEMIB.MI")
    VSTOXX: VstoxxRecord | None = None
    EURUSD: EurUsdRecord | None = None
    eu_breadth: str
    eu_bull_regime: bool | None = None    # None when no index was tracked
    interpretation: str


class SentimentSnapshot(BaseModel):
    """The whole sentiment_data.json document — one snapshot per run."""
    generated_at: str
    composite_score: float = Field(allow_inf_nan=False)
    composite_label: RiskLabel
    composite_delta: float | None = None   # None on the first ever run

    # Sections — None means "that fetch failed this run", which is tolerated
    cnn_fear_greed: FearGreedRecord | None = None
    vix: VixRecord | None = None
    market_internals: MarketInternals | None = None
    safe_haven: SafeHaven | None = None
    credit: Credit | None = None
    put_call: PutCall | None = None
    rates: Rates | None = None
    eu_internals: EuInternals | None = None

    eu_composite_score: float | None = None            # None when eu is missing
    eu_composite_label: RiskLabel | Literal["N/A"]

    # Written by sentiment_agent.py AFTER validation, so they are absent from the
    # document being validated but present in the file on disk.
    schema_valid: bool | None = None
    schema_errors: list[dict] | None = None