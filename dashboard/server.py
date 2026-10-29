#!/usr/bin/env python3
"""
dashboard/server.py — local dashboard for the paper books, scans, certs and market context.

Reads test_ptf.json, test_portfolio.json, scan_tracking.db and the pipeline's data/*.json.
Every change to the Test_PTF book goes through test_ptf.py's own CLI (one source of truth
for the accounting rules); the dashboard never edits a data file directly. Paper only:
nothing here touches trade_logger.py, logs/trades.jsonl or the publishing track.

Jobs it can start in the background:
  - run_pipeline.sh       refused while NYSE or Xetra/Euronext is open (volume_ratio
                          would read the in-progress bar)
  - test_ptf.py update    fills queued orders, checks stops, snapshots NAV; asks for
                          confirmation while a market is open (intraday marks)
  - institutional_data.py Smart Money Score for the given tickers

Usage (from the repo root):
    python3 dashboard/server.py            # http://localhost:8000
    python3 dashboard/server.py --port 8050

Listens on 127.0.0.1 only. POSTs must carry the X-Trading-Agent header and come from the
dashboard's own origin, so other websites open in the browser can't trigger actions.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)  # the modules below use ./data paths
sys.path.insert(0, ROOT)

import yfinance as yf

from cert_barrier_monitor import CERTS
from test_portfolio import ticker_currency
import test_ptf

DB_PATH = "data/scan_tracking.db"
OLD_PTF_PATH = "data/test_portfolio.json"
LIVE_CACHE = "data/dashboard_live.json"
INDEX = os.path.join(ROOT, "dashboard", "index.html")
FX_CCYS = ("USD", "JPY", "GBP", "CNY")
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-=^]{0,14}$")
PY = sys.executable


def read_json(path, default=None):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


# ── market hours ────────────────────────────────────────────────────────────

MARKETS = [  # (name, tz, open, close) — weekdays only, exchange holidays not modelled
    ("NYSE", "America/New_York", time(9, 30), time(16, 0)),
    ("Xetra/Euronext", "Europe/Berlin", time(9, 0), time(17, 30)),
]


def market_status():
    out = []
    for name, tz, o, c in MARKETS:
        now = datetime.now(ZoneInfo(tz))
        out.append({"market": name, "open": now.weekday() < 5 and o <= now.time() < c,
                    "local_time": now.strftime("%H:%M")})
    return {"markets": out, "any_open": any(m["open"] for m in out)}


# ── Test_PTF ledger ─────────────────────────────────────────────────────────

def round_trips(book):
    """Closed trades from filled orders, in ledger order (same walk as test_ptf.positions)."""
    open_, closed = {}, []
    for o in book["orders"]:
        if o["status"] != "filled":
            continue
        t = open_.setdefault(o["ticker"], {"ticker": o["ticker"], "opened": o["fill_date"], "qty": 0,
                                           "cost_eur": 0.0, "bought_eur": 0.0, "proceeds_eur": 0.0,
                                           "realized_eur": 0.0, "exits": []})
        if o["side"] == "BUY":
            t["qty"] += o["qty"]
            t["cost_eur"] += o["value_eur"]
            t["bought_eur"] += o["value_eur"]
            continue
        frac = o["qty"] / t["qty"] if t["qty"] else 0
        cost_out = t["cost_eur"] * frac
        t["cost_eur"] -= cost_out
        t["qty"] -= o["qty"]
        t["proceeds_eur"] += o["value_eur"]
        t["realized_eur"] += o["value_eur"] - cost_out
        t["exits"].append({"date": o["fill_date"], "qty": o["qty"], "price": o["fill_price"],
                           "source": o.get("source"), "reason": o.get("reason")})
        if t["qty"] == 0:
            t["closed"] = o["fill_date"]
            t["pnl_pct"] = t["realized_eur"] / t["bought_eur"] * 100 if t["bought_eur"] else None
            closed.append(open_.pop(o["ticker"]))
    return closed


def ptf_payload():
    book = test_ptf.load_book()
    pos = test_ptf.positions(book)
    buys = {}  # latest BUY reason per open ticker
    for o in book["orders"]:
        if o["status"] == "filled" and o["side"] == "BUY":
            buys[o["ticker"]] = {"reason": o.get("reason"), "source": o.get("source")}
    positions = [{"ticker": t, "ccy": ticker_currency(t), **p, **buys.get(t, {})} for t, p in pos.items()]
    deployed = sum(o["value_eur"] for o in book["orders"] if o["status"] == "filled" and o["side"] == "BUY")
    return {
        "name": book["name"], "created": book["created"], "benchmark": book["benchmark"],
        "initial_capital": book["initial_capital"], "cash": test_ptf.cash(book),
        "shadow_cash": test_ptf.shadow_cash(book), "deployed": deployed,
        "positions": positions, "closed": round_trips(book), "history": book["history"],
        "pending": [o for o in book["orders"] if o["status"] == "pending"],
        "level_changes": book.get("level_changes", [])[-10:],
    }


# ── scans ───────────────────────────────────────────────────────────────────

def scan_payload(scan_date=None):
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    dates = [r[0] for r in con.execute(
        "SELECT scan_date FROM scan_test_group GROUP BY scan_date ORDER BY scan_date DESC")]
    d = scan_date if scan_date in dates else (dates[0] if dates else None)
    rows = [dict(r) for r in con.execute("SELECT * FROM scan_test_group WHERE scan_date = ?", (d,))]
    con.close()
    return {"dates": dates, "date": d, "rows": rows}


def scan_history():
    """Every candidate of every scan, slimmed down — for the verdict scorecard."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT scan_date, ticker, conviction, setup, entry, stop, target, rr_planned, f_score, "
        "sector, final_verdict, risk_manager_verdict FROM scan_test_group ORDER BY scan_date")]
    con.close()
    return rows


# ── market context ──────────────────────────────────────────────────────────

def market_payload(held):
    regime = read_json("data/macro_regime.json", {})
    sent = read_json("data/sentiment_data.json", {})
    rot = read_json("data/sector_rotation.json", {})
    earn = read_json("data/earnings_calendar.json", {})
    held_earn = [e for e in earn.get("tickers", []) if e["ticker"] in held]
    return {
        "regime": {k: regime.get(k) for k in ("generated_at", "regime", "confidence", "growth", "inflation",
                                              "favored_sectors", "dalio_cycle", "minsky_score")},
        "sentiment": {"generated_at": sent.get("generated_at"), "composite_score": sent.get("composite_score"),
                      "composite_label": sent.get("composite_label"), "fear_greed": sent.get("cnn_fear_greed"),
                      "vix": sent.get("vix")},
        "rotation": rot,
        "earnings": {"generated_at": earn.get("generated_at"), "cutoff": earn.get("cutoff_date"), "held": held_earn},
    }


# ── live prices ─────────────────────────────────────────────────────────────

def all_tickers():
    book = test_ptf.load_book()
    old = read_json(OLD_PTF_PATH, {"positions": []})
    t = set(test_ptf.positions(book)) | {book["benchmark"]} | {p["ticker"] for p in old["positions"]}
    t |= {o["ticker"] for o in book["orders"] if o["status"] == "pending"}
    t |= {u["ticker"] for c in CERTS for u in c["underlyings"]}
    t |= {r["ticker"] for r in scan_history()}
    return sorted(t)


def fetch_close(ticker):
    try:
        h = yf.Ticker(ticker).history(period="5d").dropna(subset=["Close"])
        return ticker, (float(h["Close"].iloc[-1]) if not h.empty else None)
    except Exception:
        return ticker, None


def booked_exit(p):
    """Old test portfolio: first day the low touched the stop or the high the target since entry,
    booked at that level (or the open, if it gapped through). Same rule test_ptf.py uses for stops."""
    if p.get("kind") == "long_term":
        return p["ticker"], None
    try:
        h = yf.Ticker(p["ticker"]).history(start=p["entry_date"]).dropna(subset=["Close"])
    except Exception:
        return p["ticker"], None
    for ts, r in h.iloc[1:].iterrows():  # entry day itself excluded: entered at that close
        if r["Low"] <= p["stop"]:
            return p["ticker"], {"date": ts.strftime("%Y-%m-%d"), "kind": "STOP", "price": min(float(r["Open"]), p["stop"])}
        if r["High"] >= p["target"]:
            return p["ticker"], {"date": ts.strftime("%Y-%m-%d"), "kind": "TARGET", "price": max(float(r["Open"]), p["target"])}
    return p["ticker"], None


def fetch_live():
    tickers = all_tickers()
    fx_pairs = [f"EUR{c}=X" for c in FX_CCYS]
    old = read_json(OLD_PTF_PATH, {"positions": []})
    with ThreadPoolExecutor(max_workers=16) as ex:
        got = dict(ex.map(fetch_close, tickers + fx_pairs))
        exits = dict(ex.map(booked_exit, old["positions"]))
    # EUR value of 1 unit of each quote currency (EURUSD=X is USD per EUR)
    fx = {"EUR": 1.0}
    for c in FX_CCYS:
        r = got.get(f"EUR{c}=X")
        fx[c] = 1 / r if r else None
    fx["GBp"] = fx["GBP"] / 100 if fx.get("GBP") else None
    live = {"fetched": datetime.now().isoformat(timespec="seconds"),
            "prices": {t: got.get(t) for t in tickers}, "fx": fx, "old_exits": exits}
    with open(LIVE_CACHE, "w") as f:
        json.dump(live, f, indent=1)
    return live


def data_payload(scan_date=None):
    old = read_json(OLD_PTF_PATH, {"positions": []})
    for p in old["positions"]:
        p["ccy"] = ticker_currency(p["ticker"])
    ptf = ptf_payload()
    held = {p["ticker"] for p in ptf["positions"]} | {o["ticker"] for o in ptf["pending"]}
    return {"ptf": ptf, "scan": scan_payload(scan_date), "scan_history": scan_history(), "old": old,
            "certs": CERTS, "institutional": read_json("data/institutional.json", {"tickers": {}}),
            "market": market_payload(held), "hours": market_status(), "jobs": jobs_list(),
            "live": read_json(LIVE_CACHE), "served": datetime.now().isoformat(timespec="seconds")}


# ── actions (Test_PTF via its CLI) ──────────────────────────────────────────

class BadRequest(Exception):
    pass


def _ticker(v):
    v = str(v or "").strip().upper()
    if not TICKER_RE.match(v):
        raise BadRequest(f"invalid ticker {v!r}")
    return v


def _num(v, name, required=True):
    if v in (None, ""):
        if required:
            raise BadRequest(f"{name} is required")
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise BadRequest(f"{name} must be a number")
    if x <= 0:
        raise BadRequest(f"{name} must be positive")
    return x


def _text(v, name, required=True):
    v = str(v or "").strip()
    if required and not v:
        raise BadRequest(f"{name} is required")
    return v[:600]


def ptf_action(body):
    a = body.get("action")
    if a == "buy":
        qty = _num(body.get("qty"), "qty")
        if qty != int(qty):
            raise BadRequest("qty must be a whole number")
        args = ["buy", _ticker(body.get("ticker")), str(int(qty))]
        for k in ("stop", "target"):
            x = _num(body.get(k), k, required=False)
            if x is not None:
                args += [f"--{k}", str(x)]
        args += ["--reason", _text(body.get("reason"), "reason")]
    elif a == "sell":
        q = str(body.get("qty", "")).strip().lower()
        if q != "all":
            n = _num(q, "qty")
            if n != int(n):
                raise BadRequest("qty must be a whole number or 'all'")
            q = str(int(n))
        args = ["sell", _ticker(body.get("ticker")), q, "--reason", _text(body.get("reason"), "reason")]
    elif a == "set-stop":
        args = ["set-stop", _ticker(body.get("ticker")), str(_num(body.get("stop"), "stop"))]
        t = _num(body.get("target"), "target", required=False)
        if t is not None:
            args += ["--target", str(t)]
        args += ["--reason", _text(body.get("reason"), "reason")]
    elif a in ("cancel", "fill-now"):
        try:
            args = [a, str(int(body.get("order_id")))]
        except (TypeError, ValueError):
            raise BadRequest("order_id must be an integer")
    else:
        raise BadRequest(f"unknown action {a!r}")
    if a in ("buy", "sell"):
        src = _text(body.get("source"), "source", required=False) or f"dashboard {date.today().isoformat()}"
        args += ["--source", src]
    r = subprocess.run([PY, "test_ptf.py", *args], capture_output=True, text=True, timeout=180)
    return {"ok": r.returncode == 0, "cmd": "python3 test_ptf.py " + " ".join(args),
            "output": (r.stdout + r.stderr).strip()}


# ── background jobs ─────────────────────────────────────────────────────────

JOBS, JOBS_LOCK = {}, threading.Lock()
JOB_KINDS = {
    "pipeline": {"label": "Data pipeline (run_pipeline.sh)", "market_guard": "block"},
    "ptf_update": {"label": "Test_PTF update (fill orders, check stops, snapshot)", "market_guard": "confirm"},
    "institutional": {"label": "Institutional scores", "market_guard": "confirm"},
}


def jobs_list():
    with JOBS_LOCK:
        return [{k: v for k, v in j.items() if k != "proc"} | {"log": j["log"][-400:]}
                for j in sorted(JOBS.values(), key=lambda j: j["started"], reverse=True)[:6]]


def _run_job(job, cmd):
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                             env={**os.environ, "PYTHONUNBUFFERED": "1"})
        job["proc"] = p
        for line in p.stdout:
            job["log"].append(re.sub(r"\x1b\[[0-9;]*m", "", line.rstrip("\n")))  # strip ANSI colours
        p.wait()
        job["status"] = "done" if p.returncode == 0 else f"failed (exit {p.returncode})"
    except Exception as e:
        job["log"].append(f"error: {e}")
        job["status"] = "failed"
    job["finished"] = datetime.now().isoformat(timespec="seconds")


def start_job(body):
    kind = body.get("kind")
    if kind not in JOB_KINDS:
        raise BadRequest(f"unknown job {kind!r}")
    hours = market_status()
    guard = JOB_KINDS[kind]["market_guard"]
    if hours["any_open"]:
        open_names = ", ".join(m["market"] for m in hours["markets"] if m["open"])
        if guard == "block":
            raise BadRequest(f"refused: {open_names} open — the pipeline's volume_ratio would read the "
                             f"in-progress bar. Run it pre-market or after the close.")
        if guard == "confirm" and not body.get("confirm_open"):
            return {"needs_confirm": f"{open_names} open — prices will be intraday marks, not closes. Run anyway?"}
    if kind == "pipeline":
        cmd = ["bash", "run_pipeline.sh"]
    elif kind == "ptf_update":
        cmd = [PY, "test_ptf.py"]
    else:
        tickers = [_ticker(t) for t in re.split(r"[\s,]+", str(body.get("tickers", "")).strip()) if t]
        if not tickers:
            raise BadRequest("give at least one ticker")
        cmd = [PY, "institutional_data.py", *tickers[:40]]
    with JOBS_LOCK:
        if any(j["kind"] == kind and j["status"] == "running" for j in JOBS.values()):
            raise BadRequest(f"a {JOB_KINDS[kind]['label']} job is already running")
        jid = uuid.uuid4().hex[:8]
        job = JOBS[jid] = {"id": jid, "kind": kind, "label": JOB_KINDS[kind]["label"], "cmd": " ".join(cmd),
                           "status": "running", "started": datetime.now().isoformat(timespec="seconds"),
                           "finished": None, "log": []}
    threading.Thread(target=_run_job, args=(job, cmd), daemon=True).start()
    return {"job": jid}


# ── HTTP ────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json")

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                self._send(200, open(INDEX, "rb").read(), "text/html; charset=utf-8")
            elif u.path == "/api/data":
                self._json(data_payload(parse_qs(u.query).get("scan", [None])[0]))
            elif u.path == "/api/live":
                self._json(fetch_live())
            elif u.path == "/api/jobs":
                self._json({"jobs": jobs_list(), "hours": market_status()})
            else:
                self._send(404, b"not found", "text/plain")
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        # CSRF guard: a custom header forces a CORS preflight that this server never answers,
        # and the Origin (when sent) must be this dashboard.
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if self.headers.get("X-Trading-Agent") != "1" or (origin and origin not in (f"http://{host}",)):
            return self._json({"error": "forbidden"}, 403)
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
            u = urlparse(self.path)
            if u.path == "/api/ptf":
                self._json(ptf_action(body))
            elif u.path == "/api/jobs":
                self._json(start_job(body))
            else:
                self._send(404, b"not found", "text/plain")
        except BadRequest as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def log_message(self, fmt, *args):
        if "/api/jobs" in (args[0] if args else ""):
            return  # job polling is noisy
        sys.stderr.write(f"[dashboard] {self.address_string()} {fmt % args}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)  # localhost only
    print(f"Trading-Agent dashboard → http://localhost:{a.port}   Ctrl+C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
