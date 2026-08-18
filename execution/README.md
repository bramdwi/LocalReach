# execution/

This folder contains **deterministic Python scripts** — the execution layer of the DOE system.

## What goes here

Scripts that handle:
- API calls
- Data processing
- File operations
- Cloud storage interactions

## Rules

1. **If it runs more than once, it belongs in code** — not in the AI's head.
2. Scripts must be **fast, testable, and repeatable**.
3. Secrets and tokens live in `.env` (loaded via `python-dotenv`).
4. All intermediate files go to `.tmp/` — they are disposable.
5. Check `execution/` for existing tools **before** writing anything new.

## Conventions

- One script per distinct operation (e.g., `scrape_single_site.py`, `upload_to_sheets.py`).
- Use `helpers.py` for shared utilities (logging, env loading, error formatting).
- Scripts should be runnable standalone: `python execution/script_name.py`.
