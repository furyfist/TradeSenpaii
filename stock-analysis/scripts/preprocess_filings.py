import re
import pandas as pd
from pathlib import Path
from html.parser import HTMLParser

# config
INDEX_CSV = Path("data/raw/sec_filingsstrip_html/filings_index.csv")
OUTPUT_CSV = Path("data/processed/sec_sentiment_input.csv")

# HTML Stripper (uffff)
class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self,d):
        self.fed.append(d)

    def get_data(self):
        return " ".join(self.fed)
    
def strip_html(text: str) -> str:
    stripper = HTMLStripper()
    try:
        stripper.feed(text)
        return stripper.get_data()
    except Exception:
        return text

def clean_sec_text(raw: str) -> str:
    # Strip HTML tags
    text = strip_html(raw)

    # Remove SEC header block (everything before <DOCUMENT> or up to first real sentence)
    text = re.sub(r"-----BEGIN PRIVACY.*?-----END PRIVACY-ENHANCED MESSAGE-----", "", text, flags=re.DOTALL)
    text = re.sub(r"<SEC-DOCUMENT>.*?<DOCUMENT>", "", text, flags=re.DOTALL)
    text = re.sub(r"<SEC-HEADER>.*?</SEC-HEADER>", "", text, flags=re.DOTALL)

    # Remove XBRL/XML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove URLs
    text = re.sub(r"http\S+", " ", text)

    # Remove special characters, keep letters/numbers/punctuation
    text = re.sub(r"[^\w\s\.\,\!\?\;\:\-\(\)]", " ", text)

    # Collapse excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove lines that are purely numbers or very short (table artifacts)
    lines = text.split(".")
    lines = [l.strip() for l in lines if len(l.strip()) > 40]
    text = ". ".join(lines)

    return text

# Section Extraction (focus on relevent sections only, other wise it will add noise into training)
def extract_relevent_section(text: str, form_type: str) -> str:
    """
    For 8-K: the whole document is usually short — use all of it
    For 10-Q/10-K: extract MD&A section only (most sentiment-rich)
    If MD&A not found, fall back to first 3000 chars
    """

    if form_type == "8-K":
        return text[:5000] # 8-Ks are short, take the whole thing (capped)
    
    # For 10-Q and 10-K : find MD&A Section
    mda_pattern = re.compile(
        r"(management.{0,10}discussion.{0,10}analysis)(.*?)(quantitative|item\s+[34]|risk factor)",
        re.IGNORECASE | re.DOTALL
    )
    match = mda_pattern.search(text)
    if match:
        section = match.group(2).strip()
        return section[:6000]   # Cap at 6000 chars for FinBERT chunking later

    # Fallback: first 3000 characters
    return text[:3000]

# Main Pipeline
def preprocess_filings():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INDEX_CSV)
    print(f"[INFO] Total filings to process: {len(df)}")

    records = []
    failed = 0

    for i, row in df.iterrows():
        filepath = Path(row["file_path"])
        form_type = row["form_type"]
        date = row["date"]
        accession = row["accession_number"]

        if not filepath.exists():
            print(f"[WARN] File not found: {filepath}")
            failed += 1
            continue

        try:
            raw_text = filepath.read_text(encoding='utf-8', errors="replace")
        except Exception as e:
            print(f"  [WARN] Could not read {filepath}: {e}")
            failed += 1
            continue

        # Clean and extract relevent section
        clean_text = clean_sec_text(raw_text)
        section = extract_relevent_section(clean_text, form_type)

        # Skip if result is too short to be meaningful
        if len(section) < 100:
            print(f"  [WARN] Text too short after cleaning for {accession} — skipping")
            failed += 1
            continue

        records.append({
            "date": date,
            "form_type": form_type,
            "accession_number": accession,
            "clean_text": section
        })

        if (i+1) % 50 == 0:
            print(f"[Progress] {i+1}/{len(df)} processed...")

    output_df = pd.DataFrame(records)
    output_df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n[DONE] Successfully processed: {len(records)}")
    print(f"[DONE] Failed/skipped:          {failed}")
    print(f"[DONE] Output saved to:         {OUTPUT_CSV}")
    print(f"\n[PREVIEW]")
    print(output_df[["date", "form_type", "clean_text"]].head(3).to_string(index=False))


if __name__ == "__main__":
    preprocess_filings()
