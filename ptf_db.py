#!/usr/bin/env python3
"""
ptf_db.py — mirrors the Test_PTF paper portfolio (data/test_ptf.json) into
SQLite (data/scan_tracking.db, the same DB scan_logger.py writes), so the
tickers the pipeline puts in portfolio can be queried next to the
scan_test_group rows that selected them.

Design:
  - data/test_ptf.json stays the source of truth. test_ptf.py calls sync()
    every time it saves the book; the ptf_* tables are rebuilt from the JSON
    inside a single transaction, so the DB can never drift from the ledger and
    a re-sync is always safe (idempotent).
  - A DB failure never blocks test_ptf.py: the JSON is written first and
    sync errors are printed, not raised (see test_ptf.save_book).

Tables:
  ptf_orders         every order as recorded (pending / filled / cancelled)
  ptf_positions      open positions right now: qty, avg cost EUR, stop, target
  ptf_history        daily NAV vs shadow benchmark snapshots
  ptf_level_changes  stop/target moves with reasons
  ptf_meta           name, capital, benchmark, last sync time
View:
  v_ptf_tickers      one row per ticker ever bought: open/closed, dates, qty,
                     plus the scan_test_group row that preceded the first buy
                     (conviction, f_score, strategy_type, final_verdict)

Manual re-sync / backfill:  python3 test_ptf.py sync-db
"""

import sqlite3
from datetime import datetime

DB_PATH = "data/scan_tracking.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ptf_orders (
    id               INTEGER PRIMARY KEY,
    created          TEXT NOT NULL,
    ticker           TEXT NOT NULL,
    side             TEXT NOT NULL,
    qty              NUMERIC,          -- 'all' while a sell-all is pending
    reason           TEXT,
    source           TEXT,
    status           TEXT NOT NULL,
    fill_date        TEXT,
    fill_price       REAL,
    fx               REAL,
    value_eur        REAL,
    bench_price      REAL,
    bench_units      REAL,
    bench_value_eur  REAL,
    fill_note        TEXT
);
CREATE INDEX IF NOT EXISTS ix_ptf_orders_ticker ON ptf_orders(ticker);

CREATE TABLE IF NOT EXISTS ptf_positions (
    ticker        TEXT PRIMARY KEY,
    qty           REAL NOT NULL,
    avg_cost_eur  REAL,
    cost_eur      REAL,
    opened        TEXT,
    stop          REAL,
    target        REAL,
    bench_units   REAL
);

CREATE TABLE IF NOT EXISTS ptf_history (
    date         TEXT PRIMARY KEY,
    nav          REAL,
    shadow_nav   REAL,
    cash         REAL,
    invested     REAL,
    bench_close  REAL
);

CREATE TABLE IF NOT EXISTS ptf_level_changes (
    seq     INTEGER PRIMARY KEY,
    date    TEXT,
    ticker  TEXT,
    stop    REAL,
    target  REAL,
    reason  TEXT
);

CREATE TABLE IF NOT EXISTS ptf_meta (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
"""

VIEW_SQL = """
CREATE VIEW v_ptf_tickers AS
SELECT
    o.ticker,
    CASE WHEN p.ticker IS NULL THEN 'closed' ELSE 'open' END      AS status,
    MIN(CASE WHEN o.side = 'BUY' THEN o.created END)               AS first_buy_order,
    MIN(CASE WHEN o.side = 'BUY' AND o.status = 'filled' THEN o.fill_date END) AS first_fill,
    MAX(CASE WHEN o.status = 'filled' THEN o.fill_date END)        AS last_fill,
    SUM(CASE WHEN o.side = 'BUY'  AND o.status = 'filled' THEN o.qty ELSE 0 END) AS qty_bought,
    SUM(CASE WHEN o.side = 'SELL' AND o.status = 'filled' THEN o.qty ELSE 0 END) AS qty_sold,
    SUM(CASE WHEN o.side = 'BUY'  AND o.status = 'filled' THEN o.value_eur ELSE 0 END) AS eur_bought,
    SUM(CASE WHEN o.side = 'SELL' AND o.status = 'filled' THEN o.value_eur ELSE 0 END) AS eur_sold,
    p.qty AS qty_open, p.avg_cost_eur, p.stop, p.target,
    s.scan_date      AS scan_date,
    s.conviction     AS scan_conviction,
    s.f_score        AS scan_f_score,
    s.strategy_type  AS scan_strategy_type,
    s.final_verdict  AS scan_final_verdict
FROM ptf_orders o
LEFT JOIN ptf_positions p ON p.ticker = o.ticker
LEFT JOIN scan_test_group s ON s.id = (
    SELECT s2.id FROM scan_test_group s2
    WHERE s2.ticker = o.ticker
      AND s2.scan_date <= (SELECT MIN(created) FROM ptf_orders
                           WHERE ticker = o.ticker AND side = 'BUY')
    ORDER BY s2.scan_date DESC, s2.id DESC LIMIT 1)
WHERE o.status != 'cancelled'
GROUP BY o.ticker
HAVING SUM(CASE WHEN o.side = 'BUY' THEN 1 ELSE 0 END) > 0;
"""

ORDER_COLS = ["id", "created", "ticker", "side", "qty", "reason", "source", "status",
              "fill_date", "fill_price", "fx", "value_eur", "bench_price", "bench_units",
              "bench_value_eur", "fill_note"]


def sync(book, open_positions, db_path=DB_PATH):
    """Rebuild every ptf_* table from the in-memory book. `open_positions` is
    test_ptf.positions(book) (ticker -> qty/cost_eur/opened/stop/target/...)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        has_scan = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='scan_test_group'").fetchone()
        with conn:  # one transaction: all tables or nothing
            for t in ("ptf_orders", "ptf_positions", "ptf_history", "ptf_level_changes", "ptf_meta"):
                conn.execute(f"DELETE FROM {t}")
            conn.executemany(
                f"INSERT INTO ptf_orders ({', '.join(ORDER_COLS)}) "
                f"VALUES ({', '.join('?' * len(ORDER_COLS))})",
                [[o.get(c) for c in ORDER_COLS] for o in book["orders"]])
            conn.executemany(
                "INSERT INTO ptf_positions VALUES (?,?,?,?,?,?,?,?)",
                [(t, p["qty"], p["cost_eur"] / p["qty"] if p["qty"] else None, p["cost_eur"],
                  p.get("opened"), p.get("stop"), p.get("target"), p.get("bench_units"))
                 for t, p in open_positions.items()])
            conn.executemany(
                "INSERT INTO ptf_history VALUES (?,?,?,?,?,?)",
                [(h["date"], h.get("nav"), h.get("shadow_nav"), h.get("cash"),
                  h.get("invested"), h.get("bench_close")) for h in book.get("history", [])])
            conn.executemany(
                "INSERT INTO ptf_level_changes VALUES (?,?,?,?,?,?)",
                [(i, c.get("date"), c.get("ticker"), c.get("stop"), c.get("target"), c.get("reason"))
                 for i, c in enumerate(book.get("level_changes", []), 1)])
            conn.executemany(
                "INSERT INTO ptf_meta VALUES (?,?)",
                [("name", book.get("name")), ("initial_capital", str(book.get("initial_capital"))),
                 ("base_ccy", book.get("base_ccy")), ("benchmark", book.get("benchmark")),
                 ("synced_at", datetime.now().isoformat(timespec="seconds"))])
            conn.execute("DROP VIEW IF EXISTS v_ptf_tickers")
            if has_scan:
                conn.execute(VIEW_SQL)
        return len(open_positions), len(book["orders"])
    finally:
        conn.close()
