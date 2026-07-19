# System Architecture — your-trading-system

Complete map of every component, what it reads, what it writes, and what triggers it. Generated 2026-06-23 by reading the live codebase (not from memory/notes) — treat this as ground truth for that date, but re-verify against the code if it's been a while.

---

## 1. Directory tree

```
trading_agent/
├── .claude/
│   └── commands/scan.md          ← the ACTIVE /scan command (Claude Code reads here)
├── .trading/
│   ├── agents/                   ← 11 agent personas (.md prompts, no code)
│   ├── commands/                 ← EMPTY (old scan.md stub deleted 2026-06-21)
│   ├── hooks/                    ← shell scripts wired into settings.json hooks
│   ├── output-styles/terse.md    ← optional terse output mode
│   ├── plugins/alerts/config.json← calendar integration stub (not wired to any script)
│   ├── rules/forex.md            ← FX-specific rules, separate from RISK.md
│   └── skills/{breakout,pullback}/playbook.md
├── data/                         ← all pipeline output (JSON), gitignored contents
│   └── transcripts/              ← earnings call transcripts (fetch_transcript.py)
├── logs/
│   └── trades.jsonl              ← the trade ledger, source of truth for P&L
├── sessions/                     ← manual session notes (YYYY-MM-DD.md)
├── snapshots/                    ← EndOfDay.sh daily backups (trades.jsonl + sentiment_data.json)
├── *.py                          ← 16 scripts, all flat in repo root
├── *.sh                          ← run_pipeline.sh (orchestrator, repo root)
├── config.py                     ← single source of truth for constants + file paths
├── RISK.md / RISK.local.md       ← global rules / personal account data (gitignored)
├── settings.json                 ← hooks + permissions + model + riskFile pointer
├── settings.local.json           ← personal overrides (gitignored)
├── .env                          ← API keys (gitignored): FINNHUB_API_KEY
└── ARCHITECTURE.md               ← this file
```

---

## 2. Config & secrets — the shared backbone

**`config.py`** — every script imports from here. No magic numbers duplicated across files.
- Account: `ACCOUNT_SIZE = 74_000`
- Risk: `RR_RATIO = 1.5`
- Per-market filters: `MIN_*` / `EU_*` / `JP_*` / `CA_*` / `BR_*` (volume, ATR%, batch size/pause)
- `CONVICTION_FILTER = {"High", "Medium"}` — gates which tickers flow into fundamental_agent.py and alt_data.py
- **File path constants** (`*_PATH`) — every script's input/output path is defined once here and imported, not hardcoded

**`.env`** (gitignored, loaded via `python-dotenv` in `alt_data.py`):
- `FINNHUB_API_KEY` — powers analyst trend + insider MSPR + news fallback (added 2026-06-23)
- `QUIVER_API_KEY` — congressional trading, reference-only now (not scored — both Quiver and Finnhub gate that endpoint behind paid plans)

**`RISK.md`** (global, versioned) — dynamic position-sizing tiers (HALF/NORMAL/GOOD/STRONG/MAX), max 5 open positions, 3% daily drawdown, 1.5:1 min R:R.
**`RISK.local.md`** (gitignored) — actual account state: €74k (€44k invested + €30k liquidity), Trade Republic broker, live position snapshot. `risk-manager.md` and `risk_dashboard.py`/`position_monitor.py` read this for real sizing math.
**`.trading/rules/forex.md`** — session awareness (London/NY), pip sizing, spread filters — only applies to FX pairs.

---

## 3. Hooks — what fires automatically (wired in `settings.json`)

| Event | Script | Behavior |
|---|---|---|
| `UserPromptSubmit` (every message) | `.trading/hooks/PreMarket.sh` | One-line status: open position count (from trades.jsonl) + sentiment data date. Replaced an old version that dumped all 3038 tickers. |
| `Stop` (session end) | `.trading/hooks/EndOfDay.sh` | Backs up `trades.jsonl` + `sentiment_data.json` to `snapshots/YYYY-MM-DD/`. Warns if no session note exists at `sessions/YYYY-MM-DD.md`. |
| (manual, deprecated) | `.trading/hooks/PostTrade.sh` | Dead stub — just prints a message redirecting to `trade_logger.py`. Not wired to any hook event. |

`settings.json` also sets: `model: claude-opus-4-8`, `riskFile: RISK.md`, permissions `[Bash, Read, Write, WebFetch]`.

---

## 4. Python scripts — inputs, outputs, role

### Pre-session data layer (run via `run_pipeline.sh`, in this exact order)

| Order | Script | Reads | Writes | Purpose |
|---|---|---|---|---|
| 1 | `earnings_calendar.py` | `data/watchlist.txt` | `data/earnings_calendar.json` | Flags tickers reporting within 7 days — run before everything else |
| — | *(pipeline checks `logs/trades.jsonl` open positions against earnings_calendar.json → prints a trigger to run `investor-relations.md` if any open position reports soon)* |
| 2 | `fetch_data.py` | `data/watchlist.txt` (3,179 tickers: US+EU+JP+CA+BR) | `data/market_data.json` | OHLCV, technicals, conviction filter (High/Medium/Low). Has per-market batching to dodge Yahoo rate limits. |
| *(3min cooldown in run_pipeline.sh — Yahoo rate-limit reset)* |
| 3 | `fundamental_agent.py` | `data/market_data.json`, yfinance | `data/fundamental_data.json` | Scores High/Medium conviction tickers 0–100 (Track A/B/C routing) |
| 4 | `sentiment_agent.py` | yfinance, CNN F&G scrape | `data/sentiment_data.json` | F&G, VIX, SPY/QQQ/IWM vs MA, EU internals (DAX/FTSE/CAC), composite score → drives sizing tier |
| 5 | `alt_data.py` | `data/market_data.json` (conviction-filtered), yfinance, Finnhub, Quiver | `data/alt_data.json` | Insider clusters (yfinance) + insider MSPR (Finnhub) + short interest + **analyst recommendation trend (Finnhub)** + news NLP (VADER, yfinance/Finnhub news) + congressional (Quiver, reference only). Outputs Alt Data Score 0–100. |
| 6 | `macro_regime_classifier.py` | yfinance market indicators | `data/macro_regime.json` | Auto Goldilocks/Reflation/Stagflation/Deflation + Minsky score + Dalio cycle |
| 7 | `sector_rotation.py` | yfinance (11 US SPDR + 8 EU Xtrackers ETFs) | `data/sector_rotation.json` | 5d sector momentum ranking |
| 8 | `watchlist_ranker.py` | all of the above JSONs | `data/watchlist_ranked.json` | Composite score: tech 40% / fund 25% / alt 20% / vol 15% |

### Pre-market / intraday

| Script | Reads | Writes | Purpose |
|---|---|---|---|
| `pre_market_scanner.py` | `data/market_data.json`, open positions, yfinance | `data/premarket_gaps.json` | Scans up to 300 EU tickers + open positions for overnight gaps (±2% default), run ~08:30 CET |
| `price_alert_monitor.py` | Yahoo v8 chart endpoint directly (bypasses yfinance to dodge rate-limit conflicts with fetch_data.py) | `data/price_cache.json` (fallback cache) | Live price alerts, shows `[cached]` tag if live fetch fails |
| `fetch_transcript.py` | Motley Fool / Seeking Alpha (scrape) | `data/transcripts/TICKER_latest.txt` | Earnings call transcript for `investor-relations.md` |

### Position management (run anytime, standalone)

| Script | Reads | Writes | Purpose |
|---|---|---|---|
| `risk_dashboard.py` | `logs/trades.jsonl`, `RISK.local.md`, live prices | terminal | Live portfolio snapshot: P&L, sizing tier, stop proximity, earnings countdown, drawdown |
| `position_monitor.py` | `logs/trades.jsonl`, live prices | terminal | Per-trade daily health check: stop distance, target progress, R-multiple, time stop, trail signal |
| `correlation_check.py` | `logs/trades.jsonl` open positions, yfinance 60d | terminal | Sector concentration + pairwise correlation matrix; `--add TICKER` tests a proposed new position before entry |

### Trade lifecycle

| Script | Reads | Writes | Purpose |
|---|---|---|---|
| `trade_logger.py` | `data/sentiment_data.json` (for sizing tier at entry) | `logs/trades.jsonl` | CLI: `entry` / `exit` / `stats` / `open` / `show`. Optional `--grade A/B/C`, `--track A/B/C` |
| `populate_trades.py` | (one-time historical import) | `logs/trades.jsonl` | Already run once — imported 33 historical trades |
| `backtest.py` | `logs/trades.jsonl`, yfinance | `data/backtest_results.json` | 3 modes: `validate` (replay closed trades), `simulate` (hypothetical), `summary` (stats) |

**Orchestrator:** `run_pipeline.sh` — runs steps 1, 2, (cooldown), 3, 4, 5, 6, 7, 8 above in sequence, color-coded pass/fail, never blocks on failure (flags `[PILLAR INCOMPLETE]` and continues), prints pillar status table + Friday journal-analyzer reminder at the end.

### Contrarian scanner (run on demand via `/contrarian`)

| Script | Reads | Writes | Purpose |
|---|---|---|---|
| `contrarian_scan.py` | `data/market_data.json` (downtrend pool), open positions (trade_logger), yfinance (1yr OHLCV + .info) | `data/contrarian_data.json` | Scans for high-quality stocks under temporary pressure: down ≥20% from 52wH + RSI ≤35 + revenue not collapsing. Scores 0–12 per ticker. Runtime: ~3–5 min. Invoke via `python3 contrarian_scan.py` or `--tickers AAPL MSFT` for targeted scan. |

---

## 5. Agents (`.trading/agents/*.md`) — prompts, not code

These are pure markdown personas invoked by Claude during a session — they read the JSON files above and produce structured verdict blocks. None of them execute code themselves.

| Agent | Reads | Pipeline position | Role |
|---|---|---|---|
| `macro-analyst.md` | macro_regime.json, market context | Before `/scan` | Regime, yield curve, Fed/ECB/BOJ, cross-asset matrix, Financial Cycle Analysis (Marks/Dalio/Minsky/Kindleberger/Reinhart-Rogoff/Koo). Outputs Macro Verdict + Directional Bias (LONG/NEUTRAL/SHORT) — gates Step 10 of `/scan`. |
| `exit-analyst.md` | open positions (trade_logger/position_monitor) | `/scan` Step 0 | Exit type classification, time stops, trail rules, partial exits, thesis-break checklist — runs **before** any new-idea scanning |
| `technical-analyst.md` | market_data.json | `/scan` Step 3 (implicit) | Murphy/Weinstein/Minervini/Nison/Wyckoff/Elder/Bulkowski — setup quality A/B/C |
| `fundamental-analyst.md` | fundamental_data.json | `/scan` Step 3 | Graham/Fisher/Lynch/Ilmanen/Koller DCF/Penman/Benninga, Track A/B/C routing |
| `market-researcher.md` | live web/news | `/scan` Step 5 (mandatory for HIGH conviction) | News catalysts, options flow, institutional activity, sector rotation, risk events |
| `alt-data-agent.md` | **alt_data.json** | `/scan` Step 6 (mandatory, all tickers) | Interprets insider clusters + MSPR, short interest, analyst trend, news velocity → Alt Data Score verdict block |
| `strategy-analyst.md` | all prior agent outputs | `/scan` Step 7 | Classifies POSITION / SWING / MOMENTUM / TURNAROUND / EVENT |
| `institutional-flow.md` | 13F/dark pool/options flow/ETF flows (live research) | `/scan` Step 8 (mandatory, all tickers) | Smart Money Score 0–100 → ALIGNED/CAUTIOUS/CONTRARIAN WARNING |
| `risk-manager.md` | RISK.local.md, full analysis stack | `/scan` Step 9 | Final APPROVE/CAUTION/REJECT, position sizing, stop validation |
| `short-screener.md` | market_data.json | `/scan` Step 10 (conditional — only if macro bias is NEUTRAL or SHORT) | Short candidates with Short Score |
| `contrarian-analyst.md` | `data/contrarian_data.json` (from `contrarian_scan.py`) | `/contrarian` command (standalone companion to `/scan`) | Interprets contrarian_data.json through Dreman/Marks/Klarman framework. Five signals: price weakness, oversold RSI, fundamental integrity, short squeeze potential, volume divergence. Narrative taxonomy: MACRO_FEAR / SINGLE_EVENT / SECTOR_CONTAGION / CROWDED_SHORT / PROXY_COLLAPSE / GROWTH_DECELERATION. Outputs CONTRARIAN OVERVIEW + per-ticker CONTRARIAN VERDICT (HIGH/MEDIUM/LOW). Never merged with momentum scan output. |
| `investor-relations.md` | `data/transcripts/*.txt` | Standalone, triggered by `run_pipeline.sh` when an open position has earnings ≤7 days | Earnings call tone, metrics vs consensus, Q&A evasion, 5 takeaways |
| `journal-analyzer.md` | `logs/trades.jsonl` | Standalone, Friday reminder from `run_pipeline.sh` | 8-phase trade journal analysis incl. Performance Attribution |

---

## 6. The `/scan` command — full step sequence

Lives at `.claude/commands/scan.md` (this is the one Claude Code actually reads — `.trading/commands/` is empty, an old stub was deleted there 2026-06-21).

```
Step 0  → exit-analyst.md on all open positions (skip if none)
Step 1  → load market_data.json + fundamental_data.json + sentiment_data.json + alt_data.json
           (each missing file = flag only, never block)
Step 2  → cross-reference technical conviction × fundamental rating → CONFIRMED / CAUTION / drop
Step 3  → assess each setup (trend, volume, S/R, setup type, ATR%, F-Score)
Step 4  → rank: CONFIRMED by f_score desc, then CAUTION by volume_ratio desc
Step 5  → market-researcher.md — MANDATORY for HIGH conviction, optional for Medium
Step 6  → alt-data-agent.md — MANDATORY for all tickers in output
Step 7  → strategy-analyst.md — all tickers
Step 8  → institutional-flow.md — MANDATORY for all tickers (final analysis layer)
Step 9  → risk-manager.md — final sizing/stop/APPROVE-CAUTION-REJECT, fed RISK.local.md
Step 10 → short-screener.md — CONDITIONAL on macro-analyst Directional Bias (NEUTRAL/SHORT only)
Step 11 → contrarian-analyst.md — OPTIONAL companion, invoked by /contrarian
          (always separate from Steps 1–10; momentum and contrarian outputs never merged)
```

Hard rule baked into the command: Steps 5–8 are never skipped for HIGH conviction tickers; missing data flags and continues, never blocks — same "flag not block" principle as the rest of the system.

---

## 7. Data flow — one diagram

```
watchlist.txt (3,179 tickers)
        │
        ▼
earnings_calendar.py ──────────────► earnings_calendar.json ─┐
        │                                                     │ (cross-check open
        ▼                                                     │  positions → trigger
fetch_data.py ──────────────────────► market_data.json        │  investor-relations.md)
        │                                  │  │  │             │
        │ (conviction-filtered)            │  │  └─────────────┘
        ▼                                  │  │
fundamental_agent.py ──► fundamental_data.json │
        │                                     │
sentiment_agent.py ─────► sentiment_data.json ─┼──► trade_logger.py (sizing tier at entry)
        │                                     │
alt_data.py ◄── yfinance + Finnhub + Quiver ──┤
        └──────────────────────────► alt_data.json
        │
macro_regime_classifier.py ──► macro_regime.json
sector_rotation.py ──────────► sector_rotation.json
        │
watchlist_ranker.py (reads all above) ──► watchlist_ranked.json

                    ════════ /scan reads market_data + fundamental_data +
                              sentiment_data + alt_data ════════
                                          │
                         exit-analyst → technical/fundamental cross-ref →
                         market-researcher → alt-data-agent → strategy-analyst →
                         institutional-flow → risk-manager → (short-screener if NEUTRAL/SHORT)
                                          │
                                          ▼
                              trade_logger.py entry ──► logs/trades.jsonl
                                          │
                    position_monitor.py / risk_dashboard.py / correlation_check.py
                              (read trades.jsonl continuously while open)
                                          │
                              trade_logger.py exit ──► logs/trades.jsonl (status: closed)
                                          │
                              journal-analyzer.md (Friday) / backtest.py validate
                                          │
                              EndOfDay.sh ──► snapshots/YYYY-MM-DD/
```

---

## 8. Known gaps / things that look wired but aren't

- `.trading/plugins/alerts/config.json` — a Google Calendar integration stub. Not imported or called by any script. Dead config.
- `.trading/statusline.json` — static placeholder (`open_positions: 0`, `last_updated: 2024-01-01`). Not regenerated by any script — if you want a live statusline, something needs to write to this file (currently nothing does).
- `PostTrade.sh` — deprecated stub, not wired to any hook event in `settings.json`. Safe to delete if you want to reduce clutter; harmless if left.
- `RISK.local.md`'s `personalRiskFile` / `brokerConfig: "broker.json"` pointer in `settings.local.json` — `broker.json` does not exist anywhere in the repo. Referenced but never created.
- Congressional trading (`alt_data.py` → Quiver) is fetched and stored in `alt_data.json` but excluded from scoring as of 2026-06-23 — both free sources (Quiver, Finnhub) gated it behind paid plans. Financial Modeling Prep is the untested candidate to bring it back free.
- `data/eu_market_data.json`, `data/ticker_data_20260611.json`, `data/scan_results_2026-05-07.txt` — orphaned one-off files from earlier sessions, not read by any current script.
