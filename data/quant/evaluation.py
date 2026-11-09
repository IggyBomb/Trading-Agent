import pandas as pd
import logging
log = logging.getLogger("evaluation")
from quant_parameter_class import QuantParameter
from quant_utils import ratio, last4, estimate, forecast_lags, adjusted_eps_ttm


class Valuation(QuantParameter):
    # The valuation metrics
    METRICS = [
        "price_to_earnings_non_gaap_trailing",
        "price_to_earnings_non_gaap_forward",
        "price_to_earnings_gaap_trailing",
        "price_to_earnings_gaap_forward",
        "price_earnings_to_growth_gaap_trailing",
        "price_earnings_to_growth_non_gaap_forward",
        "enterprise_value_to_sales_trailing",
        "enterprise_value_to_sales_forward",
        "enterprise_value_to_ebitda_trailing",
        "enterprise_value_to_ebitda_forward",
        "enterprise_value_to_ebit_trailing",
        "enterprise_value_to_ebit_forward",
        "price_to_sales_trailing",
        "price_to_sales_forward",
        "price_to_book_trailing",
        "price_to_book_forward",
        "price_to_cash_flow_trailing",
        "price_to_cash_flow_forward",
        "dividend_yield_trailing",
    ]
    # table in the DB
    TABLE_NAME = "valuation_history"

    # The constructor of the class
    def __init__(self, ticker, stock=None):
        super().__init__(ticker, stock)

        # ── Metrics yfinance already gives ready-made ──
        self.price_to_earnings_gaap_trailing     = self.info.get("trailingPE")
        self.enterprise_value_to_sales_trailing  = self.info.get("enterpriseToRevenue")
        self.enterprise_value_to_ebitda_trailing = self.info.get("enterpriseToEbitda")
        self.price_to_sales_trailing             = self.info.get("priceToSalesTrailing12Months")
        self.price_to_book_trailing              = self.info.get("priceToBook")
        yield_ttm = self.info.get("trailingAnnualDividendYield")
        self.dividend_yield_trailing = yield_ttm * 100 if yield_ttm is not None else None   # fraction -> %

        # ── Raw numbers the other metrics are built from ──
        self.shares          = self.info.get("sharesOutstanding")
        self.market_cap       = self.info.get("marketCap")
        self.enterprise_value = self.info.get("enterpriseValue")
        self.ebitda_ttm       = self.info.get("ebitda")
        self.cash_flow_ttm    = self.info.get("operatingCashflow")
        self.eps_gaap_ttm     = self.info.get("trailingEps")
        book_per_share        = self.info.get("bookValue")
        self.book_value       = book_per_share * self.shares if book_per_share and self.shares else None
        self.ebit_ttm         = last4(self.stock.quarterly_income_stmt, "EBIT")

        # Adjusted (non-GAAP) EPS of the last 4 quarters, as reported to analysts
        self.eps_nongaap_ttm = adjusted_eps_ttm(self.stock.earnings_history)

        # Analyst forecasts for this fiscal year. If Yahoo still lags on a year just
        # closed, its "+1y" is this year and there's nothing further out
        eps_est = self.stock.earnings_estimate
        revenue_est = self.stock.revenue_estimate
        lagging = forecast_lags(revenue_est, self.stock.income_stmt)
        this_year = "+1y" if lagging else "0y"
        self.eps_nongaap_fwd  = estimate(eps_est, this_year)
        self.eps_nongaap_next = None if lagging else estimate(eps_est, "+1y")
        self.revenue_fwd      = estimate(revenue_est, this_year)

        # ── Metrics we calculate in the class ──
        self.calc_forward_inputs()
        self.calc_pe()
        self.calc_peg()
        self.calc_ev()
        self.calc_price_ratios()

    def calc_forward_inputs(self):
        # How much profit is expected to grow this year (e.g. 2.0 = doubles)
        growth = ratio(self.eps_nongaap_fwd, self.eps_nongaap_ttm)
        # Yahoo has no GAAP forecast: assume GAAP moves like adjusted EPS
        self.eps_gaap_fwd = (self.eps_nongaap_fwd * self.eps_gaap_ttm / self.eps_nongaap_ttm
                             if growth and self.eps_gaap_ttm is not None else None)
        # Operating profit grows with EPS; EBITDA = EBIT + depreciation (EBITDA - EBIT today)
        self.ebit_fwd = self.ebit_ttm * growth if growth and self.ebit_ttm is not None else None
        self.ebitda_fwd = (self.ebit_fwd + self.ebitda_ttm - self.ebit_ttm
                           if self.ebit_fwd is not None and self.ebitda_ttm is not None else None)
        # Extra profit expected this year, in total dollars
        extra_profit = ((self.eps_gaap_fwd - self.eps_gaap_ttm) * self.shares
                        if self.eps_gaap_fwd is not None and self.shares else None)
        # Next year's book = today's book + this year's profit (dividends ignored)
        self.book_value_fwd = (self.book_value + self.eps_gaap_fwd * self.shares
                               if self.book_value and self.eps_gaap_fwd is not None else None)
        # Cash flow rises with the extra profit
        self.cash_flow_fwd = (self.cash_flow_ttm + extra_profit
                              if self.cash_flow_ttm is not None and extra_profit is not None else None)

    def calc_pe(self):
        # Price / Earnings: how many years of profit you pay for
        self.price_to_earnings_non_gaap_trailing = ratio(self.price, self.eps_nongaap_ttm)
        self.price_to_earnings_non_gaap_forward  = ratio(self.price, self.eps_nongaap_fwd)
        self.price_to_earnings_gaap_forward      = ratio(self.price, self.eps_gaap_fwd)

    def calc_peg(self):
        # PEG = P/E divided by earnings growth in % (below 1 = cheap for its growth)
        # GAAP: TTM EPS vs the fiscal year that ended at least a year earlier
        self.price_earnings_to_growth_gaap_trailing = None
        annual = self.stock.income_stmt
        quarters = self.stock.quarterly_income_stmt
        if annual is not None and not annual.empty and quarters is not None and not quarters.empty:
            cutoff = max(quarters.columns) - pd.Timedelta(days=360)
            older = sorted([c for c in annual.columns if c <= cutoff], reverse=True)
            prev_eps = float(annual.at["Diluted EPS", older[0]]) if older and "Diluted EPS" in annual.index else None
            if prev_eps and prev_eps > 0 and self.eps_gaap_ttm is not None:
                self.price_earnings_to_growth_gaap_trailing = ratio(self.price_to_earnings_gaap_trailing, (self.eps_gaap_ttm / prev_eps - 1) * 100)
        # Non-GAAP: forward P/E vs yearly growth from now to next year's forecast
        # (only 1 year of forecast when Yahoo lags: then the growth to this year's forecast)
        # (a loss forecast gives a negative ratio: no yearly rate, its square root isn't a real number)
        growth_2y = ratio(self.eps_nongaap_next, self.eps_nongaap_ttm)
        growth_1y = ratio(self.eps_nongaap_fwd, self.eps_nongaap_ttm)
        if self.eps_nongaap_next is not None:
            yearly = (growth_2y ** 0.5 - 1) * 100 if growth_2y and growth_2y > 0 else None
        else:
            yearly = (growth_1y - 1) * 100 if growth_1y else None
        self.price_earnings_to_growth_non_gaap_forward = ratio(self.price_to_earnings_non_gaap_forward, yearly)

    def calc_ev(self):
        # Enterprise Value = price of the whole company, debt included, cash removed
        self.enterprise_value_to_sales_forward  = ratio(self.enterprise_value, self.revenue_fwd)
        self.enterprise_value_to_ebitda_forward = ratio(self.enterprise_value, self.ebitda_fwd)
        self.enterprise_value_to_ebit_trailing  = ratio(self.enterprise_value, self.ebit_ttm)
        self.enterprise_value_to_ebit_forward   = ratio(self.enterprise_value, self.ebit_fwd)

    def calc_price_ratios(self):
        # Market cap compared with sales, book value and cash generated
        self.price_to_sales_forward      = ratio(self.market_cap, self.revenue_fwd)
        self.price_to_book_forward       = ratio(self.market_cap, self.book_value_fwd)
        self.price_to_cash_flow_trailing = ratio(self.market_cap, self.cash_flow_ttm)
        self.price_to_cash_flow_forward  = ratio(self.market_cap, self.cash_flow_fwd)

    def get_metrics(self):
        # All 19 metrics as {name: value}
        return {name: getattr(self, name) for name in self.METRICS}

    





    
