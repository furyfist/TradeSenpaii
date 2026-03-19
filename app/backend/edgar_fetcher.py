"""
TradeSenpai — EDGAR Filing Fetcher
====================================
Fetches actual SEC filing text from EDGAR API.
Extracts Risk Factors + MD&A sections.
Highlights sentences that match LM risk signals.
"""

import re
import requests
import pandas as pd
from pathlib import Path
from typing import Optional

EDGAR_HEADERS = {"User-Agent": "TradeSenpai dev@tradesenpai.com"}
BASE_URL      = "https://data.sec.gov"

TICKER_CIK = {
    "AAPL":  "0000320193",
    "JNJ":   "0000200406",
    "KO":    "0000021344",
    "PG":    "0000080424",
    "WMT":   "0000104169",
    "GOOGL": "0001652044",
}

# Sections we care about — ordered by priority
TARGET_SECTIONS = [
    "risk factors",
    "management",
    "liquidity",
    "legal proceedings",
    "quantitative and qualitative",
]

# LM risk word patterns (simplified subset for highlighting)
NEGATIVE_PATTERNS = [
    r"\b(loss|losses|decline|declining|decreased|decrease|adverse|adversely)\b",
    r"\b(impairment|write.?off|write.?down|deficit|default|bankruptcy)\b",
    r"\b(deteriorat\w+|weaken\w+|worsen\w+|downturn)\b",
]

UNCERTAINTY_PATTERNS = [
    r"\b(uncertain\w*|unpredictab\w*|volatil\w*|fluctuat\w*)\b",
    r"\b(may|might|could|should|would)\s+\w+\s+(affect|impact|result|cause)\b",
    r"\b(no assurance|cannot guarantee|cannot predict|difficult to predict)\b",
]

LITIGATION_PATTERNS = [
    r"\b(litigation|lawsuit|legal proceedings|legal action|claim[s]?)\b",
    r"\b(plaintiff|defendant|court|judgment|settlement|damages)\b",
    r"\b(regulatory|enforcement|investigation|penalty|penalties|fine[s]?)\b",
]


def get_recent_filings(ticker: str, form_types: list = None) -> list[dict]:
    """
    Returns list of recent filings for a ticker from EDGAR submissions API.
    """
    if form_types is None:
        form_types = ["10-K", "10-Q"]

    cik = TICKER_CIK.get(ticker.upper())
    if not cik:
        raise ValueError(f"Unknown ticker: {ticker}")

    url = f"{BASE_URL}/submissions/CIK{cik}.json"
    r   = requests.get(url, headers=EDGAR_HEADERS, timeout=10)
    r.raise_for_status()

    data    = r.json()
    recent  = data["filings"]["recent"]

    filings = []
    for i, form in enumerate(recent["form"]):
        if form not in form_types:
            continue
        filings.append({
            "ticker":    ticker,
            "form":      form,
            "date":      recent["filingDate"][i],
            "accession": recent["accessionNumber"][i],
        })

    return filings[:20]   # last 20 qualifying filings


def get_filing_index(accession: str, cik: str) -> list[dict]:
    """
    Returns the index of documents in a filing.
    Needed to find the actual .htm/.txt document.
    """
    acc_clean = accession.replace("-", "")
    url = f"{BASE_URL}/Archives/edgar/data/{int(cik)}/{acc_clean}/{accession}-index.json"

    r = requests.get(url, headers=EDGAR_HEADERS, timeout=10)
    r.raise_for_status()

    data  = r.json()
    files = data.get("directory", {}).get("item", [])

    return files


def find_primary_document(files: list[dict]) -> Optional[str]:
    """
    Finds the primary .htm filing document from the index.
    Prefers the main 10-K/10-Q document over exhibits.
    """
    # prefer files with these name patterns
    priority = ["10k", "10q", "form10", "annual", "quarterly", "report"]

    htm_files = [
        f for f in files
        if f.get("name", "").lower().endswith((".htm", ".html"))
        and not any(x in f.get("name","").lower()
                    for x in ["ex", "exhibit", "r1.", "r2.", "r3.", "r4."])
    ]

    if not htm_files:
        return None

    # sort by priority keywords in filename
    def score(f):
        name = f.get("name", "").lower()
        return sum(p in name for p in priority)

    htm_files.sort(key=score, reverse=True)
    return htm_files[0]["name"]


def fetch_filing_text(accession: str, cik: str, doc_name: str) -> str:
    """
    Fetches the raw HTML of a filing document and strips to plain text.
    """
    acc_clean = accession.replace("-", "")
    url = f"{BASE_URL}/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc_name}"

    r = requests.get(url, headers=EDGAR_HEADERS, timeout=30)
    r.raise_for_status()

    # strip HTML tags
    text = re.sub(r"<[^>]+>", " ", r.text)
    # collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # remove page headers/footers noise
    text = re.sub(r"Table of Contents", "", text, flags=re.IGNORECASE)

    return text.strip()


def extract_section(text: str, section_name: str, max_chars: int = 8000) -> str:
    """
    Extracts a named section from filing text.
    Looks for the section header and returns text until the next major section.
    """
    # build pattern to find section header
    pattern = re.compile(
        rf"(?i)(item\s+\d+[a-z]?\s*[.\-:–]?\s*{re.escape(section_name)})",
        re.IGNORECASE
    )

    match = pattern.search(text)
    if not match:
        return ""

    start = match.start()
    # find the next item section as end boundary
    next_item = re.search(
        r"(?i)item\s+\d+[a-z]?\s*[.\-:–]",
        text[start + 100:]   # skip current header
    )
    end = start + 100 + next_item.start() if next_item else start + max_chars

    return text[start:min(end, start + max_chars)].strip()


def split_into_sentences(text: str) -> list[str]:
    """Splits text into sentences, filtering noise."""
    # split on sentence endings
    sentences = re.split(r"(?<=[.!?])\s+", text)
    # filter: min 20 chars, max 500 chars, no pure numbers/symbols
    sentences = [
        s.strip() for s in sentences
        if 20 < len(s.strip()) < 500
        and re.search(r"[a-zA-Z]{3,}", s)
    ]
    return sentences


def classify_sentence(sentence: str) -> list[str]:
    """
    Returns list of risk categories triggered by this sentence.
    Categories: negative, uncertainty, litigation
    """
    s       = sentence.lower()
    tags    = []

    if any(re.search(p, s) for p in NEGATIVE_PATTERNS):
        tags.append("negative")

    if any(re.search(p, s) for p in UNCERTAINTY_PATTERNS):
        tags.append("uncertainty")

    if any(re.search(p, s) for p in LITIGATION_PATTERNS):
        tags.append("litigation")

    return tags


def get_highlighted_filing(
    ticker: str,
    accession: str,
    max_sentences: int = 80,
) -> dict:
    """
    Main function — fetches a filing and returns highlighted sentences.

    Returns:
    {
        ticker, accession, date, form,
        sections: [
            {
                name: "Risk Factors",
                sentences: [
                    {
                        text: "...",
                        tags: ["negative", "uncertainty"],
                        highlighted: bool
                    }
                ]
            }
        ],
        stats: { total, highlighted, negative, uncertainty, litigation }
    }
    """
    cik = TICKER_CIK.get(ticker.upper())
    if not cik:
        raise ValueError(f"Unknown ticker: {ticker}")

    print(f"[INFO] Fetching filing {accession} for {ticker}...")

    # get filing index
    files       = get_filing_index(accession, cik)
    primary_doc = find_primary_document(files)

    if not primary_doc:
        raise ValueError(f"Could not find primary document for {accession}")

    print(f"[INFO] Primary document: {primary_doc}")

    # fetch full text
    full_text = fetch_filing_text(accession, cik, primary_doc)
    print(f"[INFO] Fetched {len(full_text):,} chars")

    # extract sections
    sections_out = []
    total_sentences   = 0
    total_highlighted = 0
    tag_counts        = {"negative": 0, "uncertainty": 0, "litigation": 0}

    section_map = {
        "Risk Factors":      "risk factors",
        "MD&A":              "management",
        "Legal Proceedings": "legal proceedings",
        "Liquidity":         "liquidity",
    }

    for section_label, section_key in section_map.items():
        section_text = extract_section(full_text, section_key, max_chars=12000)
        if not section_text:
            continue

        sentences = split_into_sentences(section_text)
        sentences = sentences[:max_sentences // len(section_map)]

        sentence_objs = []
        for s in sentences:
            tags        = classify_sentence(s)
            highlighted = len(tags) > 0

            sentence_objs.append({
                "text":        s,
                "tags":        tags,
                "highlighted": highlighted,
            })

            total_sentences += 1
            if highlighted:
                total_highlighted += 1
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if sentence_objs:
            sections_out.append({
                "name":      section_label,
                "sentences": sentence_objs,
            })

    return {
        "ticker":    ticker,
        "accession": accession,
        "sections":  sections_out,
        "stats": {
            "total":       total_sentences,
            "highlighted": total_highlighted,
            "pct":         round(total_highlighted / max(total_sentences, 1) * 100, 1),
            **tag_counts,
        },
    }