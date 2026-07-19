#!/usr/bin/env python3
"""
fetch_transcript.py — Earnings call transcript fetcher
Retrieves the most recent earnings call transcript for a given ticker.
Saves to data/transcripts/TICKER_latest.txt for the Investor Relations agent.

Usage:
  python3 fetch_transcript.py PLAB
  python3 fetch_transcript.py POET --quarter Q1 --year 2026
"""

import os, sys, re, argparse, json
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests --quiet")
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    os.system(f"{sys.executable} -m pip install beautifulsoup4 --quiet")
    from bs4 import BeautifulSoup

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

TRANSCRIPT_DIR = "./data/transcripts"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# ── Source: Motley Fool ───────────────────────────────────────────────────────

def _fetch_page(url: str, timeout: int = 12) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception:
        pass
    return None


def _extract_article_text(soup: BeautifulSoup) -> str | None:
    selectors = [
        ("div", {"class": "article-body"}),
        ("div", {"id": "article-body"}),
        ("div", {"class": re.compile(r"article.?body|content.?body|transcript")}),
        ("article", {}),
        ("main", {}),
    ]
    for tag, attrs in selectors:
        node = soup.find(tag, attrs) if attrs else soup.find(tag)
        if node:
            paragraphs = node.find_all(["p", "h2", "h3", "strong"])
            text = "\n".join(p.get_text(" ", strip=True) for p in paragraphs if p.get_text(strip=True))
            if len(text) > 800:
                return text
    return None


def try_motley_fool(ticker: str) -> dict | None:
    # 1. Try their tag/search page for call transcripts
    urls_to_try = [
        f"https://www.fool.com/earnings/call-transcripts/?ticker={ticker.lower()}",
        f"https://www.fool.com/search/results/?q={ticker}+earnings+transcript&filter=article_type:13",
    ]
    for search_url in urls_to_try:
        soup = _fetch_page(search_url)
        if not soup:
            continue
        links = soup.find_all("a", href=re.compile(r"/earnings/call-transcripts/\d{4}/"))
        for link in links[:8]:
            href = link.get("href", "")
            if ticker.lower() in href.lower() or ticker.lower() in link.get_text("", strip=True).lower():
                full_url = ("https://www.fool.com" + href) if href.startswith("/") else href
                article_soup = _fetch_page(full_url)
                if article_soup:
                    text = _extract_article_text(article_soup)
                    if text and len(text) > 800:
                        return {"source": "Motley Fool", "url": full_url, "text": text}

    # 2. Try constructing URL from yfinance earnings date
    try:
        cal = yf.Ticker(ticker).calendar
        dates = cal.get("Earnings Date", []) if cal else []
        if not isinstance(dates, list):
            dates = [dates]
        for ed in dates[:2]:
            if hasattr(ed, "year"):
                y, m, d = ed.year, ed.month, ed.day
                # Try common Motley Fool slug patterns
                slug_candidates = [
                    f"{ticker.lower()}-q",
                    ticker.lower(),
                ]
                base = f"https://www.fool.com/earnings/call-transcripts/{y}/{m:02d}/{d:02d}/"
                soup_base = _fetch_page(base)
                if soup_base:
                    links = soup_base.find_all("a", href=re.compile(ticker.lower()))
                    for link in links[:3]:
                        href = link.get("href", "")
                        full_url = ("https://www.fool.com" + href) if href.startswith("/") else href
                        article_soup = _fetch_page(full_url)
                        if article_soup:
                            text = _extract_article_text(article_soup)
                            if text and len(text) > 800:
                                return {"source": "Motley Fool", "url": full_url, "text": text}
    except Exception:
        pass

    return None


# ── Source: Seeking Alpha (public summary pages) ──────────────────────────────

def try_seeking_alpha_summary(ticker: str) -> dict | None:
    # SA transcript listing page (public, no login needed for listing)
    url = f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts"
    soup = _fetch_page(url)
    if not soup:
        return None

    links = soup.find_all("a", href=re.compile(r"/article/\d+"))
    for link in links[:5]:
        href = link.get("href", "")
        full_url = ("https://seekingalpha.com" + href) if href.startswith("/") else href
        article_soup = _fetch_page(full_url)
        if article_soup:
            text = _extract_article_text(article_soup)
            if text and len(text) > 800:
                return {"source": "Seeking Alpha", "url": full_url, "text": text}
    return None


# ── Source: Earnings Call Cheatsheet (free summaries) ────────────────────────

def try_earnings_call_cheatsheet(ticker: str) -> dict | None:
    url = f"https://earningscallcheatsheet.com/{ticker.lower()}"
    soup = _fetch_page(url)
    if not soup:
        return None
    content = soup.find("main") or soup.find("article") or soup.body
    if content:
        text = content.get_text(separator="\n", strip=True)
        if len(text) > 300:
            return {
                "source": "EarningsCallCheatsheet (summary — Q&A analysis limited)",
                "url": url,
                "text": text,
                "summary_only": True,
            }
    return None


# ── Source: StockAnalysis earnings page ──────────────────────────────────────

def try_stock_analysis(ticker: str) -> dict | None:
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/?p=quarterly"
    soup = _fetch_page(url)
    if not soup:
        return None
    # This gives financials, not a transcript — only useful for numbers cross-check
    text = soup.get_text(separator="\n", strip=True)
    if len(text) > 500:
        return {
            "source": "StockAnalysis (financial data only — not a transcript)",
            "url": url,
            "text": text[:5000],
            "financials_only": True,
        }
    return None


# ── Main fetch logic ──────────────────────────────────────────────────────────

def fetch_transcript(ticker: str, quarter: str = None, year: int = None) -> dict:
    ticker  = ticker.upper()
    year    = year or datetime.now().year
    quarter = quarter or "latest"

    sources = [
        ("Motley Fool",              try_motley_fool),
        ("Seeking Alpha",            try_seeking_alpha_summary),
        ("EarningsCallCheatsheet",   try_earnings_call_cheatsheet),
    ]

    for name, fn in sources:
        print(f"  [{ticker}] Trying {name}...", end=" ", flush=True)
        try:
            result = fn(ticker)
        except Exception as e:
            result = None
        if result and result.get("text") and len(result["text"]) > 300:
            print(f"✓ found ({len(result['text']):,} chars)")
            return {
                "ticker":       ticker,
                "quarter":      quarter,
                "year":         year,
                "source":       result["source"],
                "url":          result.get("url", ""),
                "text":         result["text"],
                "summary_only": result.get("summary_only", False),
                "financials_only": result.get("financials_only", False),
                "fetched_at":   datetime.now().isoformat(),
                "char_count":   len(result["text"]),
            }
        print("not found")

    return {
        "ticker":   ticker,
        "quarter":  quarter,
        "year":     year,
        "error":    "Transcript not found. Manual retrieval required.",
        "sources_tried": [name for name, _ in sources],
        "manual_sources": [
            f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts",
            f"https://www.fool.com/search/results/?q={ticker}+earnings+transcript",
            f"https://finance.yahoo.com/quote/{ticker}/",
            f"https://ir.[company-website].com/events-presentations",
        ],
    }


# ── Parse transcript into sections ───────────────────────────────────────────

def split_sections(text: str) -> dict:
    """Split transcript into Prepared Remarks and Q&A sections."""
    sections = {"prepared_remarks": "", "qa_section": "", "full_text": text}

    qa_markers = [
        r"question.and.answer", r"q&a", r"q\s*&\s*a session",
        r"operator.*question", r"we will now.*question",
        r"open.*line.*question", r"first question"
    ]
    qa_pattern = re.compile("|".join(qa_markers), re.IGNORECASE)
    match = qa_pattern.search(text)

    if match:
        sections["prepared_remarks"] = text[:match.start()].strip()
        sections["qa_section"]       = text[match.start():].strip()
    else:
        sections["prepared_remarks"] = text
        sections["qa_section"]       = "[Q&A section not identified in transcript]"

    return sections


def main():
    parser = argparse.ArgumentParser(description="Fetch earnings call transcript")
    parser.add_argument("ticker", help="Ticker symbol (e.g. PLAB, AAPL)")
    parser.add_argument("--quarter", "-q", default=None,
                        help="Quarter hint (e.g. Q1, Q2 — informational only)")
    parser.add_argument("--year", "-y", type=int, default=None,
                        help="Year hint (e.g. 2026 — informational only)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Transcript Fetcher — {args.ticker.upper()}")
    if args.quarter or args.year:
        print(f"  Target: {args.quarter or ''} {args.year or ''}")
    print(f"{'='*60}\n")

    result = fetch_transcript(args.ticker, args.quarter, args.year)
    ticker = args.ticker.upper()
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    if "error" in result:
        print(f"\n  ✗ {result['error']}")
        print(f"\n  Manual retrieval options:")
        for url in result.get("manual_sources", []):
            print(f"    • {url}")
        with open(f"{TRANSCRIPT_DIR}/{ticker}_NOTFOUND.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Stub saved to {TRANSCRIPT_DIR}/{ticker}_NOTFOUND.json")
    else:
        sections  = split_sections(result["text"])
        txt_path  = f"{TRANSCRIPT_DIR}/{ticker}_latest.txt"
        json_path = f"{TRANSCRIPT_DIR}/{ticker}_latest.json"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"TICKER:   {ticker}\n")
            f.write(f"SOURCE:   {result.get('source','')}\n")
            f.write(f"FETCHED:  {result.get('fetched_at','')}\n")
            if result.get("url"):
                f.write(f"URL:      {result['url']}\n")
            if result.get("summary_only"):
                f.write(f"NOTE:     Summary only — full transcript not available, Q&A analysis limited\n")
            f.write(f"{'='*60}\n\n")
            f.write("── PREPARED REMARKS ─────────────────────────────────────\n\n")
            f.write(sections["prepared_remarks"] + "\n\n")
            f.write("── Q&A SESSION ──────────────────────────────────────────\n\n")
            f.write(sections["qa_section"] + "\n")

        result["sections"] = {
            "prepared_remarks_chars": len(sections["prepared_remarks"]),
            "qa_section_chars":       len(sections["qa_section"]),
        }
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\n  ✓ Saved to {txt_path}")
        print(f"    Total: {result['char_count']:,} chars  |  "
              f"Prepared: {len(sections['prepared_remarks']):,}  |  "
              f"Q&A: {len(sections['qa_section']):,}")
        if result.get("summary_only"):
            print(f"    ⚠ Summary only — Q&A evasion analysis will be limited")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
