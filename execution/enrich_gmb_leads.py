"""
enrich_gmb_leads.py — Enrich scraped GMB leads with contact details,
                      scoring, and personalised cold emails.

Directive: directives/enrich_gmb_leads.md

Usage:
    python execution/enrich_gmb_leads.py .tmp/gmb_leads_*.json \
        --email-from "Jono" \
        --email-company "My Agency" \
        --email-service "custom interior design solutions"

Outputs:
    .tmp/enriched_leads_<query>_<timestamp>.txt
    .tmp/enriched_leads_<query>_<timestamp>.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_env, get_logger, format_error, TMP_DIR  # noqa: E402

logger = get_logger("enrich_gmb_leads")

# ---------------------------------------------------------------------------
# Dependency management
# ---------------------------------------------------------------------------

def _ensure_deps():
    """Install required packages if missing."""
    required = {"requests": "requests", "bs4": "beautifulsoup4"}
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing + ["-q"]
        )


_ensure_deps()

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
}
FETCH_TIMEOUT = 10  # seconds
POLITE_DELAY = 1.0  # seconds between requests

# Social media platform patterns
SOCIAL_PATTERNS = {
    "instagram": re.compile(
        r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+/?", re.I
    ),
    "facebook": re.compile(
        r"https?://(?:www\.)?(?:facebook\.com|fb\.com)/[A-Za-z0-9_./-]+/?", re.I
    ),
    "linkedin": re.compile(
        r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[A-Za-z0-9_./-]+/?", re.I
    ),
    "tiktok": re.compile(
        r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+/?", re.I
    ),
    "x_twitter": re.compile(
        r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+/?", re.I
    ),
}

# Email extraction
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I
)
# Filter out common false-positive extensions
FALSE_EMAIL_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
}
# Domains used by error-tracking / analytics — never real contacts
BLOCKED_EMAIL_DOMAINS = {
    "sentry.io", "sentry.wixpress.com", "sentry-next.wixpress.com",
    "bugsnag.com", "rollbar.com", "logrocket.com",
    "example.com", "test.com", "localhost",
}


# ===========================================================================
# 1. Website scraping — emails & social media
# ===========================================================================

def fetch_page(url: str) -> str | None:
    """Fetch a page's HTML. Returns None on any failure."""
    try:
        # Normalise URL
        if not url.startswith("http"):
            url = "http://" + url

        resp = requests.get(
            url, headers=HEADERS, timeout=FETCH_TIMEOUT, allow_redirects=True
        )
        resp.raise_for_status()

        # Only process HTML responses
        content_type = resp.headers.get("Content-Type", "")
        if "html" not in content_type.lower() and "text" not in content_type.lower():
            logger.warning("Non-HTML response from %s — skipping", url)
            return None

        return resp.text

    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, format_error(exc))
        return None


def extract_emails(html: str, base_url: str) -> list[str]:
    """Extract unique email addresses from HTML text."""
    emails = set()

    # 1. Regex over raw HTML
    for match in EMAIL_RE.findall(html):
        emails.add(match.lower())

    # 2. Parse mailto: links
    soup = BeautifulSoup(html, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("mailto:"):
            raw = href.replace("mailto:", "").split("?")[0].strip()
            if EMAIL_RE.match(raw):
                emails.add(raw.lower())

    # Filter false positives
    filtered = set()
    for email in emails:
        ext = "." + email.rsplit(".", 1)[-1]
        if ext in FALSE_EMAIL_EXTENSIONS:
            continue
        domain = email.split("@")[1]
        # Skip tracking/analytics domains
        if domain in BLOCKED_EMAIL_DOMAINS:
            continue
        # Skip obviously invalid domains
        if "." not in domain or len(domain) <= 3:
            continue
        # Skip hex-looking local parts (UUIDs from error trackers)
        local = email.split("@")[0]
        if len(local) > 20 and all(c in "0123456789abcdef" for c in local.replace(".", "").replace("-", "").replace("_", "")):
            continue
        filtered.add(email)

    return sorted(filtered)


def _clean_social_url(raw: str) -> str:
    """Truncate a URL at the first character that can't be in a clean social URL."""
    # Strip query strings and fragments first
    url = raw.split("?")[0].split("#")[0]
    # Truncate at characters that indicate embedded JSON/junk
    for ch in ('"', "'", "&", ";", ")", "]", "}", ",", " ", "\t", "\n"):
        idx = url.find(ch)
        if idx != -1:
            url = url[:idx]
    return url.rstrip("/")


def extract_social_media(html: str, base_url: str) -> dict[str, str]:
    """Extract social media profile links from HTML."""
    found: dict[str, str] = {}
    soup = BeautifulSoup(html, "html.parser")

    # Collect all hrefs from <a> and <link> tags (most reliable)
    hrefs: set[str] = set()
    for tag in soup.find_all(["a", "link"], href=True):
        href = tag["href"].strip()
        if href.startswith("/"):
            href = urljoin(base_url, href)
        hrefs.add(_clean_social_url(href))

    # Also scan raw HTML for URLs not in <a> tags (e.g. in data attributes)
    # But EXCLUDE <script> content to avoid JSON-embedded junk
    for script in soup.find_all("script"):
        script.decompose()
    clean_html = str(soup)
    url_pattern = re.compile(r'https?://[^\s"\'\'<>]+', re.I)
    for match in url_pattern.findall(clean_html):
        hrefs.add(_clean_social_url(match))

    # Match against platform patterns
    for platform, pattern in SOCIAL_PATTERNS.items():
        for href in hrefs:
            if pattern.match(href):
                clean = _clean_social_url(href)
                # Skip generic share/intent/widget URLs
                skip_keywords = ("/sharer", "/intent/", "/share", "/widgets", "/embed")
                if any(kw in clean.lower() for kw in skip_keywords):
                    continue
                # Minimum sanity: username portion should exist
                path = urlparse(clean).path.strip("/")
                if path and len(path) > 1:
                    found[platform] = clean
                    break  # one match per platform is enough

    return found


def scrape_website(url: str) -> dict:
    """Scrape a business website for emails and social media links."""
    result = {"emails": [], "social_media": {}, "scrape_status": "skipped"}

    if not url or url == "N/A":
        return result

    html = fetch_page(url)
    if html is None:
        result["scrape_status"] = "failed"
        return result

    result["emails"] = extract_emails(html, url)
    result["social_media"] = extract_social_media(html, url)
    result["scrape_status"] = "ok"

    return result


# ===========================================================================
# 2. Lead scoring
# ===========================================================================

def score_lead(lead: dict) -> tuple[int, dict]:
    """
    Score a lead from 1–5 based on contact completeness and reputation.

    Returns (score, breakdown_dict).
    """
    breakdown = {}
    score = 0

    # +1 Has phone
    has_phone = lead.get("phone", "N/A") not in ("N/A", "", None)
    if has_phone:
        score += 1
        breakdown["phone"] = "✓ Has phone number"
    else:
        breakdown["phone"] = "✗ No phone number"

    # +1 Has website
    has_website = lead.get("website", "N/A") not in ("N/A", "", None)
    if has_website:
        score += 1
        breakdown["website"] = "✓ Has website"
    else:
        breakdown["website"] = "✗ No website"

    # +1 Email found
    has_email = bool(lead.get("emails"))
    if has_email:
        score += 1
        breakdown["email"] = f"✓ Email found ({', '.join(lead['emails'])})"
    else:
        breakdown["email"] = "✗ No email found"

    # +1 Social media presence
    socials = lead.get("social_media", {})
    has_social = bool(socials)
    if has_social:
        platforms = ", ".join(socials.keys())
        score += 1
        breakdown["social_media"] = f"✓ Social media ({platforms})"
    else:
        breakdown["social_media"] = "✗ No social media found"

    # +1 Strong reputation
    rating = lead.get("rating", 0)
    reviews = lead.get("reviews_count", 0)
    if isinstance(rating, (int, float)) and isinstance(reviews, (int, float)):
        if rating >= 4.5 and reviews >= 10:
            score += 1
            breakdown["reputation"] = f"✓ Strong reputation ({rating}★, {reviews} reviews)"
        else:
            breakdown["reputation"] = f"✗ Below threshold ({rating}★, {reviews} reviews)"
    else:
        breakdown["reputation"] = "✗ Rating/reviews unavailable"

    return score, breakdown


# ===========================================================================
# 3. Cold email generation
# ===========================================================================

def generate_cold_email_ai(
    lead: dict,
    sender_name: str,
    sender_company: str,
    service_desc: str,
    api_key: str,
) -> str | None:
    """Generate a personalised cold email using OpenAI gpt-4o-mini in Indonesian."""
    try:
        sender_info = f"Pengirim: {sender_name}" + (f" dari {sender_company}" if sender_company else "")
        prompt = f"""Tulis email perkenalan/cold email bisnis yang singkat, sopan, dan profesional (2-3 paragraf, maksimal 120 kata) dalam Bahasa Indonesia.

{sender_info}
Layanan yang ditawarkan: {service_desc}

Detail bisnis target:
- Nama Bisnis: {lead['business_name']}
- Kategori: {lead['category']}
- Lokasi: {lead['address']}
- Rating: {lead.get('rating', 'N/A')} bintang ({lead.get('reviews_count', 'N/A')} ulasan)
- Website: {lead.get('website', 'N/A')}

Aturan:
- Gunakan Bahasa Indonesia yang sopan dan profesional (gunakan salam seperti 'Halo Tim [Nama Bisnis],' atau 'Yth. Manajemen [Nama Bisnis]').
- Berikan apresiasi spesifik mengenai bisnis/kualitas layanan mereka.
- Jelaskan secara singkat bagaimana kerja sama/layanan ini dapat membantu meningkatkan pertumbuhan atau operasional mereka.
- Akhiri dengan Call-to-Action ringan (contoh: diskusi singkat via telepon/WhatsApp/Google Meet 10-15 menit).
- Penutup: Salam hangat / Hormat saya, diikuti nama {sender_name}{f' dan {sender_company}' if sender_company else ''}.
- JANGAN gunakan tanda kurung placeholder seperti [Nama] — gunakan data asli yang disediakan."""

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Anda adalah copywriter business development profesional berbahasa Indonesia."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as exc:
        logger.warning("AI email generation failed: %s", format_error(exc))
        return None


def generate_cold_email_template(
    lead: dict,
    sender_name: str,
    sender_company: str,
    service_desc: str,
) -> str:
    """Generate a template-based cold email in Indonesian (no AI required)."""
    biz = lead["business_name"]
    category = lead.get("category", "bidang usaha Anda")
    rating_text = f"rating {lead.get('rating')}★" if lead.get("rating") else "reputasi yang sangat baik"
    
    intro_sender = f"Perkenalkan, nama saya {sender_name}." if not sender_company else f"Perkenalkan, nama saya {sender_name} dari {sender_company}."
    closing_company = f"\n{sender_company}" if sender_company else ""

    return f"""Subjek: Peluang Kerja Sama & Pertumbuhan Bisnis untuk {biz}

Halo Tim {biz},

Semoga pesan ini menemui Anda dalam keadaan baik. Saya melihat profil bisnis Anda saat mencari layanan {category.lower()} terbaik di wilayah Anda, dan saya sangat terkesan dengan {rating_text} serta kualitas pekerjaan yang Anda hadirkan.

{intro_sender} Kami berfokus pada {service_desc}, dan kami melihat potensi yang sangat baik untuk berkolaborasi dalam membantu {biz} menjangkau lebih banyak pelanggan potensial.

Apakah Anda ada waktu luang sekitar 10–15 menit minggu ini untuk diskusi singkat mengenai potensi kolaborasi ini?

Terima kasih atas waktu dan perhatiannya.

Salam hangat,
{sender_name}{closing_company}"""


# ===========================================================================
# 4. Output formatting
# ===========================================================================

def format_enriched_report(leads: list[dict], query: str) -> str:
    """Build a human-readable enriched lead report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 76
    thin = "─" * 60

    lines = [
        sep,
        "  ENRICHED LEAD REPORT  —  Google My Business",
        sep,
        f"  Original Query : {query}",
        f"  Enriched At    : {now}",
        f"  Total Leads    : {len(leads)}",
        "",
        "  Score Distribution:",
    ]

    # Score histogram
    scores = [l.get("lead_score", 0) for l in leads]
    for s in range(5, 0, -1):
        count = scores.count(s)
        bar = "█" * count
        lines.append(f"    {s}★  {bar} ({count})")

    avg = sum(scores) / len(scores) if scores else 0
    lines.append(f"    Avg: {avg:.1f}★")
    lines.append(sep)
    lines.append("")

    for i, lead in enumerate(leads, 1):
        score = lead.get("lead_score", 0)
        stars = "★" * score + "☆" * (5 - score)

        lines.append(f"┌─ Lead #{i:>3}  [{stars}]  Score: {score}/5 {thin[:30]}")
        lines.append(f"│")
        lines.append(f"│ ▸ BUSINESS INFO")
        lines.append(f"│   Name     : {lead['business_name']}")
        lines.append(f"│   Category : {lead['category']}")
        lines.append(f"│   Rating   : {lead.get('rating', 'N/A')}  ({lead.get('reviews_count', 'N/A')} reviews)")
        lines.append(f"│   Address  : {lead['address']}")
        lines.append(f"│")
        lines.append(f"│ ▸ CONTACT DETAILS")
        lines.append(f"│   Phone    : {lead.get('phone', 'N/A')}")
        lines.append(f"│   Website  : {lead.get('website', 'N/A')}")

        emails = lead.get("emails", [])
        lines.append(f"│   Email(s) : {', '.join(emails) if emails else 'None found'}")

        lines.append(f"│")
        lines.append(f"│ ▸ SOCIAL MEDIA")
        socials = lead.get("social_media", {})
        if socials:
            for platform, url in socials.items():
                label = platform.replace("_", "/").title()
                lines.append(f"│   {label:<12}: {url}")
        else:
            lines.append(f"│   No social media profiles found")

        lines.append(f"│")
        lines.append(f"│ ▸ SCORE BREAKDOWN")
        breakdown = lead.get("lead_score_breakdown", {})
        for key, detail in breakdown.items():
            lines.append(f"│   {detail}")

        lines.append(f"│")
        lines.append(f"│ ▸ COLD EMAIL ({lead.get('cold_email_method', 'template').upper()})")
        lines.append(f"│   ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")
        email_text = lead.get("cold_email", "")
        for email_line in email_text.split("\n"):
            lines.append(f"│   {email_line}")
        lines.append(f"│   ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")
        lines.append(f"└{'─' * 75}")
        lines.append("")

    lines.append(sep)
    lines.append(f"  END OF ENRICHED REPORT  —  {len(leads)} lead(s)")
    lines.append(sep)

    return "\n".join(lines)


def _safe_filename(text: str, max_len: int = 40) -> str:
    clean = re.sub(r"[^\w\s-]", "", text.lower())
    clean = re.sub(r"[\s]+", "_", clean).strip("_")
    return clean[:max_len]


# ===========================================================================
# 5. Main pipeline
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich GMB leads with emails, socials, scoring & cold emails.",
        epilog='Example: python execution/enrich_gmb_leads.py .tmp/gmb_leads_*.json',
    )
    parser.add_argument(
        "source_json",
        help="Path to the gmb_leads JSON file to enrich",
    )
    parser.add_argument(
        "--email-from",
        default="Brahman DB",
        help="Nama pengirim untuk cold email (default: Brahman DB)",
    )
    parser.add_argument(
        "--email-company",
        default="",
        help="Nama perusahaan pengirim (default: kosong)",
    )
    parser.add_argument(
        "--email-service",
        default="layanan pemasaran digital dan peningkatan penjualan",
        help="Deskripsi singkat layanan yang ditawarkan",
    )
    args = parser.parse_args()

    # --- Load env & input ---
    load_env()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    has_ai = bool(openai_key)

    if has_ai:
        logger.info("OpenAI key detected — will use AI for cold emails")
    else:
        logger.info("No OpenAI key — using template-based cold emails")

    source_path = Path(args.source_json)
    if not source_path.exists():
        logger.error("Source file not found: %s", source_path)
        sys.exit(1)

    with open(source_path, "r", encoding="utf-8") as f:
        source_data = json.load(f)

    leads = source_data.get("leads", [])
    query = source_data.get("query", "unknown")
    logger.info("Loaded %d leads from %s", len(leads), source_path.name)

    # --- Enrich each lead ---
    enriched_leads: list[dict] = []

    for i, lead in enumerate(leads, 1):
        biz_name = lead.get("business_name", "Unknown")
        website = lead.get("website", "N/A")
        logger.info("[%d/%d] Enriching: %s", i, len(leads), biz_name)

        # Step 1: Scrape website for emails & social media
        web_data = scrape_website(website)
        lead["emails"] = web_data["emails"]
        lead["social_media"] = web_data["social_media"]
        lead["scrape_status"] = web_data["scrape_status"]

        if web_data["emails"]:
            logger.info("  📧 Emails: %s", ", ".join(web_data["emails"]))
        if web_data["social_media"]:
            logger.info(
                "  📱 Socials: %s",
                ", ".join(f"{k}={v}" for k, v in web_data["social_media"].items()),
            )

        # Step 2: Score the lead
        score, breakdown = score_lead(lead)
        lead["lead_score"] = score
        lead["lead_score_breakdown"] = breakdown
        logger.info("  ⭐ Score: %d/5", score)

        # Step 3: Generate cold email
        if has_ai:
            ai_email = generate_cold_email_ai(
                lead,
                args.email_from,
                args.email_company,
                args.email_service,
                openai_key,
            )
            if ai_email:
                lead["cold_email"] = ai_email
                lead["cold_email_method"] = "ai"
            else:
                # Fallback to template if AI fails
                lead["cold_email"] = generate_cold_email_template(
                    lead, args.email_from, args.email_company, args.email_service
                )
                lead["cold_email_method"] = "template (ai fallback)"
        else:
            lead["cold_email"] = generate_cold_email_template(
                lead, args.email_from, args.email_company, args.email_service
            )
            lead["cold_email_method"] = "template"

        enriched_leads.append(lead)

        # Polite delay between website fetches
        if i < len(leads):
            time.sleep(POLITE_DELAY)

    # --- Write outputs ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"enriched_leads_{_safe_filename(query)}_{ts}"
    txt_path = TMP_DIR / f"{base}.txt"
    json_path = TMP_DIR / f"{base}.json"

    # Text report
    report = format_enriched_report(enriched_leads, query)
    txt_path.write_text(report, encoding="utf-8")
    logger.info("Text report → %s", txt_path)

    # JSON
    payload = {
        "query": query,
        "original_source": str(source_path),
        "enriched_at": datetime.now().isoformat(),
        "total_leads": len(enriched_leads),
        "ai_emails_used": has_ai,
        "leads": enriched_leads,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("JSON data   → %s", json_path)

    # --- Summary ---
    scores = [l["lead_score"] for l in enriched_leads]
    hot = sum(1 for s in scores if s >= 4)
    warm = sum(1 for s in scores if 2 <= s < 4)
    cold = sum(1 for s in scores if s < 2)

    print(f"\n✅  {len(enriched_leads)} leads enriched successfully")
    print(f"    🔥 Hot (4-5★): {hot}  |  🌤️ Warm (2-3★): {warm}  |  ❄️ Cold (1★): {cold}")
    print(f"    📄  {txt_path}")
    print(f"    📋  {json_path}")


if __name__ == "__main__":
    main()
