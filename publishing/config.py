"""
publishing/config.py — settings for the public research track.

This folder is deliberately detached from the rest of Trading-Agent. It imports
nothing from the parent repo and modifies nothing there. It only *reads* the
JSON the existing pipeline already writes into ../data/, and the trade journal
in ../logs/.

Your personal trading system is untouched and keeps working exactly as before.

BEFORE PUBLISHING ANYTHING, fill in the ENTITY block below.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# ── read-only inputs: written by the existing pipeline ──────────────────────
DATA = REPO / "data"
LOGS = REPO / "logs"

MARKET_DATA_PATH  = DATA / "market_data.json"
FUNDAMENTAL_PATH  = DATA / "fundamental_data.json"
SENTIMENT_PATH    = DATA / "sentiment_data.json"
SECTOR_PATH       = DATA / "sector_rotation.json"
MACRO_REGIME_PATH = DATA / "macro_regime.json"
EARNINGS_PATH     = DATA / "earnings_calendar.json"
TRADES_PATH       = LOGS / "trades.jsonl"

# ── outputs: written only inside this folder ────────────────────────────────
PUBLICATIONS_DIR = HERE / "publications"
HISTORY_PATH     = HERE / "recommendation_history.jsonl"
DRAFTS_DIR       = HERE / "drafts"

# ── ENTITY ──────────────────────────────────────────────────────────────────
# MAR Art. 20 requires every publication to identify who produced it. This is
# the first disclosure on the page, not decoration.
#
# The address below is still a gap. publish.py refuses to render while any
# [square brackets] remain here, so a provisional value cannot quietly end up
# printed on something a paying subscriber reads. Fill it in, and the block
# lifts by itself.
PRODUCER = "Equity.ie Ltd, [SEDE LEGALE DA INSERIRE]"
AUTHOR   = "Andrea Guida"

ISSUER_RELATIONSHIP = (
    "No payment or consideration received from the issuer. No issuer or third "
    "party reviewed this publication before dissemination."
)

# ── position disclosure ─────────────────────────────────────────────────────
# trades.jsonl is a journal, not a position record. Until every position you
# actually hold is logged there AND you have checked it against the broker,
# leave these as they are: the code will refuse to publish rather than assert
# a position that may be wrong.
#
# When reconciled, set POSITIONS_COMPLETE = True and put the date you checked
# into POSITIONS_RECONCILED_AT, e.g. datetime(2026, 9, 1, tzinfo=timezone.utc)
POSITIONS_COMPLETE     = False
POSITIONS_RECONCILED_AT = None
POSITION_MAX_AGE_HOURS  = 24 * 7        # a journal, checked weekly

# ── personal dealing ────────────────────────────────────────────────────────
# Days either side of a publication during which you do not trade the
# instrument you wrote about. Publishing a BUY on something you bought last week
# is the shape of scalping whether or not you meant it that way; a written
# blackout is what makes the answer to that accusation boring.
#
# `publish.py check` reminds you of this every time. Nothing enforces it — only
# you can.
BLACKOUT_DAYS = 5

# Map company names or alternative symbols to the ticker used in trades.jsonl
POSITION_ALIASES = {
    # "Amazon": "AMZN",
    # "Societe Generale": "GLE.PA",
}
