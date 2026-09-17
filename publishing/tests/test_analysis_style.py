"""
test_analysis_style.py

    python -m pytest test_analysis_style.py -q

The point of analysis_style is that an agent cannot take the rules without also
taking the check. These tests hold that.
"""

import pytest

from compliance_guard import ComplianceError
from analysis_style import (
    ANALYSIS_RULES,
    check,
    draft,
    enforce,
    repair_instruction,
    system_prompt,
)

GOOD = "The shares trade at 0.7x tangible book. Below EUR 65 the thesis breaks."
BAD = "At these levels I'd start a position. Size it at max 2% of portfolio."


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

def test_rules_come_first():
    out = system_prompt("Focus on European banks.")
    assert out.startswith("# Output rules")
    assert out.index("Output rules") < out.index("Focus on European banks")


def test_empty_base_returns_rules_alone():
    assert system_prompt() == ANALYSIS_RULES
    assert system_prompt("   ") == ANALYSIS_RULES


def test_rules_carry_the_rating_definitions():
    assert "BUY = expected total return above 15%" in ANALYSIS_RULES


# ---------------------------------------------------------------------------
# check / enforce
# ---------------------------------------------------------------------------

def test_enforce_passes_clean_text():
    assert enforce(GOOD) == GOOD


def test_enforce_raises_on_personalisation():
    with pytest.raises(ComplianceError):
        enforce(BAD)


def test_check_does_not_raise():
    report = check(BAD)
    assert not report.clean
    assert report.blocking


# ---------------------------------------------------------------------------
# draft()
# ---------------------------------------------------------------------------

def test_draft_returns_a_clean_first_attempt():
    calls = []

    def gen(system, user):
        calls.append(user)
        return GOOD

    assert draft(gen, "Analyse GLE") == GOOD
    assert len(calls) == 1


def test_draft_repairs_a_bad_first_attempt():
    outputs = iter([BAD, GOOD])
    seen = []

    def gen(system, user):
        seen.append(user)
        return next(outputs)

    assert draft(gen, "Analyse GLE") == GOOD
    assert len(seen) == 2
    assert "Rewrite the draft below" in seen[1]
    assert "OUT-03" in seen[1] or "OUT-09" in seen[1]


def test_draft_raises_when_repair_also_fails():
    def gen(system, user):
        return BAD

    with pytest.raises(ComplianceError) as exc:
        draft(gen, "Analyse GLE")
    assert "still personalises after 2 attempt" in str(exc.value)


def test_draft_respects_attempt_count():
    tries = []

    def gen(system, user):
        tries.append(1)
        return BAD

    with pytest.raises(ComplianceError):
        draft(gen, "Analyse GLE", attempts=3)
    assert len(tries) == 3


def test_draft_passes_the_rules_as_system():
    captured = {}

    def gen(system, user):
        captured["system"] = system
        return GOOD

    draft(gen, "Analyse GLE", base_prompt="House style: terse.")
    assert "Write about the instrument, never about the reader" in captured["system"]
    assert "House style: terse." in captured["system"]


def test_warnings_are_surfaced_not_swallowed():
    seen = []

    def gen(system, user):
        return "You may recall the Q2 print. The shares trade at 0.7x book."

    out = draft(gen, "Analyse GLE", on_warning=seen.append)
    assert out
    assert seen and any(f.rule_id == "OUT-25" for f in seen[0].warnings)


def test_zero_attempts_rejected():
    with pytest.raises(ValueError):
        draft(lambda system, user: GOOD, "x", attempts=0)


def test_repair_instruction_names_the_findings():
    text = repair_instruction(BAD, check(BAD))
    assert "Rewrite the draft below" in text
    assert "Do not add a disclaimer" in text
    assert BAD in text


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
