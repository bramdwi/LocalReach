# Directive: Enrich GMB Leads

## Goal
Take scraped GMB leads (JSON) and enrich each listing by: (1) extracting emails and social media links from business websites, (2) scoring lead quality 1–5, and (3) generating a personalized cold email introduction.

## Inputs
- **Source JSON** — path to a `gmb_leads_*.json` file produced by `execution/scrape_gmb_leads.py`
- **OPENAI_API_KEY** — (optional) for AI-generated cold emails. If absent, a template-based email is generated instead.

## Execution
1. `execution/enrich_gmb_leads.py <path-to-json> [--email-from "Your Name"] [--email-company "Your Company"] [--email-service "What you offer"]`
   - Reads the scraped JSON
   - For each lead with a website ≠ "N/A":
     - Fetches the homepage HTML (with timeout + User-Agent)
     - Extracts email addresses via regex + `mailto:` links
     - Extracts social media links (Instagram, Facebook, LinkedIn, TikTok, X/Twitter)
   - Scores each lead 1–5 (see rubric below)
   - Generates a personalized cold email per lead
   - Writes enriched output to `.tmp/`

### Scoring Rubric (1–5 points)
| Criterion | Points |
|---|---|
| Has phone number | +1 |
| Has website (not N/A) | +1 |
| Email found on website | +1 |
| ≥1 social media profile found | +1 |
| Rating ≥ 4.5 **and** ≥ 10 reviews | +1 |

### Cold Email Generation
- **With OPENAI_API_KEY**: Calls `gpt-4o-mini` to write a short, personalized intro referencing the business name, category, and any unique details from their website.
- **Without OPENAI_API_KEY**: Uses a professional template filled with lead-specific fields.

## Outputs
Both files land in `.tmp/`:

| File | Format | Purpose |
|---|---|---|
| `enriched_leads_<query>_<ts>.txt` | Structured text report | Human-readable — full enrichment details |
| `enriched_leads_<query>_<ts>.json` | JSON | Machine-readable — all enriched data |

### Fields added per lead (on top of original GMB data)
| Field | Description |
|---|---|
| `emails` | List of email addresses found on website |
| `social_media` | Dict of platform → URL |
| `lead_score` | Integer 1–5 |
| `lead_score_breakdown` | Dict explaining each point |
| `cold_email` | Personalized email text |
| `cold_email_method` | `"ai"` or `"template"` |

## Edge Cases & Learnings
- Websites may be down, redirect infinitely, or return non-HTML content — the script uses a 10-second timeout and catches all request exceptions gracefully.
- Some sites block scrapers — a realistic User-Agent header is set.
- Email regex may produce false positives (e.g. `support@example.png`) — the script filters common image/file extensions.
- **[2026-08-17] Wix-hosted sites embed Sentry error-tracking UUIDs as `@sentry.wixpress.com` emails in `<script>` tags.** Fixed by: (a) blocking known error-tracker domains, (b) filtering UUID-shaped local parts (>20 hex chars).
- **[2026-08-17] Social media URLs extracted from raw HTML (especially `<script>` JSON blobs) contained trailing encoded junk.** Fixed by: (a) stripping `<script>` tags before raw-HTML URL scan, (b) `_clean_social_url()` truncates at first invalid character (`"`, `&`, `;`, etc.), (c) validating that the URL path portion is at least 2 chars.
- **[2026-08-17] Some GMB websites have dead DNS** (e.g. `jhonfurniture28.com` returned `NameResolutionError`). The script logs a warning and continues — the lead scores lower due to missing email/social.
- OpenAI calls cost tokens. `gpt-4o-mini` is used to keep costs minimal (~$0.001 per lead). Confirm with user before running large batches.
- Rate limiting: 1-second delay between website fetches to be polite.

