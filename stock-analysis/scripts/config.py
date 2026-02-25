# TradeSenpai V2 — Central Ticker Configuration

TICKERS = {
    "KO": {
        "cik":      "0000021344",
        "name":     "Coca-Cola",
        "sector":   "Consumer Staples",
    },
    "JNJ": {
        "cik":      "0000200406",
        "name":     "Johnson & Johnson",
        "sector":   "Healthcare",
    },
    "PG": {
        "cik":      "0000080424",
        "name":     "Procter & Gamble",
        "sector":   "Consumer Staples",
    },
    "WMT": {
        "cik":      "0000104169",
        "name":     "Walmart",
        "sector":   "Retail",
    },
    "AAPL": {
        "cik":      "0000320193",
        "name":     "Apple",
        "sector":   "Technology",
    },
    "GOOGL": {
        "cik":      "0001652044",
        "name":     "Alphabet",
        "sector":   "Technology",
    },
}

FILING_TYPES  = ["8-K", "10-Q", "10-K"]
REQUEST_DELAY = 0.5

# ── Path helpers 
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent   # stock-analysis/

def raw_dir(ticker: str) -> Path:
    return ROOT_DIR / "data" / "raw" / "sec_filings" / ticker

def processed_dir(ticker: str) -> Path:
    p = ROOT_DIR / "data" / "processed" / ticker
    p.mkdir(parents=True, exist_ok=True)
    return p

def filings_index_path(ticker: str) -> Path:
    return raw_dir(ticker) / "filings_index.csv"

def sentiment_input_path(ticker: str) -> Path:
    return processed_dir(ticker) / "sec_sentiment_input.csv"

def sentiment_features_path(ticker: str) -> Path:
    return processed_dir(ticker) / "sec_sentiment_features.csv"

def merged_dataset_path(ticker: str) -> Path:
    return processed_dir(ticker) / "merged_dataset.csv"

def cleaned_prices_path(ticker: str) -> Path:
    return processed_dir(ticker) / "cleaned.csv"

def model_path(ticker: str) -> Path:
    return ROOT_DIR.parent / "app" / "backend" / "model" / f"transformer_{ticker}.pt"