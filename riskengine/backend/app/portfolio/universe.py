"""Index universe: 20 S&P 100 stocks with static metadata.
Weights and prices are fetched from yfinance at runtime; this file only defines identity and sector.
"""
from __future__ import annotations

INDEX_UNIVERSE: dict[str, dict] = {
    "AAPL": {"name": "Apple",             "sector": "Technology",  "base_weight": 0.075},
    "MSFT": {"name": "Microsoft",         "sector": "Technology",  "base_weight": 0.075},
    "NVDA": {"name": "NVIDIA",            "sector": "Technology",  "base_weight": 0.060},
    "GOOGL": {"name": "Alphabet",         "sector": "Technology",  "base_weight": 0.055},
    "META": {"name": "Meta Platforms",    "sector": "Technology",  "base_weight": 0.045},
    "AMZN": {"name": "Amazon",            "sector": "Consumer",    "base_weight": 0.065},
    "TSLA": {"name": "Tesla",             "sector": "Consumer",    "base_weight": 0.045},
    "WMT": {"name": "Walmart",            "sector": "Consumer",    "base_weight": 0.040},
    "KO":  {"name": "Coca-Cola",          "sector": "Consumer",    "base_weight": 0.035},
    "PG":  {"name": "Procter & Gamble",   "sector": "Consumer",    "base_weight": 0.035},
    "JPM": {"name": "JPMorgan Chase",     "sector": "Finance",     "base_weight": 0.065},
    "GS":  {"name": "Goldman Sachs",      "sector": "Finance",     "base_weight": 0.045},
    "BAC": {"name": "Bank of America",    "sector": "Finance",     "base_weight": 0.040},
    "XOM": {"name": "Exxon Mobil",        "sector": "Energy",      "base_weight": 0.050},
    "CVX": {"name": "Chevron",            "sector": "Energy",      "base_weight": 0.040},
    "PFE": {"name": "Pfizer",             "sector": "Healthcare",  "base_weight": 0.040},
    "JNJ": {"name": "Johnson & Johnson",  "sector": "Healthcare",  "base_weight": 0.045},
    "UNH": {"name": "UnitedHealth",       "sector": "Healthcare",  "base_weight": 0.040},
    "BA":  {"name": "Boeing",             "sector": "Industrials", "base_weight": 0.035},
    "HD":  {"name": "Home Depot",         "sector": "Consumer",    "base_weight": 0.035},
}

SECTORS = sorted({v["sector"] for v in INDEX_UNIVERSE.values()})
TICKERS = list(INDEX_UNIVERSE.keys())
