import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from config import sentiment_input_path, filings_index_path
from html.parser import HTMLParser
import re
import pandas as pd

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--ticker", required=True)
args = parser.parse_args()

INDEX_CSV  = filings_index_path(args.ticker)
OUTPUT_CSV = sentiment_input_path(args.ticker)

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
        return re.sub(r"<[^>]+>", " ", text)


# EXTRACT PRIMARY DOCUMENT FROM full-submission.txt
def extract_primary_document_from_submission(submission_path: Path, form_type: str) -> str | None:
    if not submission_path.exists():
        return None

    raw = submission_path.read_text(encoding="utf-8", errors="replace")
    doc_blocks = re.split(r"<DOCUMENT>", raw, flags=re.IGNORECASE)

    for block in doc_blocks[1:]:
        type_match = re.search(r"<TYPE>\s*([^\s<]+)", block, re.IGNORECASE)
        if not type_match:
            continue

        doc_type   = type_match.group(1).strip().upper()
        is_primary = (
            doc_type == form_type.upper() or
            doc_type.startswith(form_type.upper()) or
            doc_type in {"10-K405", "10-KSB", "10-QSB", "8-K/A", "10-K/A", "10-Q/A"}
        )

        if not is_primary:
            continue

        text_match = re.search(r"<TEXT>(.*?)</TEXT>", block, re.IGNORECASE | re.DOTALL)
        if text_match:
            return text_match.group(1).strip()

        text_start = re.search(r"<TEXT>", block, re.IGNORECASE)
        if text_start:
            return block[text_start.end():].strip()

    return None


# JUNK DETECTOR
def is_directory_junk(text: str) -> bool:
    junk_signals = [
        "Parent Directory", "global-search-form",
        "Directory Listing", "index-headers.html",
        "Last Modified", "_setAccount", "UA-30394047",
    ]
    return sum(1 for s in junk_signals if s in text) >= 2


# STRIP TAIL BOILERPLATE
# Removes signatures, certifications, exhibit lists
# that appear AFTER the real content — these add
# noise to LM word counts without adding signal
def strip_tail_boilerplate(text: str) -> str:
    # These patterns mark the end of real content
    tail_markers = [
        r"pursuant to the requirements of the securities exchange act",
        r"signatures?\s+pursuant",
        r"certifications?\s+pursuant to",
        r"exhibit\s+index",
        r"list of exhibits",
        r"index to exhibits",
        r"incorporated herein by reference",
        r"power of attorney",
        r"consent of independent",
        r"rule\s+13a-14",
        r"sarbanes.oxley",
    ]
    combined = re.compile("|".join(tail_markers), re.IGNORECASE)
    match    = combined.search(text)
    if match:
        # Keep everything before the tail marker
        return text[:match.start()].strip()
    return text

# CLEAN TEXT
def clean_text(raw: str) -> str:
    # Strip HTML
    text = strip_html(raw)

    # Remove leftover tags
    text = re.sub(r"<[^>]{1,200}>", " ", text)

    # Remove XBRL artifacts
    text = re.sub(r"\b(ix|xbrl|xmlns|xlink|gaap|us-gaap)\s*:\s*\w+", " ", text, flags=re.IGNORECASE)

    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)

    # Remove lines that are mostly numeric (tables, page numbers)
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        alpha_chars = sum(c.isalpha() for c in line)
        total_chars = len(line)
        if total_chars > 0 and (alpha_chars / total_chars) < 0.3:
            continue
        if len(line) < 25:
            continue
        clean_lines.append(line)

    text = " ".join(clean_lines)
    text = re.sub(r"\s+", " ", text).strip()

    return text

# SECTION EXTRACTION
# No character caps — let full sections through
# for better LM word count coverage
def extract_relevant_section(text: str, form_type: str) -> str:
    # Strip tail boilerplate first regardless of form type
    text = strip_tail_boilerplate(text)

    if form_type == "8-K":
        # Extract all Item body texts concatenated
        item_pattern = re.compile(
            r"item\s+\d+[\.\d]*[^\n]*\n(.*?)(?=item\s+\d+[\.\d]*[^\n]*\n|$)",
            re.IGNORECASE | re.DOTALL
        )
        matches = item_pattern.findall(text)
        if matches:
            bodies = [m.strip() for m in matches if len(m.strip()) > 80]
            if bodies:
                return " ".join(bodies)   # no cap — full item bodies

        return text   # fallback: full cleaned text, no cap

    # ── 10-Q and 10-K: extract MD&A ──
    mda_start = re.compile(
        r"(item\s*[27][\.\s]*"
        r"(?:management[\s\'s]*"
        r"(?:discussion|discussion and analysis)"
        r"(?:\s+of\s+financial\s+condition)?)"
        r"|"
        r"management[\s\'s]+discussion\s+and\s+analysis)",
        re.IGNORECASE
    )
    mda_end = re.compile(
        r"(item\s*[3-9]\b"
        r"|quantitative\s+and\s+qualitative"
        r"|market\s+risk"
        r"|controls\s+and\s+procedures"
        r"|legal\s+proceedings"
        r"|risk\s+factors)",
        re.IGNORECASE
    )

    start_match = mda_start.search(text)
    if not start_match:
        # MD&A not found — return full cleaned text, no cap
        return text

    start_pos = start_match.end()
    end_match = mda_end.search(text, start_pos + 200)
    end_pos   = end_match.start() if end_match else len(text)  # no artificial cap

    section = text[start_pos:end_pos].strip()

    # If section is suspiciously short, fall back to full text
    if len(section) < 200:
        return text

    return section


# MAIN PIPELINE
def preprocess_filings():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INDEX_CSV)
    print(f"[INFO] Total filings to process: {len(df)}")

    records      = []
    failed       = 0
    junk_skipped = 0

    for i, row in df.iterrows():
        file_path  = Path(row["file_path"])
        form_type  = row["form_type"]
        date       = row["date"]
        accession  = row["accession_number"]

        submission_path = file_path.parent / "full-submission.txt"

        # Extract from <DOCUMENT> block
        raw_text = extract_primary_document_from_submission(submission_path, form_type)

        if not raw_text:
            if file_path.exists():
                raw_text = file_path.read_text(encoding="utf-8", errors="replace")
            else:
                print(f"  [WARN] No text found: {accession}")
                failed += 1
                continue

        if is_directory_junk(raw_text):
            print(f"  [JUNK] {accession}")
            junk_skipped += 1
            failed += 1
            continue

        clean  = clean_text(raw_text)
        section = extract_relevant_section(clean, form_type)

        if len(section) < 100:
            print(f"  [WARN] Too short after cleaning: {accession}")
            failed += 1
            continue

        records.append({
            "date":             date,
            "form_type":        form_type,
            "accession_number": accession,
            "clean_text":       section,
            "word_count":       len(section.split())   # track coverage
        })

        if (i + 1) % 50 == 0:
            print(f"  [PROGRESS] {i+1}/{len(df)} processed...")

    output_df = pd.DataFrame(records)
    output_df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n[DONE] Successfully processed : {len(records)}")
    print(f"[DONE] Junk skipped            : {junk_skipped}")
    print(f"[DONE] Failed                  : {failed - junk_skipped}")
    print(f"[DONE] Output saved to         : {OUTPUT_CSV}")

    print(f"\n[WORD COUNT STATS]")
    print(output_df["word_count"].describe())

    print(f"\n[SAMPLE — first 600 chars of first record]")
    print(output_df.iloc[0]["clean_text"][:600])


if __name__ == "__main__":
    preprocess_filings()