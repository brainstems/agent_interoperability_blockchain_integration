from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()
templates = Jinja2Templates(directory="admin_app/templates")

# --- Mock Data ---
agents = [
    {
        "agent_id": "AgentA",
        "health": "Healthy",
        "uptime": 123.4,
        "error_rate": 0.5,
        "completed_tasks": 42,
        "failed_tasks": 2,
        "pending_tasks": 3,
        "reputation": 4.8
    },
    {
        "agent_id": "AgentB",
        "health": "Warning",
        "uptime": 98.7,
        "error_rate": 2.1,
        "completed_tasks": 30,
        "failed_tasks": 5,
        "pending_tasks": 1,
        "reputation": 4.2
    },
    {
        "agent_id": "AgentC",
        "health": "Healthy",
        "uptime": 200.0,
        "error_rate": 0.0,
        "completed_tasks": 60,
        "failed_tasks": 0,
        "pending_tasks": 0,
        "reputation": 5.0
    }
]

marketplace = {
    "num_bids": 17,
    "avg_bid": 3.2,
    "avg_completion_time": 12.4,
    "bottlenecks": ["AgentB high error rate"]
}

# --- HTML Endpoint ---
@router.get("/", response_class=HTMLResponse)
def performance_dashboard(request: Request):
    return templates.TemplateResponse("performance.html", {"request": request, "agents": agents, "marketplace": marketplace})
