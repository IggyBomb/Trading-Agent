"""
quant_utils.py — small helpers shared by every evaluation class
(Valuation, Growth, ...).
"""


def to_number(value):
    # Plain float, or None if missing / not a number (NaN)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def percent(fraction):
    # 0.25 -> 25.0 (yfinance gives growth as a fraction)
    return fraction * 100 if fraction is not None else None


def ratio(top, bottom):
    # Safe division: no number if data is missing or the bottom is zero/negative
    if top is None or bottom is None or bottom <= 0:
        return None
    return top / bottom


def growth(new, old):
    # % change from old to new (e.g. 50.0 = +50%). No number if old is missing or
    # zero/negative: growth from a loss has no meaning (SA shows "NM")
    change = ratio(new, old)
    return (change - 1) * 100 if change is not None and new is not None else None


def last4(table, row):
    # TTM = sum of the last 4 quarters of one line of a financial statement
    if table is None or row not in table.index:
        return None
    values = table.loc[row].sort_index(ascending=False).iloc[:4]
    return None if len(values) < 4 or values.isna().any() else float(values.sum())


def yearly(table, row, years=2):
    # One line of an annual statement, newest year first: [last year, year before, ...]
    if table is None or row not in table.index:
        return [None] * years
    values = [to_number(v) for v in table.loc[row].sort_index(ascending=False).iloc[:years]]
    return values + [None] * (years - len(values))


def quarter(table, row, back=0):
    # One line of a quarterly statement: back=0 = latest quarter, back=4 = same quarter a year earlier
    if table is None or row not in table.index:
        return None
    values = table.loc[row].sort_index(ascending=False)
    return to_number(values.iloc[back]) if len(values) > back else None


def estimate(table, period, column="avg"):
    # Analyst figure for a period: "0y" = this fiscal year, "+1y" = next one
    if table is None or period not in table.index or column not in table.columns:
        return None
    return to_number(table.loc[period, column])


def forecast_lags(revenue_estimate, income_stmt):
    # Right after a fiscal year closes, Yahoo can lag for a few weeks: its "this year"
    # forecast (0y) is then still the year just reported, and "+1y" is really this year.
    # Revenue tells which case we're in: 0y should start from the last reported year.
    base = estimate(revenue_estimate, "0y", "yearAgoRevenue")
    last_year, year_before = yearly(income_stmt, "Total Revenue")
    if base is None or not last_year or not year_before:
        return False
    return abs(base / year_before - 1) < 0.03 and abs(base / last_year - 1) >= 0.03


# Sector given to tickers that are not in the benchmark workbook (add them at the next batch upload)
NOT_FOUND = "NOT FOUND IN Sector_Benchmarks.xlsx"


def model_sector(ticker, sector_lookup):
    # (model code, region) of a ticker, e.g. ("SM", "US"), from the workbook's Constituents sheet.
    # Not in the workbook -> (NOT_FOUND, None), so it shows up as a flag
    return sector_lookup.get(ticker, (NOT_FOUND, None))