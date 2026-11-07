"""
profitability.py — the Profitability evaluation: the 13 metrics of the Seeking Alpha
Profitability page, all over the last 12 months (trailing).

Margins and returns are in % (e.g. 25.0 = 25%), asset turnover is a multiple (0.96x),
cash and income figures are in the company's reporting currency.
"""

from quant_parameter_class import QuantParameter
from quant_utils import last4, percent, quarter, ratio, to_number

# SA (S&P Capital IQ) uses a fixed 37.5% tax rate for return on capital
NOTIONAL_TAX_RATE = 0.375


def average(a, b):
    return None if a is None or b is None else (a + b) / 2


def total_capital(balance, back):
    # Debt + equity on one balance-sheet date (no debt line = no debt)
    equity = quarter(balance, "Stockholders Equity", back)
    debt = quarter(balance, "Total Debt", back)
    return None if equity is None else equity + (debt or 0)


class Profitability(QuantParameter):
    # The profitability metrics
    METRICS = [
        "gross_profit_margin_trailing",
        "ebit_margin_trailing",
        "ebitda_margin_trailing",
        "net_income_margin_trailing",
        "levered_free_cash_flow_margin_trailing",
        "return_on_common_equity_trailing",
        "return_on_total_capital_trailing",
        "return_on_total_assets_trailing",
        "capital_expenditure_to_sales_trailing",
        "asset_turnover_ratio_trailing",
        "cash_from_operations_trailing",
        "cash_per_share_trailing",
        "net_income_per_employee_trailing",
    ]
    # table in the DB
    TABLE_NAME = "profitability_history"

    # The constructor of the class
    def __init__(self, ticker, stock=None):
        super().__init__(ticker, stock)

        # ── Metrics yfinance already gives ready-made (fraction -> %) ──
        # Yahoo puts 0 when a company has no such line (banks have no gross profit / EBITDA)
        self.gross_profit_margin_trailing     = percent(to_number(self.info.get("grossMargins")) or None)
        self.ebitda_margin_trailing           = percent(to_number(self.info.get("ebitdaMargins")) or None)
        self.net_income_margin_trailing       = percent(to_number(self.info.get("profitMargins")))
        self.return_on_common_equity_trailing = percent(to_number(self.info.get("returnOnEquity")))
        self.return_on_total_assets_trailing  = percent(to_number(self.info.get("returnOnAssets")))
        self.cash_from_operations_trailing    = to_number(self.info.get("operatingCashflow"))

        # ── Raw numbers: last 12 months ──
        income   = self.stock.quarterly_income_stmt
        cash     = self.stock.quarterly_cashflow
        balance  = self.stock.quarterly_balance_sheet
        self.revenue_ttm    = to_number(self.info.get("totalRevenue"))
        self.net_income_ttm = to_number(self.info.get("netIncomeToCommon"))
        # Yahoo's free cash flow is the "levered" one (after interest), like SA's
        self.levered_free_cash_flow_ttm = to_number(self.info.get("freeCashflow"))
        self.ebit_ttm       = last4(income, "EBIT")
        capex = last4(cash, "Capital Expenditure")
        self.capex_ttm      = abs(capex) if capex is not None else None   # money spent is shown negative
        self.shares         = to_number(self.info.get("sharesOutstanding"))
        self.employees      = to_number(self.info.get("fullTimeEmployees"))

        # ── Raw numbers: balance sheet today and a year ago (back=4 quarters) ──
        self.cash_now      = quarter(balance, "Cash And Cash Equivalents")
        self.assets_now    = quarter(balance, "Total Assets")
        self.assets_before = quarter(balance, "Total Assets", back=4)
        # Total capital = what lenders and shareholders put in (debt + equity)
        self.capital_now    = total_capital(balance, back=0)
        self.capital_before = total_capital(balance, back=4)

        # ── Metrics we calculate ourselves ──
        self.calc_margins()
        self.calc_returns()
        self.calc_per_unit()

    def calc_margins(self):
        # Share of every sale left after each kind of cost
        self.ebit_margin_trailing = percent(ratio(self.ebit_ttm, self.revenue_ttm))
        self.levered_free_cash_flow_margin_trailing = percent(ratio(self.levered_free_cash_flow_ttm, self.revenue_ttm))
        self.capital_expenditure_to_sales_trailing = percent(ratio(self.capex_ttm, self.revenue_ttm))

    def calc_returns(self):
        # Profit after a standard tax, per unit of average capital over the year (start + end) / 2
        ebit_after_tax = self.ebit_ttm * (1 - NOTIONAL_TAX_RATE) if self.ebit_ttm is not None else None
        self.return_on_total_capital_trailing = percent(ratio(ebit_after_tax, average(self.capital_now, self.capital_before)))
        # Sales made per unit of assets (e.g. 0.96x = 0.96 of sales per 1 of assets)
        self.asset_turnover_ratio_trailing = ratio(self.revenue_ttm, average(self.assets_now, self.assets_before))

    def calc_per_unit(self):
        self.cash_per_share_trailing = ratio(self.cash_now, self.shares)
        self.net_income_per_employee_trailing = ratio(self.net_income_ttm, self.employees)

    def get_metrics(self):
        # All 13 metrics as {name: value}
        return {name: getattr(self, name) for name in self.METRICS}
