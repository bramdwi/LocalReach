# Directive: Web Dashboard & Local Runner

## Goal
Provide a local web interface for non-technical users to interactively search Google Maps for B2B leads, enrich them with web-crawled contact info and AI pitches, score lead quality, and export to CSV or Google Sheets.

## Inputs
- **Web App Host/Port** — default `http://127.0.0.1:8000`
- **Environment variables** — `SERPAPI_KEY`, `OPENAI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS` from `.env`

## Execution
1. Start the server:
   ```bash
   python run_web.py
   # or
   python execution/web_server.py
   ```
2. The browser automatically opens `http://127.0.0.1:8000`.

## Features
- **Leads Explorer & Analytics**: Real-time KPI summaries (Lead Score, Email Rate, Socials Rate), Table view & Grid card view, multi-filter by score/email/website.
- **Lead Detail Drawer**: Score breakdown, discovered emails, social profile links, and personalized cold email generator with one-click copy and `mailto:` launcher.
- **Pipeline Studio**: Interactive runner for `scrape_gmb_leads.py` + `enrich_gmb_leads.py` + `export_to_google_sheets.py` with live terminal streaming logs and progress bar.
- **Google Sheets Sync & CSV Export**: Export to CSV deliverable or push directly to Google Sheets API.
- **History & Stored Batches**: Instant switcher across past runs stored in `.tmp/`.
- **Settings Modal**: Update API keys in `.env` directly from the web interface.

## Outputs
- Standardized deliverables and intermediates saved in `.tmp/`
- Direct CSV and JSON browser downloads
