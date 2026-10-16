"""Company master: ticker, display name, sector, aliases. Aliases are matched with word boundaries.
`cs` aliases are case-sensitive (e.g. 'Apple', 'Coke'). `NEG_CTX` blocks known non-company readings."""
COMPANIES: dict[str, dict] = {
    "AAPL": {"name": "Apple", "sector": "Technology", "aliases": ["Apple Inc", "Apple"], "cs": ["Apple"]},
    "MSFT": {"name": "Microsoft", "sector": "Technology", "aliases": ["Microsoft"], "cs": []},
    "NVDA": {"name": "NVIDIA", "sector": "Technology", "aliases": ["NVIDIA"], "cs": []},
    "GOOGL": {"name": "Alphabet", "sector": "Technology", "aliases": ["Alphabet", "Google"], "cs": ["Google"]},
    "META": {"name": "Meta Platforms", "sector": "Technology", "aliases": ["Meta Platforms", "Facebook"], "cs": ["Facebook"]},
    "AMZN": {"name": "Amazon", "sector": "Consumer", "aliases": ["Amazon"], "cs": ["Amazon"]},
    "TSLA": {"name": "Tesla", "sector": "Consumer", "aliases": ["Tesla"], "cs": []},
    "WMT": {"name": "Walmart", "sector": "Consumer", "aliases": ["Walmart"], "cs": []},
    "KO": {"name": "Coca-Cola", "sector": "Consumer", "aliases": ["Coca-Cola", "Coca Cola", "Coke"], "cs": ["Coke"]},
    "PG": {"name": "Procter & Gamble", "sector": "Consumer", "aliases": ["Procter & Gamble", "P&G"], "cs": ["P&G"]},
    "HD": {"name": "Home Depot", "sector": "Consumer", "aliases": ["Home Depot"], "cs": []},
    "JPM": {"name": "JPMorgan Chase", "sector": "Finance", "aliases": ["JPMorgan Chase", "JPMorgan", "JP Morgan"], "cs": []},
    "GS": {"name": "Goldman Sachs", "sector": "Finance", "aliases": ["Goldman Sachs", "Goldman"], "cs": ["Goldman"]},
    "BAC": {"name": "Bank of America", "sector": "Finance", "aliases": ["Bank of America", "BofA"], "cs": ["BofA"]},
    "XOM": {"name": "Exxon Mobil", "sector": "Energy", "aliases": ["Exxon Mobil", "ExxonMobil", "Exxon"], "cs": []},
    "CVX": {"name": "Chevron", "sector": "Energy", "aliases": ["Chevron"], "cs": []},
    "PFE": {"name": "Pfizer", "sector": "Healthcare", "aliases": ["Pfizer"], "cs": []},
    "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare", "aliases": ["Johnson & Johnson", "J&J"], "cs": ["J&J"]},
    "UNH": {"name": "UnitedHealth", "sector": "Healthcare", "aliases": ["UnitedHealth"], "cs": []},
    "BA": {"name": "Boeing", "sector": "Industrials", "aliases": ["Boeing"], "cs": []},
}
# Regex lookaheads that veto a match (non-company senses)
NEG_CTX = {"Apple": r"(?!\s+(?:juice|pie|orchard|cider|farm|harvest|trees?))",
           "Amazon": r"(?!\s+(?:rainforest|river|basin|jungle|forest))"}

COUNTRIES = ["United States", "U.S.", "China", "Russia", "Ukraine", "Iran", "Israel", "Saudi Arabia", "Japan",
             "India", "Germany", "United Kingdom", "UK", "Taiwan", "Europe", "European Union", "Middle East"]
SECTOR_KEYWORDS = {"Energy": ["oil", "crude", "gas", "energy"], "Finance": ["bank", "lender", "credit", "loan"],
                   "Technology": ["chip", "semiconductor", "software", "cloud", "cyber"],
                   "Healthcare": ["drug", "pharma", "treatment", "clinical"],
                   "Consumer": ["retail", "retailer", "consumer", "beverage"]}
