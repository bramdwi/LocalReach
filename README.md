# ⚡ LocalReach — GMB Lead Engine & Enrichment (DOE System)

> **Directive → Observation → Experiment**

LocalReach is an automated local B2B outbound engine: real-time Google Maps scraping, website & contact enrichment, AI cold pitch generation, and direct Google Sheets sync.

## Directory Structure

```
.
├── AGENTS.md           # Operating rules (immutable unless instructed)
├── directives/         # SOP-style Markdown instructions
│   ├── README.md       # How to write directives
│   └── _template.md    # Starter template for new directives
├── execution/          # Deterministic Python scripts
│   ├── README.md       # How to write execution scripts
│   └── helpers.py      # Shared utilities (env, logging, paths)
├── .tmp/               # Disposable intermediate files
├── .env                # Secret keys (gitignored)
├── .env.example        # Safe template for .env
└── .gitignore          # Keeps secrets & junk out of VCS
```

## Quick Start

### 🌐 Option A: Interactive Local Web UI (Recommended)
Run the local web dashboard:
```bash
python run_web.py
```
Open **`http://127.0.0.1:8000`** in your browser to scrape, enrich, inspect pitches, and export leads interactively.

### 💻 Option B: CLI Pipeline
1. Copy `.env.example` → `.env` and fill in your API keys.
2. Run scrape: `python execution/scrape_gmb_leads.py "dentists in Jakarta" --limit 20`
3. Run enrich: `python execution/enrich_gmb_leads.py .tmp/gmb_leads_*.json`
4. Run export: `python execution/export_to_google_sheets.py`

## Principles

| Principle | Meaning |
|---|---|
| **Check before creating** | Always look in `execution/` for existing tools first. |
| **Self-anneal on failure** | Fix the script, re-test, update the directive. |
| **Improve continuously** | Directives are living documents — learnings go back in. |
| **Deliverables live in the cloud** | Local files are intermediates only. |
