import os 
import re
import pandas as pd
from pathlib import Path
from sec_edgar_downloader import Downloader

# Config
COMPANY_NAME    = "TradeSenapi"
EMAIL           = "tradesenpai@email.com"       # EDGAR requires this — replace it
TICKER          = "KO"
FILING_TYPES    = ["8-K", "10-Q", "10-K"]
DOWNLOAD_DIR    = Path("data/raw/sec_filings")
INDEX_CSV       = DOWNLOAD_DIR / "filings_index.csv"

# Download all the filings
def download_all_filings():
    dl = Downloader(COMPANY_NAME, EMAIL, DOWNLOAD_DIR)

    for filing_type in FILING_TYPES:
        print(f"\n[DOWNLOADING] {filing_type} filings for {TICKER}...")
        # limit = None fethches everything available on EDGAR
        dl.get(filing_type, TICKER, limit=None,  download_details=True)
        print(f"[Done] {filing_type} complete...")

# walk the downloaded folder structure and build filings_index.csv

def extract_date_from_accession(accession: str) -> str | None:
    """
    Accession number are formatted as: XXXXXXXXXX-YY-NNNNNN
    The YY is the 2-digit year but that`s not precise enough
    We instead read the filing-details.xml that sec_edgar_downloader
    also saves, which contains the exact filing date
    """
    return None # fallback = we will get date from filings details below

def parse_filing_date(filing_dir: Path) -> str | None:
    """
    sec_edger_downloader saves a 'filing-details.xml' inside each accession folder.
    we pull the filing date from there
    """
    details_file = filing_dir / "filing-details.xml"
    if not details_file.exists():
        return None
    
    content = details_file.read_text(encoding="utf-8", errors="replace")

    # The filling date in a tag like: <filing-date> 1994-02-15 </filing-date>
    match = re.search(r"<filing-date>(\d{4}-\d{2}-\d{2})</filing-date>", content)
    if match:
        return match.group(1)
    
    # fallback: try <date-filed> tag (older EDGAR format)
    match = re.search(r"<date-filed>(\d{4}-\d{2}-\d{2})</date-filed>", content)
    if match:
        return match.group(1)

    return None

def find_primary_document(filing_dir: Path) -> Path | None:
    """
    sec_edgar_downloader names the main file 'primary-document.html' or
    'primary-document.htm' or occasionally 'primary-document.txt'.
    Returns the path if found.
    """
    for ext in ["primary-document.html", "primary-document.htm", "primary-document.txt"]:
        candidate = filing_dir / ext
        if candidate.exists():
            return candidate
    return None

def build_filings_index() -> pd.DataFrame:
    """
    Walks the sec_edgar_downloader output structure and builds a clean index:
    date | form_type | accession_number | file_path
    """
    base = DOWNLOAD_DIR / "sec-edgar-filings" / TICKER
    records = []

    for filing_type in FILING_TYPES:
        type_dir = base / filing_type
        if not type_dir.exists():
            print(f"[WARN] No Directory found for {filing_type} at {type_dir}")
            continue

        accession_dirs = [d for d in type_dir.iterdir() if d.is_dir()]
        print(f"[INDEX] {filing_type}: {len(accession_dirs)} filings found")

        for acc_dir in accession_dirs:
            accession_number = acc_dir.name

            # Get data from filing-details.xml
            date = parse_filing_date(acc_dir)
            if not date:
                print(f"  [WARN] Could not parse date for {accession_number} — skipping")
                continue

            # Get primary document path
            primary_doc = find_primary_document(acc_dir)
            if not primary_doc:
                print(f"  [WARN] No primary document for {accession_number} — skipping")
                continue

            records.append({
                "date":             date,
                "form_type":        filing_type,
                "accession_number": accession_number,
                "file_path":        str(primary_doc)
            })

    df = pd.DataFrame(records)
    if df.empty:
        print("[ERROR] No filings indexed. Check if download completed successfully.")
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(INDEX_CSV, index=False)
    print(f"\n[INDEX SAVED] {len(df)} total filings → {INDEX_CSV}")
    print(df["form_type"].value_counts().to_string())

    return df

# entry point
if __name__ == "__main__":
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1 — Download
    download_all_filings()

    # Step 2 — Build index
    df = build_filings_index()

    print("\n[PREVIEW] First 5 rows of filings_index.csv:")
    print(df.head().to_string(index=False))