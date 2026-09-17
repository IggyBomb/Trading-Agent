"""
market_outlook.py — the weekly market/sector review, as a publication type
distinct from the single-instrument `Publication` in compliance_guard.py.

Why this is a separate class, not a mode of `Publication`
-----------------------------------------------------------
`Publication` is built around one instrument: one ISIN, one rating, one target,
one position disclosure. A weekly macro/sector review is structurally
different — it has no single instrument and no BUY/HOLD/SELL rating, but it
still routinely names specific tradeable instruments (sector ETFs, indices via
their proxies) with an implied lean ("Energy in leadership", "rotation into
Financials"). That is still an MAR Article 20 disclosure trigger — just for
several instruments instead of one. Bolting that onto `Publication`'s
single `position_disclosure` field would either weaken the single-instrument
guarantee or silently make the multi-instrument case unenforced. Two
lightweight, honest classes beat one field pretending to be both.

Everything else — the "about the instrument(s), never about the reader" rule,
the same MAR footer, the same refusal-on-missing-field posture — carries over
unchanged. `OutputValidator` is reused as-is; a market outlook body must pass
the identical personalisation scan a single-instrument piece does.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence, Union

from compliance_guard import ComplianceError, OutputValidator, PUBLICATION_FOOTER, _utc

__all__ = ["MarketOutlookPublication"]


@dataclass
class MarketOutlookPublication:
    """
    A weekly market/sector review with the same disclosure rigour as
    `Publication`, adapted to a multi-instrument, no-rating piece.

    `positions` takes the place of `Publication.position_disclosure`: one
    disclosure line per instrument named in the body with a directional lean
    (a sector ETF called out as "leading" or "lagging" counts). Each entry may
    be a plain string or a zero-argument callable resolved at render time —
    same reasoning as `Publication.position_disclosure`: the book can move
    between drafting and publishing.

    There is no `rating`/`price_target`/`isin` here on purpose — a market
    outlook does not carry a single-instrument recommendation. If a piece
    needs those, it is a `Publication`, not this.
    """

    # identity
    producer: str
    author: str

    # scope
    period: str                       # e.g. "Week of 2026-09-04"
    regime: str                       # e.g. "REFLATION — mid cycle, HIGH confidence"

    # substantiation
    sources: Sequence[str]

    # conflicts — one entry per instrument named with a lean in the body.
    # Each may be a string or a zero-arg callable resolved at render time.
    positions: Sequence[Union[str, Callable[[], str]]]

    issuer_relationship: str = (
        "No payment or consideration received from any issuer. No issuer or "
        "third party reviewed this publication before dissemination."
    )

    # body
    body: str = ""

    # timing
    produced_at: Optional[datetime] = None
    disseminated_at: Optional[datetime] = None

    # standing text — same MAR footer as a single-instrument publication
    footer: str = PUBLICATION_FOOTER

    _REQUIRED = ("producer", "author", "period", "regime", "body")

    def resolve_positions(self) -> List[str]:
        """
        Resolve every position entry now, at render time. Mirrors
        `Publication.resolve_position` — a callable is invoked here so each
        line reflects the book as it stands at publication, not at drafting.
        """
        resolved: List[str] = []
        for entry in self.positions:
            value = entry() if callable(entry) else entry
            text = str(value).strip()
            if not text:
                raise ComplianceError(
                    "A position entry resolved to nothing. Every instrument "
                    "named with a lean in the body must carry a stated "
                    "disclosure, not a blank one."
                )
            resolved.append(text)
        return resolved

    def missing_fields(self) -> List[str]:
        missing = [f for f in self._REQUIRED if not str(getattr(self, f, "")).strip()]
        if not self.sources:
            missing.append("sources")
        if not self.positions:
            missing.append("positions")
        return missing

    def validate(self) -> None:
        missing = self.missing_fields()
        if missing:
            raise ComplianceError(
                "Market outlook is missing required disclosures: " + ", ".join(missing)
            )

    def header(self, positions: Optional[List[str]] = None) -> str:
        src = "\n".join(f"  - {s}" for s in self.sources)
        positions = positions if positions is not None else self.resolve_positions()
        pos_block = "\n".join(f"  - {p}" for p in positions)
        return (
            f"Producer:      {self.producer}\n"
            f"Author:        {self.author}\n"
            f"Produced:      {_utc(self.produced_at)}\n"
            f"Disseminated:  {_utc(self.disseminated_at)}\n"
            f"\n"
            f"Coverage:      {self.period}\n"
            f"Regime read:   {self.regime}\n"
            f"\n"
            f"Sources:\n{src}\n"
            f"\n"
            f"Positions (every instrument named with a lean below):\n{pos_block}\n"
            f"Issuer relationships: {self.issuer_relationship}"
        )

    def render(self, validator: Optional[OutputValidator] = None,
               allow_warnings: bool = True) -> str:
        """
        Same contract as `Publication.render`: raises ComplianceError on a
        missing disclosure or a personalised body; `allow_warnings=False`
        turns WARN findings into blockers for CI use.
        """
        self.validate()
        positions = self.resolve_positions()      # live lookups happen here
        validator = validator or OutputValidator()
        report = validator.check(self.body)
        report.raise_if_blocked()
        if not allow_warnings and report.warnings:
            lines = "\n  ".join(str(f) for f in report.warnings)
            raise ComplianceError(f"Warnings unresolved:\n  {lines}")

        rule = "-" * 72
        return (
            f"{rule}\n{self.header(positions)}\n{rule}\n\n"
            f"{self.body.strip()}\n\n"
            f"{rule}\n{self.footer}\n{rule}"
        )
