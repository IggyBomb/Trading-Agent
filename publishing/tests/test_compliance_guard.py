"""
test_compliance_guard.py

    python -m pytest test_compliance_guard.py -q
    python test_compliance_guard.py          # no pytest needed

These are the regression tests for the line. If you loosen a rule, a test here
should be the thing that argues with you about it.
"""

import pytest

from compliance_guard import (
    ComplianceError,
    InputGate,
    OutputValidator,
    Publication,
    Severity,
)


# ---------------------------------------------------------------------------
# Input gate
# ---------------------------------------------------------------------------

REFUSE = [
    "Should I buy this?",
    "should we add here",
    "What should I do with it?",
    "How much should I put in?",
    "Does this fit my portfolio?",
    "Given my holdings, is this a good idea?",
    "Is this suitable for me?",
    "In my situation would you buy?",
    "Can I afford to double up?",
    "Does this suit my risk tolerance?",
    "Can you size this for me?",
    "I hold 400 shares — do I add?",
    "I'm long already, what now?",
    "With my €20,000 what would you do?",
    "Help me rebalance my book",
]

ALLOW = [
    "What is the valuation methodology behind the target?",
    "What did you publish on this name last quarter?",
    "What is the current rating and horizon?",
    "Why did the rating change in May?",
    "What are the sources for the CET1 figure?",
    "Should the market be pricing sovereign risk here?",   # not directed at the reader
]


@pytest.mark.parametrize("q", REFUSE)
def test_gate_refuses_personalised_questions(q):
    verdict = InputGate().check(q)
    assert not verdict.allowed, f"gate let through: {q!r}"
    assert verdict.reply


@pytest.mark.parametrize("q", ALLOW)
def test_gate_allows_content_questions(q):
    verdict = InputGate().check(q)
    assert verdict.allowed, f"gate refused a fair question: {q!r}"


# ---------------------------------------------------------------------------
# Output validator
# ---------------------------------------------------------------------------

MUST_BLOCK = [
    "At these levels I'd start a position.",
    "I would buy here.",
    "My call: build in tranches.",
    "You should wait for the pullback.",
    "You must not chase this.",
    "Your portfolio is already heavy on banks.",
    "Your position is underwater, which changes the maths.",
    "Your own system's sizing rule says normal.",
    "This is suitable for you if the horizon is long.",
    "Given your exposure, trim into strength.",
    "Risk 2% here and no more.",
    "Position sizing should stay conservative.",
    "Max 2% of portfolio on this one.",
    "Allocate 5% and leave room to add.",
    "Here is how much to buy at these levels.",
]

MUST_PASS = [
    "The stock trades at 0.7x tangible book against guidance for ROTE above 11%.",
    "Below EUR 65 the thesis breaks and would need restating.",
    "Q2 was a record quarter; CET1 finished at 13.2%.",
    "The OAT-Bund spread remains the transmission channel for French sovereign risk.",
    "Consensus has the 2027 exit multiple at 7.5x earnings.",
]


@pytest.mark.parametrize("text", MUST_BLOCK)
def test_validator_blocks_personalisation(text):
    report = OutputValidator().check(text)
    assert report.blocking, f"validator missed: {text!r}"
    assert not report.clean


@pytest.mark.parametrize("text", MUST_PASS)
def test_validator_passes_instrument_language(text):
    report = OutputValidator().check(text)
    assert report.clean, (
        f"false positive on: {text!r} → "
        + "; ".join(f.rule_id for f in report.blocking)
    )


def test_second_person_warns_but_does_not_block():
    report = OutputValidator().check("You may recall the Q2 print was strong.")
    assert report.clean                       # not a blocker
    assert any(f.rule_id == "OUT-25" for f in report.warnings)


def test_bare_disclaimer_is_flagged():
    report = OutputValidator().check("This is not financial advice, just my view.")
    assert any(f.rule_id == "OUT-24" for f in report.warnings)


def test_raise_if_blocked():
    report = OutputValidator().check("You should buy this now.")
    with pytest.raises(ComplianceError):
        report.raise_if_blocked()


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def _complete(**overrides) -> Publication:
    kwargs = dict(
        producer="Example Research Ltd, Dublin",
        author="A. Analyst",
        instrument="Example SA (EXA FP)",
        isin="FR0000000000",
        rating="BUY",
        price_target="EUR 88",
        horizon="12 months",
        price_at_production="EUR 74.20",
        previous="none",
        valuation_basis="0.9x tangible book on 2027E TBVPS of EUR 98. ROTE 11.5%.",
        sources=["Q2 2026 results, 30 July 2026"],
        position_disclosure="The author holds no position as at production.",
        body="The stock trades at 0.7x tangible book. Below EUR 65 the thesis breaks.",
    )
    kwargs.update(overrides)
    return Publication(**kwargs)


def test_complete_publication_renders():
    out = _complete().render()
    assert "Producer:" in out
    assert "Positions:" in out
    assert "Rating definitions:" in out
    assert "not a personal recommendation" in out


@pytest.mark.parametrize("field", [
    "position_disclosure", "previous", "valuation_basis", "isin", "body",
])
def test_missing_disclosure_blocks_render(field):
    pub = _complete(**{field: ""})
    with pytest.raises(ComplianceError) as exc:
        pub.render()
    assert field in str(exc.value)


def test_missing_sources_blocks_render():
    with pytest.raises(ComplianceError) as exc:
        _complete(sources=[]).render()
    assert "sources" in str(exc.value)


def test_undefined_rating_blocks_render():
    with pytest.raises(ComplianceError) as exc:
        _complete(rating="STRONG BUY").render()
    assert "not one of the published definitions" in str(exc.value)


def test_personalised_body_blocks_render():
    pub = _complete(body="Your portfolio is heavy on banks, so trim here.")
    with pytest.raises(ComplianceError):
        pub.render()


def test_strict_mode_blocks_on_warnings():
    pub = _complete(body="Buy the dip. The stock trades at 0.7x tangible book.")
    pub.render(allow_warnings=True)                     # passes
    with pytest.raises(ComplianceError):
        pub.render(allow_warnings=False)                # CI mode


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
