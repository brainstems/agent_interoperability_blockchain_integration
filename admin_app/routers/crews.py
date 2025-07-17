from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json

router = APIRouter()
templates = Jinja2Templates(directory="admin_app/templates")

# --- Mock JSON config for crews ---
crew_configs = {
    "translation": '{"language_pairs": ["en-fr", "en-es"], "default_strategy": "rule-based"}',
    "qa": '{"coverage": "full", "tools": ["db", "api"], "max_depth": 3}',
    "red_team": '{"attack_vectors": ["phishing", "malware"], "aggressiveness": "medium"}'
}

@router.get("/", response_class=HTMLResponse)
def crews_dashboard(request: Request):
    return templates.TemplateResponse("crews.html", {
        "request": request,
        "translation_config": crew_configs["translation"],
        "qa_config": crew_configs["qa"],
        "red_team_config": crew_configs["red_team"]
    })

@router.post("/translation/config", response_class=HTMLResponse)
def update_translation_config(request: Request, config_json: str = Form(...)):
    crew_configs["translation"] = config_json
    return RedirectResponse(url="/admin/crews/", status_code=303)

@router.post("/qa/config", response_class=HTMLResponse)
def update_qa_config(request: Request, config_json: str = Form(...)):
    crew_configs["qa"] = config_json
    return RedirectResponse(url="/admin/crews/", status_code=303)

@router.post("/red_team/config", response_class=HTMLResponse)
def update_red_team_config(request: Request, config_json: str = Form(...)):
    crew_configs["red_team"] = config_json
    return RedirectResponse(url="/admin/crews/", status_code=303)
