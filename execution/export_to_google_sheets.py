"""
export_to_google_sheets.py — Export enriched GMB leads to Google Sheets format.

Directive: directives/export_to_google_sheets.md

Columns:
    - Name
    - Website
    - Phone
    - Email
    - Score
    - Facebook Link
    - Instagram Link
    - TikTok Link
    - X Link
    - LinkedIn Link

Usage:
    # Export latest enriched JSON to Google Sheets CSV:
    python execution/export_to_google_sheets.py

    # Specify input file and push to a Google Sheet:
    python execution/export_to_google_sheets.py .tmp/enriched_leads_*.json --sheet-url "https://docs.google.com/spreadsheets/d/..."
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_env, get_logger, format_error, TMP_DIR, PROJECT_ROOT  # noqa: E402

logger = get_logger("export_to_google_sheets")

HEADERS = [
    "Name",
    "Website",
    "Phone",
    "Email",
    "Score",
    "Facebook Link",
    "Instagram Link",
    "TikTok Link",
    "X Link",
    "LinkedIn Link",
]


# ===========================================================================
# 1. Extraction & Data Normalization
# ===========================================================================

def find_latest_enriched_file() -> Path | None:
    """Find the most recently modified enriched JSON file in .tmp/."""
    pattern = str(TMP_DIR / "enriched_leads_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    return Path(latest)


def format_lead_row(lead: dict) -> list[str]:
    """Format a single lead dict into the target column row."""
    # Name
    name = lead.get("business_name", "")

    # Website
    website = lead.get("website", "")
    if website == "N/A":
        website = ""

    # Phone
    phone = lead.get("phone", "")
    if phone == "N/A":
        phone = ""

    # Email
    emails = lead.get("emails", [])
    if isinstance(emails, list):
        email_str = ", ".join(emails)
    else:
        email_str = str(emails) if emails and emails != "N/A" else ""

    # Score
    score = lead.get("lead_score", "")
    score_str = str(score) if score is not None else ""

    # Social Media Links
    socials = lead.get("social_media", {})
    fb_link = socials.get("facebook", "")
    ig_link = socials.get("instagram", "")
    tiktok_link = socials.get("tiktok", "")
    x_link = (
        socials.get("x_twitter", "")
        or socials.get("x", "")
        or socials.get("twitter", "")
    )
    linkedin_link = socials.get("linkedin", "")

    return [
        name,
        website,
        phone,
        email_str,
        score_str,
        fb_link,
        ig_link,
        tiktok_link,
        x_link,
        linkedin_link,
    ]


def prepare_table_data(leads: list[dict]) -> tuple[list[str], list[list[str]]]:
    """Convert list of lead dictionaries to headers and 2D row data."""
    rows = [format_lead_row(lead) for lead in leads]
    return HEADERS, rows


# ===========================================================================
# 2. CSV Export
# ===========================================================================

def _safe_filename(text: str, max_len: int = 40) -> str:
    clean = re.sub(r"[^\w\s-]", "", text.lower())
    clean = re.sub(r"[\s]+", "_", clean).strip("_")
    return clean[:max_len]


def write_csv(headers: list[str], rows: list[list[str]], query: str) -> Path:
    """Write table data to a clean CSV in .tmp/."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"google_sheets_leads_{_safe_filename(query)}_{ts}"
    csv_path = TMP_DIR / f"{base}.csv"

    # Use utf-8-sig (with BOM) for seamless opening in Excel/Google Sheets
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return csv_path


# ===========================================================================
# 3. Google Sheets API Integration (Optional / Auto-connecting)
# ===========================================================================

def _ensure_gspread():
    """Import (and auto-install) gspread and google-auth."""
    try:
        import gspread
        return gspread
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "gspread", "google-auth", "-q"]
        )
        import gspread
        return gspread


def extract_spreadsheet_id(sheet_target: str) -> str:
    """Extract Google Spreadsheet ID from either a full URL or raw ID."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_target)
    if match:
        return match.group(1)
    return sheet_target.strip()


def sync_to_live_google_sheet(
    headers: list[str],
    rows: list[list[str]],
    sheet_target: str,
    credentials_file: str | None = None,
) -> bool:
    """Push data to a live Google Sheet using gspread."""
    gspread = _ensure_gspread()
    sheet_id = extract_spreadsheet_id(sheet_target)

    cred_path = credentials_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    full_cred_path = PROJECT_ROOT / cred_path if not os.path.isabs(cred_path) else Path(cred_path)

    if not full_cred_path.exists():
        logger.warning("Google credentials file not found at %s", full_cred_path)
        return False

    try:
        gc = gspread.service_account(filename=str(full_cred_path))
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)

        # Clear existing content
        worksheet.clear()

        # Update with all rows (support various gspread API versions)
        all_data = [headers] + rows
        try:
            worksheet.update(values=all_data, range_name="A1")
        except TypeError:
            try:
                worksheet.update("A1", all_data)
            except Exception:
                worksheet.update(all_data)

        # Format header row: bold and freeze row 1
        try:
            worksheet.format("A1:J1", {"textFormat": {"bold": True}})
            worksheet.freeze(rows=1)
        except Exception as fmt_exc:
            logger.debug("Header formatting skipped: %s", fmt_exc)

        logger.info("Successfully updated Google Sheet: %s (Title: '%s')", sheet_id, sh.title)
        return True
    except Exception as exc:
        logger.error("Failed to sync to Google Sheet via API: %s", format_error(exc))
        return False


# ===========================================================================
# 4. CLI Entry Point
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export enriched GMB leads to Google Sheet format.",
    )
    parser.add_argument(
        "source_json",
        nargs="?",
        default=None,
        help="Path to enriched_leads JSON file (defaults to latest in .tmp/)",
    )
    parser.add_argument(
        "--sheet-url",
        default=None,
        help="Target Google Spreadsheet URL to sync live via API",
    )
    parser.add_argument(
        "--sheet-id",
        default=None,
        help="Target Google Spreadsheet ID to sync live via API",
    )
    parser.add_argument(
        "--credentials",
        default=None,
        help="Path to Google service account credentials JSON (defaults to credentials.json)",
    )
    args = parser.parse_args()

    load_env()

    # Determine input JSON
    if args.source_json:
        source_path = Path(args.source_json)
    else:
        source_path = find_latest_enriched_file()

    if not source_path or not source_path.exists():
        logger.error("No enriched leads JSON file found to export.")
        sys.exit(1)

    logger.info("Loading leads from %s …", source_path)
    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    leads = data.get("leads", [])
    query = data.get("query", "leads")
    if not leads:
        logger.warning("No leads found inside %s", source_path.name)
        sys.exit(0)

    # Convert to Google Sheets structure
    headers, rows = prepare_table_data(leads)

    # 1. Write CSV deliverable
    csv_path = write_csv(headers, rows, query)
    logger.info("CSV exported to %s", csv_path)

    # 2. Check for live Google Sheet target
    sheet_target = (
        args.sheet_url
        or args.sheet_id
        or os.getenv("GOOGLE_SHEETS_ID")
        or os.getenv("GOOGLE_SHEET_ID")
    )
    synced_live = False

    if sheet_target:
        logger.info("Attempting live Google Sheet sync to: %s", sheet_target)
        synced_live = sync_to_live_google_sheet(
            headers, rows, sheet_target, args.credentials
        )

    # Print summary
    print("\n" + "=" * 65)
    print("  GOOGLE SHEETS EXPORT COMPLETED")
    print("=" * 65)
    print(f"  Total Rows : {len(rows)} leads")
    print(f"  Columns    : {', '.join(headers)}")
    print(f"  CSV File   : {csv_path}")

    if synced_live:
        print("  Status     : ✅ Live Google Sheet updated successfully!")
    elif sheet_target:
        print("  Status     : ⚠️  Could not connect to Google Sheet API (check credentials.json).")
        print("               You can import the CSV directly into Google Sheets.")
    else:
        print("  Status     : 📄 CSV ready for 1-click Google Sheets import (File > Import > Upload).")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
