import re
import pandas as pd
from pathlib import Path
from html.parser import HTMLParser

# Config
INDEX_CSV   = Path("data/raw/sec_filings/filings_index.csv")
OUTPUT_CSV  = Path("data/processed/sec_sentiment_input.csv")

# HTML STRIPPER
class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return " ".join(self.fed)


def strip_html(text: str) -> str:
    stripper = HTMLStripper()
    try:
        stripper.feed(text)
        return stripper.get_data()
    except Exception:
        # HTMLParser can choke on malformed HTML — fall back to regex strip
        return re.sub(r"<[^>]+>", " ", text)


# CORE: Extract primary document text from
def extract_primary_document_from_submission(submission_path: Path, form_type: str) -> str | None:
    """
    full-submission.txt bundles all documents like:
    
    <DOCUMENT>
    <TYPE>8-K
    <SEQUENCE>1
    <TEXT>
    ...actual filing content...
    </TEXT>
    </DOCUMENT>
    <DOCUMENT>
    <TYPE>EX-99
    ...exhibit, skip this...
    </DOCUMENT>
    
    We find the first <DOCUMENT> block whose <TYPE> matches the filing type
    and extract the <TEXT> content from it.
    """
    if not submission_path.exists():
        return None

    raw = submission_path.read_text(encoding="utf-8", errors="replace")

    # Split into individual document blocks
    doc_blocks = re.split(r"<DOCUMENT>", raw, flags=re.IGNORECASE)

    for block in doc_blocks[1:]:   # skip everything before first <DOCUMENT>
        # Get the TYPE of this document block
        type_match = re.search(r"<TYPE>\s*([^\s<]+)", block, re.IGNORECASE)
        if not type_match:
            continue

        doc_type = type_match.group(1).strip().upper()

        # We want the primary filing, not exhibits
        # Accept exact match OR the form type as prefix (e.g. 10-K405 counts as 10-K)
        is_primary = (
            doc_type == form_type.upper() or
            doc_type.startswith(form_type.upper()) or
            doc_type in {"10-K405", "10-KSB", "10-QSB", "8-K/A", "10-K/A", "10-Q/A"}
        )

        if not is_primary:
            continue

        # Extract content between <TEXT> and </TEXT>
        text_match = re.search(r"<TEXT>(.*?)</TEXT>", block, re.IGNORECASE | re.DOTALL)
        if text_match:
            return text_match.group(1).strip()

        # Some older filings don't have </TEXT> closing tag — take everything after <TEXT>
        text_start = re.search(r"<TEXT>", block, re.IGNORECASE)
        if text_start:
            return block[text_start.end():].strip()

    return None

# DETECT JUNK: Is this an EDGAR directory page?
def is_directory_junk(text: str) -> bool:
    """
    EDGAR index/directory pages have fingerprints we can detect.
    If multiple are present, it's junk not a real filing.
    """
    junk_signals = [
        "Parent Directory",
        "global-search-form",
        "Directory Listing",
        "index-headers.html",
        "Last Modified",
        "_setAccount",         # Google Analytics tag — never in real filings
        "UA-30394047",         # EDGAR's GA ID
    ]
    hits = sum(1 for signal in junk_signals if signal in text)
    return hits >= 2


# Text cleaning
def clean_text(raw: str) -> str:
    # Strip HTML
    text = strip_html(raw)

    # Remove leftover angle-bracket tags missed by HTMLParser
    text = re.sub(r"<[^>]{1,200}>", " ", text)

    # Remove XBRL namespace artifacts
    text = re.sub(r"\b(ix|xbrl|xmlns|xlink|gaap|us-gaap)\s*:\s*\w+", " ", text, flags=re.IGNORECASE)

    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)

    # Remove lines that look like table data (mostly numbers/symbols)
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that are >70% numeric/punctuation — table rows, page numbers etc
        alpha_chars  = sum(c.isalpha() for c in line)
        total_chars  = len(line)
        if total_chars > 0 and (alpha_chars / total_chars) < 0.3:
            continue
        # Skip very short lines (headers, labels)
        if len(line) < 30:
            continue
        clean_lines.append(line)

    text = " ".join(clean_lines)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text

# Section Extraction
def extract_relevant_section(text: str, form_type: str) -> str:
    if form_type == "8-K":
        # 8-Ks are short — use the whole thing
        return text[:5000]

    # For 10-Q and 10-K: extract MD&A section
    # Real filings use many variations of this heading
    mda_start_pattern = re.compile(
        r"(item\s*[27][\.\s]*"                          # Item 2. or Item 7.
        r"(?:management[\s\'s]*"
        r"(?:discussion|discussion and analysis)"
        r"(?:\s+of\s+financial\s+condition)?)"          # optional suffix
        r"|"
        r"management[\s\'s]+discussion\s+and\s+analysis)",  # or standalone heading
        re.IGNORECASE
    )

    # Where MD&A ends — next major section
    mda_end_pattern = re.compile(
        r"(item\s*[3-9]\b"
        r"|quantitative\s+and\s+qualitative"
        r"|market\s+risk"
        r"|controls\s+and\s+procedures"
        r"|legal\s+proceedings"
        r"|risk\s+factors)",
        re.IGNORECASE
    )

    start_match = mda_start_pattern.search(text)
    if not start_match:
        # MD&A not found — fall back to first 3000 chars
        return text[:3000]

    start_pos   = start_match.end()
    end_match   = mda_end_pattern.search(text, start_pos + 200)  # +200 to skip the heading itself
    end_pos     = end_match.start() if end_match else start_pos + 8000

    section = text[start_pos:end_pos].strip()
    return section[:6000]   # Cap for FinBERT chunking


# Main Pipeline
def preprocess_filings():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INDEX_CSV)
    print(f"[INFO] Total filings to process: {len(df)}")

    records      = []
    failed       = 0
    junk_skipped = 0

    for i, row in df.iterrows():
        file_path = Path(row["file_path"])
        form_type = row["form_type"]
        date      = row["date"]
        accession = row["accession_number"]

        # Always use full-submission.txt — it's the reliable source
        submission_path = file_path.parent / "full-submission.txt"

        # ── Extract raw text from the correct <DOCUMENT> block ──
        raw_text = extract_primary_document_from_submission(submission_path, form_type)

        if not raw_text:
            # Fallback: try reading primary-document directly
            if file_path.exists():
                raw_text = file_path.read_text(encoding="utf-8", errors="replace")
            else:
                print(f"  [WARN] No text found for {accession}")
                failed += 1
                continue

        # ── Detect and skip directory index junk ──
        if is_directory_junk(raw_text):
            print(f"  [JUNK] Directory page detected, skipping: {accession}")
            junk_skipped += 1
            failed += 1
            continue

        # ── Clean text ──
        clean = clean_text(raw_text)

        # ── Extract relevant section ──
        section = extract_relevant_section(clean, form_type)

        if len(section) < 100:
            print(f"  [WARN] Text too short after cleaning: {accession}")
            failed += 1
            continue

        records.append({
            "date":             date,
            "form_type":        form_type,
            "accession_number": accession,
            "clean_text":       section
        })

        if (i + 1) % 50 == 0:
            print(f"  [PROGRESS] {i+1}/{len(df)} processed...")

    output_df = pd.DataFrame(records)
    output_df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n[DONE] Successfully processed : {len(records)}")
    print(f"[DONE] Junk pages skipped      : {junk_skipped}")
    print(f"[DONE] Failed/other skipped    : {failed - junk_skipped}")
    print(f"[DONE] Output saved to         : {OUTPUT_CSV}")

    # Sanity check — show a real text sample
    if not output_df.empty:
        sample = output_df.iloc[0]["clean_text"]
        print(f"\n[SAMPLE] First 500 chars of first record:")
        print(sample[:500])


if __name__ == "__main__":
    preprocess_filings()