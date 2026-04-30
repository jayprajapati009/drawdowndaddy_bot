"""
Yahoo Finance ticker search.

Wraps yf.Search so handlers get clean, exchange-normalised results
without dealing with Yahoo's internal exchange codes.
"""

import logging
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

# Yahoo Finance internal exchange codes → our exchange names
_YF_EXCHANGE = {
    "NMS":       "NASDAQ",
    "NGM":       "NASDAQ",
    "NCM":       "NASDAQ",
    "NYQ":       "NYSE",
    "NYSEArca":  "NYSE",
    "ASE":       "NYSE",
    "NSI":       "NSE",
    "BSE":       "BSE",
    "BOM":       "BSE",
}

# Only show these asset types to avoid confusing users with indices/currencies
_ALLOWED_TYPES = {"EQUITY", "ETF"}


def search_tickers(query: str, max_results: int = 5) -> list[dict]:
    """
    Search Yahoo Finance for *query*.
    Returns up to *max_results* dicts: {ticker, name, exchange}.
    Empty list on failure or no results.
    """
    try:
        raw = yf.Search(query, max_results=max_results * 3, news_count=0)
        quotes = raw.quotes or []
    except Exception as exc:
        logger.warning("Ticker search failed for %r: %s", query, exc)
        return []

    results = []
    for q in quotes:
        if q.get("quoteType") not in _ALLOWED_TYPES:
            continue
        ticker   = q.get("symbol", "").strip()
        name     = (q.get("longname") or q.get("shortname") or ticker).strip()
        exchange = _YF_EXCHANGE.get(q.get("exchange", ""), "")
        if not ticker:
            continue
        results.append({"ticker": ticker, "name": name, "exchange": exchange})
        if len(results) >= max_results:
            break

    logger.debug("Search %r → %d results", query, len(results))
    return results
