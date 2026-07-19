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