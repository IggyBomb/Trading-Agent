"""
test_market_outlook.py

    python -m pytest test_market_outlook.py -q
    python test_market_outlook.py

Regression tests for the weekly market/sector review publication type. Mirrors
test_compliance_guard.py's Publication tests, adapted for the multi-instrument
`positions` list this type uses instead of a single `position_disclosure`.
"""

import pytest

from compliance_guard import ComplianceError
from market_outlook import MarketOutlookPublication


def _complete(**overrides) -> MarketOutlookPublication:
    kwargs = dict(
        producer="Example Research Ltd, Dublin",
        author="A. Analyst",
        period="Week of 2026-09-04",
        regime="REFLATION — mid cycle, HIGH confidence",
        sources=["Example sentiment/macro/sector pipeline, data as of 2026-09-04"],
        positions=[
            "XLE: The author holds no position in XLE as at the date of production.",
            "XLF: The author holds no position in XLF as at the date of production.",
        ],
        body=(
            "Energy and Financials led on 5-day momentum while Technology and "
            "Industrials lagged. That split is consistent with a reflationary "
            "read. Below a return to Technology leadership, the regime call "
            "would need restating."
        ),
    )
    kwargs.update(overrides)
    return MarketOutlookPublication(**kwargs)


def test_complete_outlook_renders():
    out = _complete().render()
    assert "Producer:" in out
    assert "Coverage:" in out
    assert "Regime read:" in out
    assert "Positions (every instrument named with a lean below):" in out
    assert "XLE" in out and "XLF" in out
    assert "not a personal recommendation" in out          # shares the MAR footer


@pytest.mark.parametrize("field", ["period", "regime", "body", "producer", "author"])
def test_missing_field_blocks_render(field):
    pub = _complete(**{field: ""})
    with pytest.raises(ComplianceError) as exc:
        pub.render()
    assert field in str(exc.value)


def test_missing_sources_blocks_render():
    with pytest.raises(ComplianceError) as exc:
        _complete(sources=[]).render()
    assert "sources" in str(exc.value)


def test_missing_positions_blocks_render():
    with pytest.raises(ComplianceError) as exc:
        _complete(positions=[]).render()
    assert "positions" in str(exc.value)


def test_blank_resolved_position_blocks_render():
    pub = _complete(positions=["XLE: ...", lambda: "  "])
    with pytest.raises(ComplianceError):
        pub.render()


def test_callable_position_resolved_at_render_time():
    calls = []

    def loader():
        calls.append(1)
        return "XLE: The author holds no position in XLE as at the date of production."

    pub = _complete(positions=[loader])
    out = pub.render()
    assert calls == [1]
    assert "XLE" in out


def test_personalised_body_blocks_render():
    pub = _complete(body="Your portfolio is heavy on Financials, so rotate now.")
    with pytest.raises(ComplianceError):
        pub.render()


def test_strict_mode_blocks_on_warnings():
    pub = _complete(body="Buy the rotation into Financials while it lasts.")
    pub.render(allow_warnings=True)                        # passes
    with pytest.raises(ComplianceError):
        pub.render(allow_warnings=False)                   # CI mode


def test_no_rating_or_isin_fields_exist():
    # A market outlook is not a single-instrument thesis in disguise — it must
    # not accept the fields that imply one.
    pub = _complete()
    assert not hasattr(pub, "rating")
    assert not hasattr(pub, "isin")
    assert not hasattr(pub, "price_target")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
