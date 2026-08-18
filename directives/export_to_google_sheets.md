# Directive: Export Leads to Google Sheets

## Goal
Export enriched GMB lead listings into a structured Google Sheet format with specified columns: Name, Website, Phone, Email, Score, Facebook Link, Instagram Link, TikTok Link, X Link, and LinkedIn Link.

## Inputs
- **Source JSON** — Path to `enriched_leads_*.json` in `.tmp/`
- **Spreadsheet Target (Optional)** — Google Spreadsheet ID or URL (via `--sheet-id` / `--sheet-url` or `GOOGLE_SHEET_ID` in `.env`)
- **Credentials (Optional for live API)** — Service account or OAuth client in `credentials.json` / `token.json`

## Target Column Schema
1. `Name` (Business Name)
2. `Website`
3. `Phone`
4. `Email`
5. `Score` (1–5)
6. `Facebook Link`
7. `Instagram Link`
8. `TikTok Link`
9. `X Link`
10. `LinkedIn Link`

## Execution
1. `python execution/export_to_google_sheets.py [.tmp/enriched_leads_*.json] [--sheet-url <URL> | --sheet-id <ID>]`
   - Parses the latest or specified enriched leads JSON file.
   - Extracts and formats each field according to the target schema.
   - Writes a Google Sheets ready CSV deliverable to `.tmp/google_sheets_leads_<query>_<ts>.csv`.
   - If Google credentials and sheet ID/URL are supplied, connects via Google Sheets API (gspread) and populates the spreadsheet cells directly.

## Outputs
- **Local Intermediate**: `.tmp/google_sheets_leads_<query>_<ts>.csv` (can be directly uploaded/imported to Google Sheets via File > Import).
- **Deliverable**: Live Google Sheet (when configured with API credentials/sheet URL).

## Edge Cases & Learnings
- If a business has multiple emails, they are comma-separated in the `Email` column.
- Missing values default to empty strings or `"N/A"` gracefully.
- Social media keys (`x_twitter`, `twitter`, `x`) are normalized to `X Link`.
- When using live Google Sheets API with service accounts, ensure the service account email has **Editor** access to the target Google Sheet.
