"""
scrape_gmb_leads.py — Scrape Google My Business listings via SerpAPI.

Directive: directives/scrape_gmb_leads.md

Usage:
    python execution/scrape_gmb_leads.py "dentists in Jakarta" --limit 20

Outputs:
    .tmp/gmb_leads_<query>_<timestamp>.txt   (human-readable report)
    .tmp/gmb_leads_<query>_<timestamp>.json  (machine-readable data)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap — ensure helpers are importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_env, get_logger, format_error, TMP_DIR  # noqa: E402

logger = get_logger("scrape_gmb_leads")

SERPAPI_ENDPOINT = "https://serpapi.com/search"


# ===========================================================================
# 1. API layer — talk to SerpAPI
# ===========================================================================

def _ensure_requests():
    """Import (and auto-install) the requests library."""
    try:
        import requests
        return requests
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "requests", "-q"]
        )
        import requests
        return requests


def search_google_maps(
    query: str,
    api_key: str,
    num_results: int = 20,
) -> list[dict]:
    """
    Search Google Maps via SerpAPI and return raw local_results.

    Paginates automatically until `num_results` are collected or
    no more pages are available.
    """
    requests = _ensure_requests()
    results: list[dict] = []
    start = 0
    page = 1

    while len(results) < num_results:
        logger.info("Fetching page %d (start=%d) …", page, start)

        params = {
            "engine": "google_maps",
            "q": query,
            "api_key": api_key,
            "start": start,
            "type": "search",
            "hl": "en",      # English labels
        }

        resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Check for API-level errors
        if "error" in data:
            raise RuntimeError(f"SerpAPI error: {data['error']}")

        local = data.get("local_results", [])
        if not local:
            logger.info("No more results on page %d — stopping.", page)
            break

        results.extend(local)
        logger.info(
            "  → got %d results (total so far: %d)", len(local), len(results)
        )

        # Is there a next page?
        next_url = (
            data.get("serpapi_pagination", {}).get("next")
            or data.get("pagination", {}).get("next")
        )
        if not next_url:
            break

        start += len(local)
        page += 1
        time.sleep(0.5)  # be polite

    return results[:num_results]


# ===========================================================================
# 2. Transform — raw result → clean lead
# ===========================================================================

def extract_lead(raw: dict) -> dict:
    """Extract a normalised lead dict from a raw SerpAPI result."""
    return {
        "business_name": raw.get("title", "N/A"),
        "category": _get_category(raw),
        "rating": raw.get("rating", "N/A"),
        "reviews_count": raw.get("reviews", "N/A"),
        "address": raw.get("address", "N/A"),
        "phone": raw.get("phone", "N/A"),
        "website": raw.get("website", "N/A"),
        "operating_hours": _normalise_hours(raw),
        "gps_coordinates": raw.get("gps_coordinates", {}),
        "place_id": raw.get("place_id", "N/A"),
    }


def _get_category(raw: dict) -> str:
    """Get the best category string from various SerpAPI fields."""
    # 'type' is a single string, 'types' is a list
    if raw.get("type"):
        return raw["type"]
    types = raw.get("types", [])
    if types:
        return ", ".join(types)
    return "N/A"


def _normalise_hours(raw: dict) -> str:
    """
    Normalise operating hours into a readable multi-line string.

    SerpAPI may return hours in several formats:
      - operating_hours: { "monday": "9 AM–5 PM", ... }
      - operating_hours: { "monday": ["9 AM–5 PM"], ... }
      - hours: "Open 24 hours" (simple string)
    """
    # Try the detailed structure first
    hours = raw.get("operating_hours")
    if isinstance(hours, dict):
        lines = []
        day_order = [
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        ]
        for day in day_order:
            val = hours.get(day)
            if val is None:
                continue
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            lines.append(f"{day.capitalize():<12} {val}")
        if lines:
            return "\n".join(lines)

    # Fall back to the simpler 'hours' field
    simple = raw.get("hours")
    if simple:
        return str(simple)

    # Check open_state as last resort
    open_state = raw.get("open_state")
    if open_state:
        return str(open_state)

    return "N/A"


# ===========================================================================
# 3. Output — write text report + JSON
# ===========================================================================

def format_text_report(leads: list[dict], query: str) -> str:
    """Build a human-readable structured text report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 72
    thin = "─" * 56

    lines = [
        sep,
        "  LEAD GENERATION REPORT  —  Google My Business",
        sep,
        f"  Query      : {query}",
        f"  Generated  : {now}",
        f"  Total Leads: {len(leads)}",
        sep,
        "",
    ]

    for i, lead in enumerate(leads, 1):
        lines.append(f"┌─ Lead #{i:>3} {thin}")
        lines.append(f"│ Business Name : {lead['business_name']}")
        lines.append(f"│ Category      : {lead['category']}")
        lines.append(f"│ Rating        : {lead['rating']}  ({lead['reviews_count']} reviews)")
        lines.append(f"│ Address       : {lead['address']}")
        lines.append(f"│ Phone         : {lead['phone']}")
        lines.append(f"│ Website       : {lead['website']}")
        lines.append(f"│ Hours         :")
        hours_str = lead["operating_hours"]
        if hours_str and hours_str != "N/A":
            for h_line in hours_str.split("\n"):
                lines.append(f"│                 {h_line}")
        else:
            lines.append(f"│                 N/A")
        coords = lead.get("gps_coordinates", {})
        if coords:
            lat = coords.get("latitude", "?")
            lng = coords.get("longitude", "?")
            lines.append(f"│ GPS           : {lat}, {lng}")
        lines.append(f"│ Place ID      : {lead['place_id']}")
        lines.append(f"└{'─' * 71}")
        lines.append("")

    lines.append(sep)
    lines.append(f"  END OF REPORT  —  {len(leads)} lead(s) extracted")
    lines.append(sep)
    return "\n".join(lines)


def _safe_filename(query: str, max_len: int = 40) -> str:
    """Sanitise a query string for use in a filename."""
    clean = re.sub(r"[^\w\s-]", "", query.lower())
    clean = re.sub(r"[\s]+", "_", clean).strip("_")
    return clean[:max_len]


def write_outputs(leads: list[dict], query: str) -> tuple[Path, Path]:
    """Write the text report and JSON to .tmp/ and return their paths."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"gmb_leads_{_safe_filename(query)}_{ts}"

    txt_path = TMP_DIR / f"{base}.txt"
    json_path = TMP_DIR / f"{base}.json"

    # Text report
    report = format_text_report(leads, query)
    txt_path.write_text(report, encoding="utf-8")

    # JSON
    payload = {
        "query": query,
        "generated_at": datetime.now().isoformat(),
        "total_leads": len(leads),
        "leads": leads,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return txt_path, json_path


# ===========================================================================
# 4. CLI entry point
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape GMB leads from Google Maps via SerpAPI.",
        epilog='Example: python execution/scrape_gmb_leads.py "dentists in Jakarta"',
    )
    parser.add_argument(
        "query",
        help='Search query, e.g. "coffee shops in Bandung"',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of leads to fetch (default: 20)",
    )
    args = parser.parse_args()

    # --- Bootstrap env ---
    load_env()
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        logger.error(
            "SERPAPI_KEY is not set. "
            "Add it to .env (free key → https://serpapi.com/manage-api-key)"
        )
        sys.exit(1)

    # --- Scrape ---
    logger.info('Starting GMB scrape: "%s"  (limit %d)', args.query, args.limit)

    try:
        raw_results = search_google_maps(args.query, api_key, args.limit)
    except Exception as exc:
        logger.error("Scrape failed: %s", format_error(exc))
        sys.exit(1)

    if not raw_results:
        logger.warning("Zero results for query: %s", args.query)
        sys.exit(0)

    # --- Transform ---
    leads = [extract_lead(r) for r in raw_results]
    logger.info("Extracted %d leads", len(leads))

    # --- Output ---
    txt_path, json_path = write_outputs(leads, args.query)
    logger.info("Text report → %s", txt_path)
    logger.info("JSON data   → %s", json_path)

    # Summary to stdout
    print(f"\n✅  {len(leads)} leads scraped successfully")
    print(f"    📄  {txt_path}")
    print(f"    📋  {json_path}")


if __name__ == "__main__":
    main()
