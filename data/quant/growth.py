"""
growth.py — the Growth evaluation

  year_over_year = last fiscal year vs the year before (annual statements)
  forward        = this fiscal year's analyst forecast vs last fiscal year
Every metric is a % change (e.g. 50.0 = +50%).
"""

import pandas as pd

from quant_parameter_class import QuantParameter
from quant_utils import estimate, forecast_lags, growth, percent, ratio, to_number, yearly


# Math that gives "no number" when one side is missing
def plus(a, b):
    return None if a is None or b is None else a + b


def minus(a, b):
    return None if a is None or b is None else a - b


def average(a, b):
    return None if a is None or b is None else (a + b) / 2


def grow_by(value, factor):
    # Scale last year's profit by the expected growth. A loss can't be scaled
    # (a bigger loss isn't "growth"), so no number then
    return None if value is None or value <= 0 or factor is None else value * factor


class Growth(QuantParameter):
    # The growth metrics
    METRICS = [
        "revenue_growth_year_over_year",
        "revenue_growth_forward",
        "ebitda_growth_year_over_year",
        "ebitda_growth_forward",
        "ebit_growth_year_over_year",
        "ebit_growth_forward",
        "earnings_per_share_diluted_growth_year_over_year",
        "earnings_per_share_diluted_growth_forward",
        "earnings_per_share_gaap_growth_year_over_year",
        "earnings_per_share_gaap_growth_forward",
        "earnings_per_share_long_term_growth",
        "levered_free_cash_flow_growth_year_over_year",
        "free_cash_flow_per_share_growth_forward",
        "operating_cash_flow_growth_year_over_year",
        "operating_cash_flow_growth_forward",
        "return_on_equity_growth_year_over_year",
        "return_on_equity_growth_forward",
        "working_capital_growth_year_over_year",
        "capital_expenditure_growth_year_over_year",
        "dividend_per_share_growth_forward",
        "dividend_growth_rate_one_year_trailing",
    ]
    # table in the DB
    TABLE_NAME = "growth_history"

    # The constructor of the class
    def __init__(self, ticker, stock=None):
        super().__init__(ticker, stock)

        # ── Metric yfinance already gives ready-made (fraction -> %) ──
        # Analysts' yearly growth for the next 3-5 years (often missing: see calc_long_term)
        self.earnings_per_share_long_term_growth = percent(estimate(self.stock.growth_estimates, "LTG", "stockTrend"))

        # ── Raw numbers: [last fiscal year, year before] from the annual statements ──
        income  = self.stock.income_stmt
        cash    = self.stock.cashflow
        balance = self.stock.balance_sheet
        self.revenue             = yearly(income, "Total Revenue")
        self.ebitda              = yearly(income, "EBITDA")
        self.ebit                = yearly(income, "EBIT")
        self.eps_diluted         = yearly(income, "Diluted EPS")
        self.net_income          = yearly(income, "Net Income")
        self.operating_cash_flow = yearly(cash, "Operating Cash Flow")
        self.free_cash_flow      = yearly(cash, "Free Cash Flow")
        # Money spent is shown negative: keep the size of the spending
        self.capex               = [abs(v) if v is not None else None for v in yearly(cash, "Capital Expenditure")]
        # Cash returned to shareholders (shown negative): what leaves equity each year
        self.dividends_paid      = [abs(v) if v is not None else None for v in yearly(cash, "Cash Dividends Paid")]
        self.buybacks            = [abs(v) if v is not None else None for v in yearly(cash, "Repurchase Of Capital Stock")]
        self.working_capital     = yearly(balance, "Working Capital")
        self.equity              = yearly(balance, "Stockholders Equity", 3)   # 3 years: ROE uses average equity
        self.last_fiscal_year_end = max(income.columns) if income is not None and not income.empty else None

        self.dividend_rate_fwd   = to_number(self.info.get("dividendRate"))   # next 12 months, per share

        # ── Metrics we calculate ourselves ──
        self.calc_forecasts()
        self.calc_year_over_year()
        self.calc_return_on_equity()
        self.calc_forward()
        self.calc_long_term()
        self.calc_dividends()

    def calc_forecasts(self):
        # Yahoo's "this year" forecast (0y) should start from our last reported year,
        # but it can lag for a few weeks after a fiscal year closes (see forecast_lags)
        eps_est = self.stock.earnings_estimate
        revenue_est = self.stock.revenue_estimate

        if not forecast_lags(revenue_est, self.stock.income_stmt):
            # Ready-made: Yahoo's growth of this year's forecast vs last year (fraction -> %)
            self.revenue_growth_forward = percent(estimate(revenue_est, "0y", "growth"))
            self.earnings_per_share_diluted_growth_forward = percent(estimate(eps_est, "0y", "growth"))
            self.eps_nongaap_fwd       = estimate(eps_est, "0y")                 # this fiscal year
            self.eps_nongaap_last_year = estimate(eps_est, "0y", "yearAgoEps")   # last fiscal year, actual
            self.eps_nongaap_next      = estimate(eps_est, "+1y")                # next fiscal year
        else:
            # Lagging: Yahoo's "next year" (+1y) is really this year. Compare it with
            # last year's actual: revenue from the statements, adjusted EPS = the 4 quarters just reported
            history = self.stock.earnings_history
            actual = history["epsActual"].dropna() if history is not None and not history.empty else []
            self.eps_nongaap_fwd       = estimate(eps_est, "+1y")
            self.eps_nongaap_last_year = float(actual.sort_index().tail(4).sum()) if len(actual) >= 4 else None
            self.eps_nongaap_next      = None   # Yahoo has no forecast further out
            self.revenue_growth_forward = growth(estimate(revenue_est, "+1y"), self.revenue[0])
            self.earnings_per_share_diluted_growth_forward = growth(self.eps_nongaap_fwd, self.eps_nongaap_last_year)

    def calc_year_over_year(self):
        # Last fiscal year vs the year before
        self.revenue_growth_year_over_year     = growth(self.revenue[0], self.revenue[1])
        self.ebitda_growth_year_over_year      = growth(self.ebitda[0], self.ebitda[1])
        self.ebit_growth_year_over_year        = growth(self.ebit[0], self.ebit[1])
        # Yahoo keeps no history of adjusted EPS: both use diluted GAAP EPS
        self.earnings_per_share_diluted_growth_year_over_year = growth(self.eps_diluted[0], self.eps_diluted[1])
        self.earnings_per_share_gaap_growth_year_over_year    = self.earnings_per_share_diluted_growth_year_over_year
        # Free cash flow = operating cash flow - capex (SA's "levered" version also removes interest)
        self.levered_free_cash_flow_growth_year_over_year = growth(self.free_cash_flow[0], self.free_cash_flow[1])
        self.operating_cash_flow_growth_year_over_year    = growth(self.operating_cash_flow[0], self.operating_cash_flow[1])
        self.working_capital_growth_year_over_year        = growth(self.working_capital[0], self.working_capital[1])
        self.capital_expenditure_growth_year_over_year    = growth(self.capex[0], self.capex[1])

    def calc_return_on_equity(self):
        # ROE = net income / average equity of the year (start + end) / 2
        self.roe_last_year = ratio(self.net_income[0], average(self.equity[0], self.equity[1]))
        roe_year_before    = ratio(self.net_income[1], average(self.equity[1], self.equity[2]))
        self.return_on_equity_growth_year_over_year = growth(self.roe_last_year, roe_year_before)

    def calc_forward(self):
        # Yahoo only forecasts revenue and EPS: the others are estimated from the
        # expected EPS growth (e.g. 2.3 = profit x2.3 this year)
        factor = ratio(self.eps_nongaap_fwd, self.eps_nongaap_last_year)

        # GAAP EPS assumed to grow like adjusted EPS
        eps_gaap_fwd = grow_by(self.eps_diluted[0], factor)
        self.earnings_per_share_gaap_growth_forward = growth(eps_gaap_fwd, self.eps_diluted[0])

        # Operating profit grows with EPS; depreciation (EBITDA - EBIT) stays at last year's level
        ebit_fwd     = grow_by(self.ebit[0], factor)
        depreciation = minus(self.ebitda[0], self.ebit[0])
        self.ebit_growth_forward   = growth(ebit_fwd, self.ebit[0])
        self.ebitda_growth_forward = growth(plus(ebit_fwd, depreciation), self.ebitda[0])

        # Cash flow rises by the extra profit; capex stays at last year's level
        net_income_fwd = grow_by(self.net_income[0], factor)
        extra_profit   = minus(net_income_fwd, self.net_income[0])
        cash_flow_fwd  = plus(self.operating_cash_flow[0], extra_profit)
        self.operating_cash_flow_growth_forward = growth(cash_flow_fwd, self.operating_cash_flow[0])
        # Same number of shares both years, so per-share growth = total growth
        self.free_cash_flow_per_share_growth_forward = growth(minus(cash_flow_fwd, self.capex[0]), self.free_cash_flow[0])

        # ROE this year: forecast profit / average of today's equity and the equity at year end
        # (equity grows by the profit kept: profit - dividends - buybacks, at last year's level)
        paid_out = (self.dividends_paid[0] or 0) + (self.buybacks[0] or 0)
        equity_end = plus(self.equity[0], minus(net_income_fwd, paid_out))
        roe_fwd = ratio(net_income_fwd, average(self.equity[0], equity_end))
        self.return_on_equity_growth_forward = growth(roe_fwd, self.roe_last_year)

    def calc_long_term(self):
        # No long-term forecast from Yahoo: use the yearly EPS growth from last
        # year's actual to next year's forecast (2 years)
        if self.earnings_per_share_long_term_growth is None:
            two_years = ratio(self.eps_nongaap_next, self.eps_nongaap_last_year)
            self.earnings_per_share_long_term_growth = (two_years ** 0.5 - 1) * 100 if two_years else None

    def calc_dividends(self):
        self.dividend_growth_rate_one_year_trailing = None
        self.dividend_per_share_growth_forward = None
        dividends = self.stock.dividends
        if dividends is None or dividends.empty:
            return   # no dividends: nothing to grow

        # Dividends paid in the last 12 months vs the 12 months before
        one_year = pd.Timedelta(days=365)
        now = pd.Timestamp.now(tz=dividends.index.tz)
        last_12m   = dividends[dividends.index > now - one_year].sum()
        before_12m = dividends[(dividends.index > now - 2 * one_year) & (dividends.index <= now - one_year)].sum()
        self.dividend_growth_rate_one_year_trailing = growth(float(last_12m), float(before_12m))

        # Next 12 months' dividend rate vs what was paid during the last fiscal year
        if self.last_fiscal_year_end is not None:
            fy_end = pd.Timestamp(self.last_fiscal_year_end).tz_localize(dividends.index.tz)
            paid_last_fy = dividends[(dividends.index > fy_end - one_year) & (dividends.index <= fy_end)].sum()
            self.dividend_per_share_growth_forward = growth(self.dividend_rate_fwd, float(paid_last_fy))

    def get_metrics(self):
        # All 21 metrics as {name: value}
        return {name: getattr(self, name) for name in self.METRICS}
