"""
compliance_guard.py — output guardrails for a subscription investment research service.

Purpose
-------
Keep generated output on the *research publishing* side of the MiFID II line by:

  1. INPUT GATE      refusing questions that can only be answered with a personal
                     recommendation ("should I buy this?", "how much for my size?").
  2. OUTPUT VALIDATOR scanning drafted text for personalisation before it ships
                     (second person about the reader's portfolio, sizing, "my call").
  3. PUBLICATION      attaching the MAR Article 20 / Delegated Reg (EU) 2016/958
                     disclosure block that every publication must carry, and
                     refusing to render when a required field is missing.

The governing rule this enforces
--------------------------------
Every subscriber receives the same publication, at the same time, in the same
form. Nothing is rendered per user. Content is about the *instrument*, never
about the *reader*.

Scope and limits
----------------
This is an engineering control, not legal advice, and not a compliance opinion.
It cannot make unlawful output lawful. It makes the common failure modes visible
and blocks the obvious ones. Regex cannot understand intent: treat a clean report
as "no known pattern matched", never as "this is compliant".

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Iterable, List, Optional, Pattern, Sequence, Union

__all__ = [
    "Severity",
    "Finding",
    "Report",
    "InputGate",
    "GateVerdict",
    "OutputValidator",
    "Publication",
    "ComplianceError",
    "STANDING_REPLY",
    "PUBLICATION_FOOTER",
    "DEFAULT_RATING_DEFINITIONS",
]


# ---------------------------------------------------------------------------
# Standing texts
# ---------------------------------------------------------------------------

STANDING_REPLY = (
    "We can't answer questions about individual positions or circumstances. "
    "Everything we publish is available to all subscribers equally, and the "
    "decision on whether to act, at what size and at what time is yours alone."
)

PUBLICATION_FOOTER = (
    "This publication is general investment research issued exclusively to the "
    "public. Every subscriber receives identical content at the same time. It is "
    "not a personal recommendation within the meaning of Article 4(1)(4) of "
    "Directive 2014/65/EU or Article 9 of Commission Delegated Regulation (EU) "
    "2017/565, is not presented as suitable for any particular person, and takes "
    "no account of any reader's objectives, financial situation, knowledge, "
    "experience, tax position or needs. Statements of fact are sourced above; all "
    "targets, forecasts and ratings are opinion and estimate. The value of "
    "investments can fall as well as rise and you may get back less than you "
    "invest. Past performance is not a reliable indicator of future results."
)

DEFAULT_RATING_DEFINITIONS = (
    "BUY = expected total return above 15% over the stated horizon. "
    "HOLD = -10% to +15%. SELL = below -10%."
)

VALID_RATINGS = ("BUY", "HOLD", "SELL")


class ComplianceError(RuntimeError):
    """Raised when a publication cannot be rendered or shipped as-is."""


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------

class Severity(Enum):
    BLOCK = "BLOCK"   # must not ship
    WARN = "WARN"     # human must look at it


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    excerpt: str
    start: int
    end: int

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.rule_id}: {self.message} — …{self.excerpt}…"


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)

    @property
    def blocking(self) -> List[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCK]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARN]

    @property
    def clean(self) -> bool:
        """No blocking findings. Warnings may still be present."""
        return not self.blocking

    def raise_if_blocked(self) -> None:
        if self.blocking:
            lines = "\n  ".join(str(f) for f in self.blocking)
            raise ComplianceError(
                f"{len(self.blocking)} blocking finding(s); publication withheld:\n  {lines}"
            )

    def __str__(self) -> str:
        if not self.findings:
            return "No patterns matched. (Not a statement that the text is compliant.)"
        return "\n".join(str(f) for f in self.findings)


# ---------------------------------------------------------------------------
# Rule table
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Rule:
    rule_id: str
    pattern: Pattern[str]
    severity: Severity
    message: str


def _rule(rule_id: str, regex: str, severity: Severity, message: str) -> _Rule:
    return _Rule(rule_id, re.compile(regex, re.IGNORECASE), severity, message)


# --- questions that cannot be answered without giving a personal recommendation
INPUT_RULES: Sequence[_Rule] = (
    _rule("IN-01", r"\bshould\s+(i|we)\b", Severity.BLOCK,
          "Asks for a recommendation directed at the questioner"),
    _rule("IN-02", r"\bwhat\s+(should|would)\s+(i|we)\s+(do|buy|sell)\b", Severity.BLOCK,
          "Asks what the questioner should do"),
    _rule("IN-03", r"\bhow\s+much\s+(should|can|do|would)\s+(i|we)\b", Severity.BLOCK,
          "Asks for a position size for the questioner"),
    _rule("IN-04",
          r"\b(my|our)\s+(portfolio|position|positions|holding|holdings|account|book|"
          r"allocation|exposure|savings|pension|capital|stack)\b",
          Severity.BLOCK, "References the questioner's own holdings"),
    _rule("IN-05", r"\b(right|suitable|appropriate|good)\s+for\s+(me|us)\b", Severity.BLOCK,
          "Asks for a suitability judgement"),
    _rule("IN-06", r"\bin\s+(my|our)\s+(case|situation|circumstances|position)\b", Severity.BLOCK,
          "Asks for an answer conditioned on the questioner's circumstances"),
    _rule("IN-07", r"\bcan\s+(i|we)\s+afford\b", Severity.BLOCK,
          "Asks about the questioner's financial capacity"),
    _rule("IN-08", r"\b(my|our)\s+risk\s+(tolerance|appetite|profile|budget)\b", Severity.BLOCK,
          "References the questioner's risk profile"),
    _rule("IN-09", r"\bsize\s+(this|it|that)\s+for\s+(me|us)\b", Severity.BLOCK,
          "Asks for sizing directed at the questioner"),
    _rule("IN-10",
          r"\b(?:i|we)(?:['’](?:m|ve)|\s+(?:am|are|have))?\s+"
          r"(?:hold|holding|own|owns|bought|long|short)\b",
          Severity.BLOCK, "Discloses the questioner's own position"),
    _rule("IN-11", r"\bwith\s+(my|our)\s*[€$£]?\s*\d", Severity.BLOCK,
          "States an amount the questioner has to deploy"),
    _rule("IN-12", r"\b(rebalance|allocate)\s+(my|our)\b", Severity.BLOCK,
          "Asks for portfolio construction advice"),
)

# --- personalisation that must never appear in a published piece
OUTPUT_RULES: Sequence[_Rule] = (
    _rule("OUT-01",
          r"\byour\s+(portfolio|position|positions|holding|holdings|account|sizing|size|"
          r"allocation|exposure|risk\s+tolerance|book|capital|stack|circumstances)\b",
          Severity.BLOCK, "Addresses the reader's own holdings or circumstances"),
    _rule("OUT-02", r"\byou\s+(should|must|need\s+to|ought\s+to)\b", Severity.BLOCK,
          "Instruction directed at the reader"),
    _rule("OUT-03", r"\bi(?:'d|\s+would)\s+(buy|sell|start|add|trim|exit|hold|open|close)\b",
          Severity.BLOCK, "First-person trade instruction reads as a recommendation to act"),
    _rule("OUT-04", r"\bmy\s+call\b", Severity.BLOCK,
          "Presents the view as a directive rather than analysis"),
    _rule("OUT-05", r"\b(suitable|appropriate|right)\s+for\s+you\b", Severity.BLOCK,
          "Explicit suitability statement — the definitional trigger for advice"),
    _rule("OUT-06", r"\bgiven\s+your\b", Severity.BLOCK,
          "Conditions the view on the reader's circumstances"),
    _rule("OUT-07", r"\brisk(?:ing)?\s+\d+(?:\.\d+)?\s*%", Severity.BLOCK,
          "Position sizing instruction"),
    _rule("OUT-08", r"\bposition\s+siz(?:e|ing)\b", Severity.BLOCK,
          "Position sizing is inherently a function of the individual"),
    _rule("OUT-09", r"\b(?:max|maximum|no\s+more\s+than)\s+\d+(?:\.\d+)?\s*%\s*(?:of|per)\b",
          Severity.BLOCK, "Caps a position as a share of the reader's capital"),
    _rule("OUT-10", r"\ballocate\s+\d+(?:\.\d+)?\s*%", Severity.BLOCK,
          "Allocation instruction"),
    _rule("OUT-11", r"\bhow\s+much\s+to\s+(buy|sell|put|deploy|commit)\b", Severity.BLOCK,
          "Sizing guidance"),
    _rule("OUT-12", r"\byour\s+(own\s+)?(system|rules?|strategy|plan|method)\b", Severity.BLOCK,
          "References the reader's own trading system"),

    # --- warn: instruction-shaped language that usually needs rewriting
    _rule("OUT-20", r"(?:^|[.!?]\s+)(Buy|Sell|Add|Trim|Exit|Start|Build|Accumulate)\s",
          Severity.WARN, "Imperative opening reads as an instruction — recast as analysis"),
    _rule("OUT-21", r"\btranche(?:s)?\b", Severity.WARN,
          "Tranche language describes an execution plan for a person, not the instrument"),
    _rule("OUT-22", r"\bstop[-\s]?loss\b", Severity.WARN,
          "Frame as a thesis-invalidation level, not an order instruction"),
    _rule("OUT-23", r"\bstart\s+a\s+position\b", Severity.WARN,
          "Recommends taking a step — prefer a rating with a stated horizon"),
    _rule("OUT-24", r"\bnot\s+(?:a\s+)?financial\s+advice\b", Severity.WARN,
          "A bare 'not financial advice' line is not a control and may read as a fig leaf"),
    _rule("OUT-25", r"\byou\b", Severity.WARN,
          "Second person present — confirm every instance refers to the instrument, not the reader"),
)


def _scan(text: str, rules: Iterable[_Rule], context: int = 42) -> Report:
    report = Report()
    seen: set = set()
    for rule in rules:
        for m in rule.pattern.finditer(text):
            key = (rule.rule_id, m.start())
            if key in seen:
                continue
            seen.add(key)
            lo = max(0, m.start() - context)
            hi = min(len(text), m.end() + context)
            excerpt = " ".join(text[lo:hi].split())
            report.findings.append(
                Finding(rule.rule_id, rule.severity, rule.message, excerpt, m.start(), m.end())
            )
    report.findings.sort(key=lambda f: (f.severity is Severity.WARN, f.start))
    return report


# ---------------------------------------------------------------------------
# Input gate
# ---------------------------------------------------------------------------

@dataclass
class GateVerdict:
    allowed: bool
    report: Report
    reply: Optional[str] = None

    def __bool__(self) -> bool:
        return self.allowed


class InputGate:
    """
    Screens inbound questions. Anything that can only be answered with a personal
    recommendation is refused with the standing reply.

    Use on every inbound channel — chat, support inbox, community forum. The
    channel you forget is the one that turns the business into an advisory.
    """

    def __init__(self, rules: Sequence[_Rule] = INPUT_RULES, reply: str = STANDING_REPLY):
        self._rules = rules
        self._reply = reply

    def check(self, question: str) -> GateVerdict:
        report = _scan(question, self._rules)
        if report.blocking:
            return GateVerdict(allowed=False, report=report, reply=self._reply)
        return GateVerdict(allowed=True, report=report)


# ---------------------------------------------------------------------------
# Output validator
# ---------------------------------------------------------------------------

class OutputValidator:
    """
    Scans drafted text before it is published.

    A BLOCK finding means the draft personalises and must be rewritten.
    A WARN finding means a human decides. Warnings are not optional noise —
    OUT-25 in particular will fire on most drafts and is there to force a read.
    """

    def __init__(self, rules: Sequence[_Rule] = OUTPUT_RULES):
        self._rules = rules

    def check(self, draft: str) -> Report:
        return _scan(draft, self._rules)

    def assert_clean(self, draft: str) -> None:
        self.check(draft).raise_if_blocked()


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def _utc(ts: Optional[datetime]) -> str:
    if ts is None:
        ts = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@dataclass
class Publication:
    """
    A single research publication with the full MAR Article 20 /
    Delegated Regulation (EU) 2016/958 disclosure apparatus.

    Every field below is required because every one of them is a disclosure
    obligation. `position_disclosure` has no default on purpose: the most
    common and most damaging omission is publishing a rating on an instrument
    you hold without saying so, so the caller is forced to state it either way.

    `position_disclosure` may be a plain string, or — better — a zero-argument
    callable resolved when `render()` runs. Pass a callable whenever the book
    can change between drafting and publishing, which is essentially always:
    a piece drafted on Monday and published on Wednesday must disclose
    Wednesday's position, not Monday's. See `disclosures.live_position_disclosure`.

    `previous` likewise has no safe default — pass the prior rating and its date,
    or the string "none" to assert there was no recommendation on this instrument
    in the preceding twelve months. Silence is not permitted.
    """

    # identity
    producer: str                 # legal entity name and registered address
    author: str

    # instrument
    instrument: str               # e.g. "Société Générale SA (GLE FP)"
    isin: str

    # the recommendation
    rating: str                   # BUY | HOLD | SELL
    price_target: str
    horizon: str                  # e.g. "12 months"
    price_at_production: str
    previous: str                 # e.g. "HOLD (issued 2026-05-12)" or "none"

    # substantiation
    valuation_basis: str          # methodology AND assumptions
    sources: Sequence[str]

    # conflicts — a string, or a callable resolved at render time
    position_disclosure: Union[str, Callable[[], str]]
    issuer_relationship: str = (
        "No payment or consideration received from the issuer. No issuer or third "
        "party reviewed this publication before dissemination."
    )

    # body
    body: str = ""

    # timing
    produced_at: Optional[datetime] = None
    disseminated_at: Optional[datetime] = None

    # standing text
    rating_definitions: str = DEFAULT_RATING_DEFINITIONS
    footer: str = PUBLICATION_FOOTER

    _REQUIRED = (
        "producer", "author", "instrument", "isin", "rating", "price_target",
        "horizon", "price_at_production", "previous", "valuation_basis",
        "position_disclosure", "body",
    )

    def resolve_position(self) -> str:
        """
        Resolve the position disclosure now. A callable is invoked here, at
        render time, so the line reflects the book as it stands at publication
        rather than as it stood when the draft was written.

        Anything the callable raises propagates. That is deliberate: a position
        source that cannot be read must stop the publication, never fall through
        to a 'holds no position' line that may be false.
        """
        value = self.position_disclosure
        if callable(value):
            resolved = value()
            if not str(resolved).strip():
                raise ComplianceError(
                    "The position_disclosure callable returned nothing. It must "
                    "state the position either way."
                )
            return str(resolved).strip()
        return str(value).strip()

    def missing_fields(self) -> List[str]:
        missing = [
            f for f in self._REQUIRED
            if f != "position_disclosure" and not str(getattr(self, f, "")).strip()
        ]
        if not callable(self.position_disclosure) and not str(self.position_disclosure).strip():
            missing.append("position_disclosure")
        if not self.sources:
            missing.append("sources")
        return missing

    def validate(self) -> None:
        missing = self.missing_fields()
        if missing:
            raise ComplianceError(
                "Publication is missing required disclosures: " + ", ".join(missing)
            )
        if self.rating.strip().upper() not in VALID_RATINGS:
            raise ComplianceError(
                f"Rating {self.rating!r} is not one of the published definitions "
                f"{VALID_RATINGS}. An undefined rating is not objective presentation."
            )

    def header(self, position: Optional[str] = None) -> str:
        src = "\n".join(f"  - {s}" for s in self.sources)
        position = position if position is not None else self.resolve_position()
        return (
            f"Producer:      {self.producer}\n"
            f"Author:        {self.author}\n"
            f"Produced:      {_utc(self.produced_at)}\n"
            f"Disseminated:  {_utc(self.disseminated_at)}\n"
            f"\n"
            f"Instrument:    {self.instrument} — ISIN {self.isin}\n"
            f"Rating:        {self.rating.strip().upper()}   "
            f"Previous: {self.previous}\n"
            f"Price target:  {self.price_target}   Horizon: {self.horizon}\n"
            f"Price at production: {self.price_at_production}\n"
            f"\n"
            f"Valuation basis: {self.valuation_basis}\n"
            f"\n"
            f"Rating definitions: {self.rating_definitions}\n"
            f"\n"
            f"Sources:\n{src}\n"
            f"\n"
            f"Positions: {position}\n"
            f"Issuer relationships: {self.issuer_relationship}"
        )

    def render(self, validator: Optional[OutputValidator] = None,
               allow_warnings: bool = True) -> str:
        """
        Assemble the publication. Raises ComplianceError if a disclosure is
        missing or the body personalises.

        allow_warnings=False turns WARN findings into blockers — use it in CI
        so nobody merges a draft nobody read.
        """
        self.validate()
        position = self.resolve_position()      # live lookup happens here
        validator = validator or OutputValidator()
        report = validator.check(self.body)
        report.raise_if_blocked()
        if not allow_warnings and report.warnings:
            lines = "\n  ".join(str(f) for f in report.warnings)
            raise ComplianceError(f"Warnings unresolved:\n  {lines}")

        rule = "-" * 72
        return (
            f"{rule}\n{self.header(position)}\n{rule}\n\n"
            f"{self.body.strip()}\n\n"
            f"{rule}\n{self.footer}\n{rule}"
        )
