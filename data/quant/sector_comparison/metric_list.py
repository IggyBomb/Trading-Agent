"""
metric_list.py — which metrics the sector comparison scores, and how: the pillar each one
counts towards, whether a lower or a higher value is better, and how its value is cleaned
before comparing. Adding a row here makes a metric part of the comparison; nothing else changes.

Directions and cleaning rules follow the "Compare (quant)" sheet of Sector_Benchmarks_quant.xlsx
(its "Better" column and the Constituents formulas). in_sheet = True marks the metrics that
sheet compares, so their Python results can be checked against it; the others are scored from
quant.db only.

Usage:
    from metric_list import METRICS
    for metric in METRICS:
        value = card.value(metric.category, metric.name)
"""

from dataclasses import dataclass

# Which direction is better
LOWER, HIGHER = "lower", "higher"

# Cleaning rules applied to the ticker's value and its peers' before comparing
POSITIVE_ONLY = "positive_only"   # a value <= 0 is not meaningful (NM): loss, negative EBITDA / book / cash flow
NO_RULE = None                    # the value is used as it is (a negative growth or margin is real)


@dataclass(frozen=True)
class Metric:
    name: str        # our name, as in quant.db and on the TickerCard
    category: str    # pillar it counts towards: "valuation", "growth", "profitability", "momentum", "revisions"
    better: str      # LOWER or HIGHER
    rule: str        # POSITIVE_ONLY or NO_RULE
    label: str       # readable name for reports (the sheet's name where it has one)
    in_sheet: bool   # True if Compare (quant) compares it (result can be checked against the sheet)


# ── Valuation (evaluation.py, 19) ──
# Every multiple: lower is better, and <= 0 is NM. Dividend yield is the exception.
VALUATION = [
    Metric("price_to_earnings_non_gaap_trailing",       "valuation", LOWER,  POSITIVE_ONLY, "P/E non-GAAP TTM",   True),
    Metric("price_to_earnings_non_gaap_forward",        "valuation", LOWER,  POSITIVE_ONLY, "P/E non-GAAP FWD",   False),
    Metric("price_to_earnings_gaap_trailing",           "valuation", LOWER,  POSITIVE_ONLY, "P/E GAAP TTM",       False),
    Metric("price_to_earnings_gaap_forward",            "valuation", LOWER,  POSITIVE_ONLY, "P/E GAAP FWD",       True),
    Metric("price_earnings_to_growth_gaap_trailing",    "valuation", LOWER,  POSITIVE_ONLY, "PEG GAAP TTM",       False),
    Metric("price_earnings_to_growth_non_gaap_forward", "valuation", LOWER,  POSITIVE_ONLY, "PEG non-GAAP FWD",   True),
    Metric("enterprise_value_to_sales_trailing",        "valuation", LOWER,  POSITIVE_ONLY, "EV/Sales TTM",       False),
    Metric("enterprise_value_to_sales_forward",         "valuation", LOWER,  POSITIVE_ONLY, "EV/Sales FWD",       True),
    Metric("enterprise_value_to_ebitda_trailing",       "valuation", LOWER,  POSITIVE_ONLY, "EV/EBITDA TTM",      False),
    Metric("enterprise_value_to_ebitda_forward",        "valuation", LOWER,  POSITIVE_ONLY, "EV/EBITDA FWD",      True),
    Metric("enterprise_value_to_ebit_trailing",         "valuation", LOWER,  POSITIVE_ONLY, "EV/EBIT TTM",        True),
    Metric("enterprise_value_to_ebit_forward",          "valuation", LOWER,  POSITIVE_ONLY, "EV/EBIT FWD",        True),
    Metric("price_to_sales_trailing",                   "valuation", LOWER,  POSITIVE_ONLY, "P/Sales TTM",        False),
    Metric("price_to_sales_forward",                    "valuation", LOWER,  POSITIVE_ONLY, "P/Sales FWD",        True),
    Metric("price_to_book_trailing",                    "valuation", LOWER,  POSITIVE_ONLY, "P/B TTM",            False),
    Metric("price_to_book_forward",                     "valuation", LOWER,  POSITIVE_ONLY, "P/B FWD",            True),
    Metric("price_to_cash_flow_trailing",               "valuation", LOWER,  POSITIVE_ONLY, "P/Cash Flow TTM",    False),
    Metric("price_to_cash_flow_forward",                "valuation", LOWER,  POSITIVE_ONLY, "P/Cash Flow FWD",    True),
    Metric("dividend_yield_trailing",                   "valuation", HIGHER, NO_RULE,       "Dividend yield TTM", True),
]

# ── Growth (growth.py, 20 of 21) ──
# Faster growth is better; a negative growth is a real decline, so no cleaning.
GROWTH = [
    Metric("revenue_growth_year_over_year",                    "growth", HIGHER, NO_RULE, "Revenue growth YoY",         False),
    Metric("revenue_growth_forward",                           "growth", HIGHER, NO_RULE, "Revenue growth FWD",         True),
    Metric("ebitda_growth_year_over_year",                     "growth", HIGHER, NO_RULE, "EBITDA growth YoY",          True),
    Metric("ebitda_growth_forward",                            "growth", HIGHER, NO_RULE, "EBITDA growth FWD",          True),
    Metric("ebit_growth_year_over_year",                       "growth", HIGHER, NO_RULE, "EBIT growth YoY",            True),
    Metric("ebit_growth_forward",                              "growth", HIGHER, NO_RULE, "EBIT growth FWD",            True),
    Metric("earnings_per_share_diluted_growth_year_over_year", "growth", HIGHER, NO_RULE, "EPS diluted growth YoY",     False),
    Metric("earnings_per_share_diluted_growth_forward",        "growth", HIGHER, NO_RULE, "EPS diluted growth FWD",     False),
    # Left out: earnings_per_share_gaap_growth_year_over_year is the same number as
    # EPS diluted growth YoY in our data (both GAAP diluted EPS); scoring both would count it twice.
    Metric("earnings_per_share_gaap_growth_forward",           "growth", HIGHER, NO_RULE, "EPS GAAP growth FWD",        True),
    Metric("earnings_per_share_long_term_growth",              "growth", HIGHER, NO_RULE, "EPS long-term growth",       True),
    Metric("levered_free_cash_flow_growth_year_over_year",     "growth", HIGHER, NO_RULE, "Levered FCF growth YoY",     True),
    Metric("free_cash_flow_per_share_growth_forward",          "growth", HIGHER, NO_RULE, "FCF/share growth FWD",       True),
    Metric("operating_cash_flow_growth_year_over_year",        "growth", HIGHER, NO_RULE, "OCF growth YoY",             True),
    Metric("operating_cash_flow_growth_forward",               "growth", HIGHER, NO_RULE, "OCF growth FWD",             True),
    Metric("return_on_equity_growth_year_over_year",           "growth", HIGHER, NO_RULE, "ROE growth YoY",             True),
    Metric("return_on_equity_growth_forward",                  "growth", HIGHER, NO_RULE, "ROE growth FWD",             True),
    Metric("working_capital_growth_year_over_year",            "growth", HIGHER, NO_RULE, "Working capital growth YoY", True),
    Metric("capital_expenditure_growth_year_over_year",        "growth", HIGHER, NO_RULE, "Capex growth YoY",           True),
    Metric("dividend_per_share_growth_forward",                "growth", HIGHER, NO_RULE, "DPS growth FWD",             True),
    Metric("dividend_growth_rate_one_year_trailing",           "growth", HIGHER, NO_RULE, "Dividend growth 1Y TTM",     True),
]

# ── Profitability (profitability.py, 13) ──
# Higher margins and returns are better; Capex / Sales is the exception (less spending per sale).
PROFITABILITY = [
    Metric("gross_profit_margin_trailing",           "profitability", HIGHER, NO_RULE, "Gross margin TTM",            True),
    Metric("ebit_margin_trailing",                   "profitability", HIGHER, NO_RULE, "EBIT margin TTM",             True),
    Metric("ebitda_margin_trailing",                 "profitability", HIGHER, NO_RULE, "EBITDA margin TTM",           False),
    Metric("net_income_margin_trailing",             "profitability", HIGHER, NO_RULE, "Net income margin TTM",       False),
    Metric("levered_free_cash_flow_margin_trailing", "profitability", HIGHER, NO_RULE, "Levered FCF margin TTM",      False),
    Metric("return_on_common_equity_trailing",       "profitability", HIGHER, NO_RULE, "Return on equity TTM",        False),
    Metric("return_on_total_capital_trailing",       "profitability", HIGHER, NO_RULE, "Return on total capital TTM", True),
    Metric("return_on_total_assets_trailing",        "profitability", HIGHER, NO_RULE, "Return on assets TTM",        True),
    Metric("capital_expenditure_to_sales_trailing",  "profitability", LOWER,  NO_RULE, "Capex / Sales TTM",           True),
    Metric("asset_turnover_ratio_trailing",          "profitability", HIGHER, NO_RULE, "Asset turnover TTM",          True),
    Metric("cash_from_operations_trailing",          "profitability", HIGHER, NO_RULE, "Cash from operations TTM",    True),
    Metric("cash_per_share_trailing",                "profitability", HIGHER, NO_RULE, "Cash per share TTM",          True),
    Metric("net_income_per_employee_trailing",       "profitability", HIGHER, NO_RULE, "Net income per employee TTM", True),
]

# ── Momentum (momentum.py, 4) ──
MOMENTUM = [
    Metric("price_performance_three_months", "momentum", HIGHER, NO_RULE, "Price change 3M",  True),
    Metric("price_performance_six_months",   "momentum", HIGHER, NO_RULE, "Price change 6M",  True),
    Metric("price_performance_nine_months",  "momentum", HIGHER, NO_RULE, "Price change 9M",  True),
    Metric("price_performance_one_year",     "momentum", HIGHER, NO_RULE, "Price change 12M", True),
]

# ── Revisions (revisions.py, 12 of 22) ──
# How much analysts changed their forecast: raised estimates are better. A cut is a real
# negative change, so no cleaning.
# The revenue changes and the 6-month EPS changes come from quant.db's own saved forecasts:
# they stay empty (NM) until the weekly run has 1, 3 and 6 months of history (from 2026-11-06).
# Left out: the fiscal-year labels, the raw EPS / revenue estimates (amounts) and the revision
# counts (depend on how many analysts cover the stock) - not comparable across companies.
REVISIONS = [
    Metric("earnings_per_share_estimate_change_one_month_current_year",    "revisions", HIGHER, NO_RULE, "EPS estimate change 1M, this FY",     False),
    Metric("earnings_per_share_estimate_change_three_months_current_year", "revisions", HIGHER, NO_RULE, "EPS estimate change 3M, this FY",     False),
    Metric("earnings_per_share_estimate_change_six_months_current_year",   "revisions", HIGHER, NO_RULE, "EPS estimate change 6M, this FY",     False),
    Metric("earnings_per_share_estimate_change_one_month_next_year",       "revisions", HIGHER, NO_RULE, "EPS estimate change 1M, next FY",     False),
    Metric("earnings_per_share_estimate_change_three_months_next_year",    "revisions", HIGHER, NO_RULE, "EPS estimate change 3M, next FY",     False),
    Metric("earnings_per_share_estimate_change_six_months_next_year",      "revisions", HIGHER, NO_RULE, "EPS estimate change 6M, next FY",     False),
    Metric("revenue_estimate_change_one_month_current_year",               "revisions", HIGHER, NO_RULE, "Revenue estimate change 1M, this FY", False),
    Metric("revenue_estimate_change_three_months_current_year",            "revisions", HIGHER, NO_RULE, "Revenue estimate change 3M, this FY", False),
    Metric("revenue_estimate_change_six_months_current_year",              "revisions", HIGHER, NO_RULE, "Revenue estimate change 6M, this FY", False),
    Metric("revenue_estimate_change_one_month_next_year",                  "revisions", HIGHER, NO_RULE, "Revenue estimate change 1M, next FY", False),
    Metric("revenue_estimate_change_three_months_next_year",               "revisions", HIGHER, NO_RULE, "Revenue estimate change 3M, next FY", False),
    Metric("revenue_estimate_change_six_months_next_year",                 "revisions", HIGHER, NO_RULE, "Revenue estimate change 6M, next FY", False),
]

# Everything the comparison loops over
METRICS = VALUATION + GROWTH + PROFITABILITY + MOMENTUM + REVISIONS
