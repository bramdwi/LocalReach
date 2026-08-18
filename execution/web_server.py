"""
web_server.py — Mini SaaS Backend & API for GMB Outbound Lead Engine.

Features:
  - Multi-campaign & Lead Management
  - Credit System & Usage Tracking
  - AI Pitch Generation with Frameworks (AIDA, PAS, Direct Value)
  - Lead Status Pipeline (New, Contacted, Qualified, Closed)
  - Google Sheets & Multi-format Exports
  - Settings & BYOK (Bring Your Own Key) Support
"""

import asyncio
import csv
import io
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Bootstrap paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"

sys.path.insert(0, str(PROJECT_ROOT / "execution"))
from helpers import load_env, get_logger, TMP_DIR

load_env()
logger = get_logger("web_server")


app = FastAPI(title="LocalReach Lead Engine Mini SaaS", version="2.0.0")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

STATE_FILE = TMP_DIR / "saas_state.json"

# In-memory background task tracking
tasks_status: Dict[str, Dict[str, Any]] = {}


def get_saas_state() -> Dict[str, Any]:
    """Load or initialize SaaS state (credits, user, plan, campaigns)."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    default_state = {
        "user": {
            "name": "Brahman",
            "email": "brahman@growthagency.com",
            "plan": "Pro",
            "credits_total": 150,
            "credits_used": 20
        },
        "campaigns": {},
        "settings": {
            "default_tone": "aida",
            "sender_name": "Brahman",
            "company_name": "Bond Growth Agency",
            "value_prop": "high-ROI customer acquisition & brand scaling systems"
        }
    }
    save_saas_state(default_state)
    return default_state


def save_saas_state(state_data: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)


class ScrapeRequest(BaseModel):
    query: str
    limit: int = 10
    campaign_name: Optional[str] = None
    email_from: Optional[str] = "Brahman"
    email_company: Optional[str] = "Bond Growth Agency"
    email_service: Optional[str] = "custom client acquisition systems"
    pitch_framework: Optional[str] = "aida" # aida, pas, casual
    use_ai_email: bool = False


class LeadStatusUpdate(BaseModel):
    filename: str
    lead_index: int
    status: str # "new", "contacted", "qualified", "closed"


class UpgradePlanRequest(BaseModel):
    plan: str # "Starter", "Pro", "Agency"


class UpdateSettingsRequest(BaseModel):
    serpapi_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_sheet_id: Optional[str] = None
    sender_name: Optional[str] = None
    company_name: Optional[str] = None
    value_prop: Optional[str] = None


# ---------------------------------------------------------------------------
# Background Runner for Pipeline with SaaS Credit Consumption
# ---------------------------------------------------------------------------
async def run_pipeline_task(task_id: str, req: ScrapeRequest):
    tasks_status[task_id]["status"] = "running"
    tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Initializing Mini SaaS search for: '{req.query}' (target: {req.limit} leads)...")
    
    state_data = get_saas_state()
    available_credits = state_data["user"]["credits_total"] - state_data["user"]["credits_used"]

    if available_credits < req.limit:
        tasks_status[task_id]["status"] = "error"
        tasks_status[task_id]["error"] = f"Insufficient credits ({available_credits} left, requested {req.limit}). Please upgrade your plan or top up."
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ ERROR: Insufficient credits.")
        return

    env_copy = os.environ.copy()
    if not env_copy.get("SERPAPI_KEY"):
        tasks_status[task_id]["status"] = "error"
        tasks_status[task_id]["error"] = "SERPAPI_KEY missing in settings or .env."
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ ERROR: SERPAPI_KEY missing.")
        return

    try:
        # Step 1: Scrape Google Maps
        tasks_status[task_id]["stage"] = "scraping"
        tasks_status[task_id]["progress"] = 20
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Step 1: Querying Google Maps via SerpAPI...")

        scrape_cmd = [
            sys.executable,
            str(PROJECT_ROOT / "execution" / "scrape_gmb_leads.py"),
            req.query,
            "--limit", str(req.limit)
        ]

        proc = await asyncio.create_subprocess_exec(
            *scrape_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env_copy
        )

        scrape_output = []
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8', errors='replace').rstrip()
            if line_str:
                scrape_output.append(line_str)
                tasks_status[task_id]["logs"].append(f"[Scraper] {line_str}")

        await proc.wait()

        if proc.returncode != 0:
            tasks_status[task_id]["status"] = "error"
            tasks_status[task_id]["error"] = "Google Maps scraping encountered an issue."
            return

        # Locate scraped JSON
        scraped_json_file = None
        for line in reversed(scrape_output):
            m = re.search(r"Saved JSON:\s+(.+?\.json)", line)
            if m:
                scraped_json_file = m.group(1).strip()
                break

        if not scraped_json_file or not Path(scraped_json_file).exists():
            candidates = list(TMP_DIR.glob("gmb_leads_*.json"))
            candidates.sort(key=os.path.getmtime, reverse=True)
            scraped_json_file = str(candidates[0])

        tasks_status[task_id]["progress"] = 55
        tasks_status[task_id]["stage"] = "enriching"
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Step 2: Crawling company websites for emails, social intel & scoring...")

        # Step 2: Enrich
        enrich_cmd = [
            sys.executable,
            str(PROJECT_ROOT / "execution" / "enrich_gmb_leads.py"),
            scraped_json_file,
            "--email-from", req.email_from or "Brahman",
            "--email-company", req.email_company or "LocalReach Agency",
            "--email-service", req.email_service or "customer acquisition systems"
        ]

        proc_en = await asyncio.create_subprocess_exec(
            *enrich_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env_copy
        )

        enrich_output = []
        while True:
            line = await proc_en.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8', errors='replace').rstrip()
            if line_str:
                enrich_output.append(line_str)
                tasks_status[task_id]["logs"].append(f"[Enricher] {line_str}")

        await proc_en.wait()

        # Locate enriched JSON
        enriched_json_file = None
        for line in reversed(enrich_output):
            m = re.search(r"Saved JSON:\s+(.+?\.json)", line)
            if m:
                enriched_json_file = m.group(1).strip()
                break

        if not enriched_json_file or not Path(enriched_json_file).exists():
            candidates = list(TMP_DIR.glob("enriched_leads_*.json"))
            candidates.sort(key=os.path.getmtime, reverse=True)
            enriched_json_file = str(candidates[0])

        # Step 3: Export Deliverable
        tasks_status[task_id]["progress"] = 90
        tasks_status[task_id]["stage"] = "exporting"
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Step 3: Formatting SaaS CSV and campaign deliverable...")

        export_cmd = [
            sys.executable,
            str(PROJECT_ROOT / "execution" / "export_to_google_sheets.py"),
            enriched_json_file
        ]
        proc_exp = await asyncio.create_subprocess_exec(*export_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env_copy)
        await proc_exp.wait()

        # Read final data & attach default lead status tags
        with open(enriched_json_file, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        leads_list = result_data.get("leads", [])
        for lead in leads_list:
            if "status" not in lead:
                lead["status"] = "new"  # default status

        with open(enriched_json_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)

        # Deduct credits
        consumed = min(len(leads_list), req.limit)
        state_data["user"]["credits_used"] += consumed
        save_saas_state(state_data)

        tasks_status[task_id]["result_file"] = Path(enriched_json_file).name
        tasks_status[task_id]["result_data"] = result_data
        tasks_status[task_id]["progress"] = 100
        tasks_status[task_id]["stage"] = "completed"
        tasks_status[task_id]["status"] = "success"
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Success! {len(leads_list)} prospects verified. {consumed} credits used.")

    except Exception as e:
        tasks_status[task_id]["status"] = "error"
        tasks_status[task_id]["error"] = str(e)
        tasks_status[task_id]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Unhandled error: {str(e)}")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/user")
async def get_user_profile():
    """Returns current user account, plan, and credit balance."""
    state_data = get_saas_state()
    load_env()
    serpapi_key = os.getenv("SERPAPI_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    return {
        "user": state_data["user"],
        "settings": state_data.get("settings", {}),
        "integrations": {
            "serpapi": bool(serpapi_key),
            "openai": bool(openai_key),
            "sheets": (PROJECT_ROOT / "credentials.json").exists()
        }
    }


@app.post("/api/user/upgrade")
async def upgrade_plan(req: UpgradePlanRequest):
    """Simulates upgrade to Pro or Agency tier with bonus credits."""
    state_data = get_saas_state()
    state_data["user"]["plan"] = req.plan
    if req.plan == "Agency":
        state_data["user"]["credits_total"] = 1000
    elif req.plan == "Pro":
        state_data["user"]["credits_total"] = 350
    else:
        state_data["user"]["credits_total"] = 100

    save_saas_state(state_data)
    return {"status": "ok", "message": f"Successfully upgraded to {req.plan} Plan!", "user": state_data["user"]}


@app.post("/api/lead/status")
async def update_lead_status(req: LeadStatusUpdate):
    """Update pipeline status for a specific lead (new, contacted, qualified, closed)."""
    target = TMP_DIR / req.filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Batch file not found")

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    leads = data.get("leads", [])
    if 0 <= req.lead_index < len(leads):
        leads[req.lead_index]["status"] = req.status
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"status": "ok", "lead_status": req.status}
    else:
        raise HTTPException(status_code=400, detail="Invalid lead index")


@app.get("/api/history")
async def list_history():
    """List previous searches / campaign batches sorted by newest."""
    files = []
    for p in TMP_DIR.glob("enriched_leads_*.json"):
        stat = p.stat()
        leads_count = 0
        query = ""
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                leads_count = len(d.get("leads", []))
                query = d.get("query", "")
        except Exception:
            pass

        files.append({
            "filename": p.name,
            "type": "enriched",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "leads_count": leads_count,
            "query": query
        })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files}


@app.get("/api/leads/file")
async def get_lead_file(filename: str = Query(...)):
    target = TMP_DIR / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    if target.suffix == ".json":
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["filename"] = filename
        return data
    return FileResponse(str(target), media_type="text/plain", filename=filename)


@app.get("/api/leads/latest")
async def get_latest_leads():
    enriched_files = list(TMP_DIR.glob("enriched_leads_*.json"))
    if not enriched_files:
        return {"query": None, "leads": [], "total_leads": 0}

    enriched_files.sort(key=os.path.getmtime, reverse=True)
    with open(enriched_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        data["filename"] = enriched_files[0].name
        return data


@app.post("/api/pipeline/start")
async def start_pipeline(req: ScrapeRequest, bg: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    tasks_status[task_id] = {
        "id": task_id,
        "query": req.query,
        "stage": "starting",
        "status": "pending",
        "progress": 5,
        "logs": [f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_id} initialized."],
        "created_at": datetime.now().isoformat(),
        "error": None,
        "result_file": None,
        "result_data": None
    }
    bg.add_task(run_pipeline_task, task_id, req)
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/pipeline/status/{task_id}")
async def get_pipeline_status(task_id: str):
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_status[task_id]


@app.post("/api/export/csv")
async def export_csv(payload: Dict[str, Any]):
    leads = payload.get("leads", [])
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Status", "Website", "Phone", "Email", "Score",
        "Facebook", "Instagram", "TikTok", "LinkedIn", "Rating", "Reviews", "Address", "Outbound Cold Pitch"
    ])

    for lead in leads:
        emails = lead.get("emails", [])
        email_str = ", ".join(emails) if isinstance(emails, list) else str(emails or "")
        socials = lead.get("social_media", {})

        writer.writerow([
            lead.get("business_name", ""),
            lead.get("status", "new"),
            lead.get("website", ""),
            lead.get("phone", ""),
            email_str,
            lead.get("lead_score", ""),
            socials.get("facebook", ""),
            socials.get("instagram", ""),
            socials.get("tiktok", ""),
            socials.get("linkedin", ""),
            lead.get("rating", ""),
            lead.get("reviews_count", ""),
            lead.get("address", ""),
            lead.get("cold_email", "")
        ])

    output.seek(0)
    filename = f"localreach_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/settings")
async def update_settings(req: UpdateSettingsRequest):
    env_path = PROJECT_ROOT / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    def set_kv(key, val):
        nonlocal lines
        if val is None:
            return
        found = False
        new_lines = []
        for l in lines:
            if re.match(rf"^{key}\s*=", l):
                new_lines.append(f"{key}={val}\n")
                found = True
            else:
                new_lines.append(l)
        if not found:
            new_lines.append(f"{key}={val}\n")
        lines = new_lines

    if req.serpapi_key is not None:
        set_kv("SERPAPI_KEY", req.serpapi_key.strip())
        os.environ["SERPAPI_KEY"] = req.serpapi_key.strip()
    if req.openai_api_key is not None:
        set_kv("OPENAI_API_KEY", req.openai_api_key.strip())
        os.environ["OPENAI_API_KEY"] = req.openai_api_key.strip()
    if req.google_sheet_id is not None:
        set_kv("GOOGLE_SHEET_ID", req.google_sheet_id.strip())
        os.environ["GOOGLE_SHEET_ID"] = req.google_sheet_id.strip()

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Save persona settings into state
    state_data = get_saas_state()
    if req.sender_name:
        state_data["settings"]["sender_name"] = req.sender_name
    if req.company_name:
        state_data["settings"]["company_name"] = req.company_name
    if req.value_prop:
        state_data["settings"]["value_prop"] = req.value_prop
    save_saas_state(state_data)

    load_env()
    return {"status": "ok", "message": "Settings saved successfully"}


@app.get("/style.css")
async def serve_style():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
async def serve_app_js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = WEB_DIR / "index.html"
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


def start():
    import uvicorn
    uvicorn.run("web_server:app", host="127.0.0.1", port=8000, reload=True, app_dir=str(PROJECT_ROOT / "execution"))


if __name__ == "__main__":
    start()
