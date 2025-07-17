from fastapi import APIRouter, Request, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="admin_app/templates")

# --- In-memory/mock config and policies ---
federated_config = {
    "learning_rate": 0.01,
    "num_rounds": 10,
    "participating_agents": ["AgentA", "AgentB", "AgentC"]
}

policies = [
    {"id": str(uuid.uuid4()), "name": "Policy_v1.json", "download_url": "/static/policies/Policy_v1.json"},
    {"id": str(uuid.uuid4()), "name": "Policy_v2.json", "download_url": "/static/policies/Policy_v2.json"}
]

# --- HTML Endpoints ---
@router.get("/", response_class=HTMLResponse)
def federated_dashboard(request: Request):
    return templates.TemplateResponse("federated.html", {"request": request, "config": federated_config, "policies": policies})

@router.post("/config", response_class=HTMLResponse)
def update_federated_config(request: Request, learning_rate: float = Form(...), num_rounds: int = Form(...), participating_agents: str = Form(...)):
    federated_config["learning_rate"] = learning_rate
    federated_config["num_rounds"] = num_rounds
    federated_config["participating_agents"] = [a.strip() for a in participating_agents.split(",") if a.strip()]
    return RedirectResponse(url="/admin/federated/", status_code=303)

@router.post("/run", response_class=HTMLResponse)
def trigger_training(request: Request):
    # In real implementation, trigger backend federated learning round
    return RedirectResponse(url="/admin/federated/", status_code=303)

@router.post("/policies/upload", response_class=HTMLResponse)
def upload_policy(request: Request, policy_file: UploadFile):
    # In real implementation, save file and register new policy
    policies.append({"id": str(uuid.uuid4()), "name": policy_file.filename, "download_url": f"/static/policies/{policy_file.filename}"})
    return RedirectResponse(url="/admin/federated/", status_code=303)
