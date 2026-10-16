"""Market data: prices, returns, volatilities from yfinance.
Falls back to realistic synthetic data if yfinance is unavailable (network issues, rate limits).
All synthetic values are clearly labelled `simulated=True` in the response.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_PRICE_CACHE: dict[str, dict] = {}          # simple in-process cache
_CACHE_TS: datetime | None = None
_CACHE_TTL_MINUTES = 30

# Realistic fallback prices (approximate recent values — clearly labelled as simulated)
_FALLBACK_PRICES: dict[str, float] = {
    "AAPL": 213.5, "MSFT": 415.2, "NVDA": 875.4, "GOOGL": 176.8, "META": 524.1,
    "AMZN": 193.6, "TSLA": 248.3, "WMT":  68.4,  "KO":   62.1,  "PG":   166.2,
    "JPM":  214.7, "GS":   491.3, "BAC":   40.5,  "XOM":  113.8, "CVX":   161.4,
    "PFE":   27.8, "JNJ":  155.2, "UNH":  571.3,  "BA":   185.6, "HD":   342.7,
}


def _fresh() -> bool:
    if _CACHE_TS is None:
        return False
    return (datetime.now(timezone.utc) - _CACHE_TS).total_seconds() < _CACHE_TTL_MINUTES * 60


def fetch_market_data(tickers: list[str], lookback_days: int = 252) -> tuple[dict[str, dict], bool]:
    """Returns (data_by_ticker, simulated).

    data_by_ticker keys: price, prev_close, return_1d, return_5d, volatility_30d, simulated
    """
    global _PRICE_CACHE, _CACHE_TS

    if _fresh() and _PRICE_CACHE:
        return _PRICE_CACHE, False

    try:
        import yfinance as yf
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days + 10)
        raw = yf.download(tickers, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                          auto_adjust=True, progress=False, threads=True)
        if raw.empty:
            raise ValueError("yfinance returned empty DataFrame")
        closes = raw["Close"] if "Close" in raw.columns else raw
        result: dict[str, dict] = {}
        for t in tickers:
            if t not in closes.columns:
                continue
            s = closes[t].dropna()
            if len(s) < 5:
                continue
            rets = s.pct_change().dropna()
            result[t] = {
                "price": round(float(s.iloc[-1]), 2),
                "prev_close": round(float(s.iloc[-2]), 2) if len(s) > 1 else round(float(s.iloc[-1]), 2),
                "return_1d": round(float(rets.iloc[-1]), 6) if len(rets) >= 1 else 0.0,
                "return_5d": round(float((s.iloc[-1] / s.iloc[-6] - 1)), 6) if len(s) >= 6 else 0.0,
                "volatility_30d": round(float(rets.tail(30).std() * np.sqrt(252)), 6),
                "simulated": False,
            }
        if len(result) >= len(tickers) * 0.8:        # tolerate up to 20% missing
            _PRICE_CACHE = result
            _CACHE_TS = datetime.now(timezone.utc)
            log.info("yfinance fetched %d tickers", len(result))
            return result, False
        raise ValueError(f"Only {len(result)}/{len(tickers)} tickers resolved")
    except Exception as e:
        log.warning("yfinance unavailable (%s); using synthetic fallback prices [SIMULATED]", e)
        rng = np.random.default_rng(42)
        result = {}
        for t in tickers:
            p = _FALLBACK_PRICES.get(t, 100.0)
            drift = rng.normal(0.0002, 0.01)
            vol = rng.uniform(0.18, 0.40)
            result[t] = {
                "price": round(p, 2),
                "prev_close": round(p * (1 - drift), 2),
                "return_1d": round(drift, 6),
                "return_5d": round(rng.normal(0.005, 0.02), 6),
                "volatility_30d": round(vol, 6),
                "simulated": True,
            }
        return result, True


def fetch_history(tickers: list[str], lookback_days: int = 252) -> tuple[pd.DataFrame, bool]:
    """Returns (price_df indexed by date, simulated).  Used for backtesting."""
    try:
        import yfinance as yf
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days + 10)
        raw = yf.download(tickers, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                          auto_adjust=True, progress=False, threads=True)
        closes = raw["Close"] if "Close" in raw.columns else raw
        closes = closes.dropna(axis=1, how="all")
        if not closes.empty:
            log.info("yfinance history: %d rows × %d tickers", len(closes), len(closes.columns))
            return closes, False
        raise ValueError("empty history")
    except Exception as e:
        log.warning("yfinance history unavailable (%s); generating synthetic [SIMULATED]", e)
        return _synthetic_history(tickers, lookback_days), True


def _synthetic_history(tickers: list[str], n_days: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_days)
    data = {}
    for t in tickers:
        p0 = _FALLBACK_PRICES.get(t, 100.0)
        vol = rng.uniform(0.20, 0.35) / np.sqrt(252)
        log_rets = rng.normal(0.0003, vol, size=n_days)
        prices = p0 * np.exp(np.cumsum(log_rets))
        data[t] = prices
    return pd.DataFrame(data, index=dates)
