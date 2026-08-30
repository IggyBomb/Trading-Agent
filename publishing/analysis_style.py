"""
analysis_style.py — the one place the output-writing rules live.

Every agent that produces analysis text imports from here: the pipeline, and
each standalone agent. One file, one set of rules, no drift between them.

The short version for a human
-----------------------------
Write about the instrument, never about the reader. That is the whole rule.
Everything in ANALYSIS_RULES below is a consequence of it.

Using it — one line per agent
-----------------------------
    from analysis_style import draft

    body = draft(my_llm, "Analyse GLE.PA following the Q2 results")

`draft()` applies the rules, checks the result, asks for one rewrite if the
model slipped, and raises if it still personalises. An agent cannot use the
rules without also getting the check, which is the point: a prompt on its own
enforces nothing.

If you need the pieces separately:

    system = system_prompt(MY_AGENT_PROMPT)   # rules + your own instructions
    text   = enforce(some_draft)              # raises if it personalises

Stdlib only.
"""

from __future__ import annotations

from typing import Callable, Optional

from compliance_guard import (
    ComplianceError,
    OutputValidator,
    Report,
    DEFAULT_RATING_DEFINITIONS,
)

__all__ = [
    "ANALYSIS_RULES",
    "RATING_DEFINITIONS",
    "REQUIRED_DISCLOSURES",
    "system_prompt",
    "check",
    "enforce",
    "repair_instruction",
    "draft",
]

RATING_DEFINITIONS = DEFAULT_RATING_DEFINITIONS

REQUIRED_DISCLOSURES = (
    "producer identity", "production and dissemination timestamps",
    "instrument and ISIN", "rating", "previous rating and date (or 'none')",
    "price target", "time horizon", "price at production",
    "valuation methodology and its assumptions", "rating definitions",
    "sources", "position disclosure",
)


ANALYSIS_RULES = f"""\
# Output rules — general investment research

You produce general investment research for publication to a subscriber list.
Every subscriber receives identical content at the same time. You are not
advising anyone and you know nothing about who is reading.

## The governing rule

Write about the instrument, never about the reader.

## Never

- Address the reader's portfolio, holdings, account, capital or exposure.
- State or imply a position size, in percent, currency or any other unit.
- Say what the reader should, must or ought to do.
- Say what you would do ("I'd start a position", "my call is...").
- Describe anything as suitable, appropriate or right for the reader.
- Condition a view on the reader's circumstances ("given your...", "if you hold...").
- Refer to the reader's own system, rules, strategy or risk tolerance.
- Lay out an execution plan — tranches, entries, adds, scaling.
- Append "not financial advice" to text that reads as advice. Fix the text.

## Instead

| Instead of | Write |
|---|---|
| "I'd start a position here" | "The setup implies X" — then rating, target, horizon |
| "Size this at 2% max" | Nothing. Sizing belongs to the reader. Omit it |
| "Buy a first tranche, add at 65" | "65 is where the thesis breaks" |
| "My call: build in tranches" | "Rating: BUY. Target 88. Horizon 12 months." |
| "This suits you if your horizon is long" | "The thesis depends on X holding" |

Second person is not banned outright — "you may recall the Q2 print" is fine.
It is banned wherever it refers to the reader's money, holdings or decisions.
When in doubt, rewrite in the third person about the instrument.

## Ratings are fixed

{RATING_DEFINITIONS}

Use only these. An improvised or undefined rating is not objective presentation.

## Fact and opinion are separated

Sourced figures are fact and must be attributable to a listed source. Targets,
forecasts and ratings are opinion and estimate, and must read that way. Never
present an estimate as a reported figure, and never invent a source, a number
or a methodology to fill a gap — say the input is unavailable and stop.

## Position management data stays internal

Stop levels, planned R:R, conviction scores and position percentages are
internal risk management. They never appear in published text. A
thesis-invalidation level is acceptable because it describes the instrument
("below 65 the thesis breaks"); a stop-loss instruction is not, because it
describes what someone should do.

## Questions you must refuse

Anything answerable only by reference to the asker's own situation — "should I
buy", "how much should I put in", "does this fit my portfolio", "I hold X, what
now". Do not answer, do not answer "in general terms" as a workaround, and do
not answer with a caveat attached. A hedged personal recommendation is still a
personal recommendation.
"""


# ---------------------------------------------------------------------------

_validator = OutputValidator()


def system_prompt(base: str = "") -> str:
    """
    The rules, followed by the agent's own instructions.

    The rules go first so that anything the agent-specific prompt says about
    tone or format is read in their light, not the other way round.
    """
    base = (base or "").strip()
    return f"{ANALYSIS_RULES}\n\n---\n\n{base}" if base else ANALYSIS_RULES


def check(text: str) -> Report:
    """Scan a draft. Returns a Report; does not raise."""
    return _validator.check(text)


def enforce(text: str) -> str:
    """Return the text if it is clean, otherwise raise ComplianceError."""
    check(text).raise_if_blocked()
    return text


def repair_instruction(text: str, report: Report) -> str:
    """The rewrite request sent back to the model after a failed check."""
    findings = "\n".join(
        f'- {f.rule_id}: {f.message} — "{f.excerpt}"' for f in report.blocking
    )
    return (
        "Rewrite the draft below. The passages listed address the reader rather "
        "than the instrument and must be removed or recast. Do not add a "
        "disclaimer and do not soften them — fix the text. Keep everything else "
        "as it is.\n\n"
        f"{findings}\n\n---\n{text}"
    )


def draft(
    generate: Callable[..., str],
    instruction: str,
    *,
    base_prompt: str = "",
    attempts: int = 2,
    on_warning: Optional[Callable[[Report], None]] = None,
) -> str:
    """
    Produce analysis text that has passed the rules.

    `generate` is your own model call. It must accept `system` and `user`
    keyword arguments and return a string:

        def my_llm(system: str, user: str) -> str: ...

    `attempts` counts total tries: 2 means one draft plus one rewrite. Raising
    it above 3 rarely helps — a draft that fails three times is usually failing
    on substance, not phrasing, and wants a human.

    `on_warning` receives the final report if there are warnings but no
    blockers. Use it to log; warnings are for a human to read, not to ignore.

    Raises ComplianceError if the text still personalises after the last try.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    system = system_prompt(base_prompt)
    user = instruction
    text = ""

    for attempt in range(1, attempts + 1):
        text = generate(system=system, user=user)
        report = check(text)

        if report.clean:
            if report.warnings and on_warning is not None:
                on_warning(report)
            return text

        if attempt == attempts:
            raise ComplianceError(
                f"Draft still personalises after {attempts} attempt(s):\n  "
                + "\n  ".join(str(f) for f in report.blocking)
            )

        user = repair_instruction(text, report)

    return text  # unreachable
