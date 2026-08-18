# Directive: Scrape GMB Leads

## Goal
Scrape Google My Business (GMB) listings from Google Maps for a given search query and extract structured lead data (business name, category, rating, address, phone, website, operating hours).

## Inputs
- **Search query** — a string describing what to search for (e.g. `"dentists in Jakarta"`, `"coffee shops near Shibuya"`)
- **Limit** — maximum number of leads to return (default: 20)
- **SERPAPI_KEY** — API key from [serpapi.com](https://serpapi.com) stored in `.env`

## Execution
1. `execution/scrape_gmb_leads.py "<query>" --limit <N>`
   - Calls SerpAPI's `google_maps` engine
   - Paginates through `local_results` until the limit is reached
   - Extracts and normalises each listing into a flat lead structure
   - Writes two output files to `.tmp/`

### Why SerpAPI?
Direct scraping of Google Maps is fragile (dynamic JS, CAPTCHAs, IP bans).  
SerpAPI provides a stable JSON interface to Google Maps results.  
Free tier: 100 searches / month — sufficient for development and small batches.

## Outputs
Both files land in `.tmp/` and are named with the query + timestamp:

| File | Format | Purpose |
|---|---|---|
| `gmb_leads_<query>_<ts>.txt` | Structured text report | Human-readable — quick review |
| `gmb_leads_<query>_<ts>.json` | JSON array | Machine-readable — downstream processing |

### Fields extracted per lead
| Field | Source key | Fallback |
|---|---|---|
| `business_name` | `title` | `"N/A"` |
| `category` | `type` | `"N/A"` |
| `rating` | `rating` | `"N/A"` |
| `reviews_count` | `reviews` | `"N/A"` |
| `address` | `address` | `"N/A"` |
| `phone` | `phone` | `"N/A"` |
| `website` | `website` | `"N/A"` |
| `operating_hours` | `hours` / `operating_hours` | `"N/A"` |
| `gps_coordinates` | `gps_coordinates` | `{}` |
| `place_id` | `place_id` | `"N/A"` |

## Edge Cases & Learnings
- SerpAPI free tier is capped at **100 searches/month**. Confirm with user before running large batches.
- Some listings omit `phone`, `website`, or `hours` — the script falls back to `"N/A"`.
- Google Maps may return fewer results than requested if the query is too narrow.
- `operating_hours` format varies: can be a dict of day→times, a nested structure, or missing entirely. The script normalises all cases to a readable string.
- Query strings with special characters are sanitised before being used in filenames.
