import os
import asyncio
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from agents.infrastructure_crew.infrastructure_agents.registry_manager_agent import RegistryManagerAgent
from agents.infrastructure_crew.schemas.learning_schemas import SharableLearning

router = APIRouter()
templates = Jinja2Templates(directory="admin_app/templates")

# --- Helper: get RegistryManagerAgent instance ---
def get_registry_agent():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    config = {"redis_url": redis_url}
    return RegistryManagerAgent(config=config)

# --- Async endpoints ---
@router.get("/", response_class=HTMLResponse)
async def learnings_dashboard(request: Request):
    registry_agent = get_registry_agent()
    # Query all learnings (by type=None returns all)
    learnings = await registry_agent.query_learnings()
    # Convert to dicts for template
    learnings_dicts = []
    for l in learnings:
        # Add used_by_agents if present in content
        used_by_agents = l.content.get("used_by_agents") if isinstance(l.content, dict) else None
        learnings_dicts.append({
            "id": l.learning_id,
            "type": l.learning_type,
            "source": l.source_entity_id,
            "content": l.content,
            "task_description": l.task_description,
            "keywords": l.keywords,
            "used_by_agents": used_by_agents or [],
        })
    return templates.TemplateResponse("learnings.html", {"request": request, "learnings": learnings_dicts})

@router.get("/{learning_id}/delete", response_class=HTMLResponse)
async def delete_learning(request: Request, learning_id: str):
    registry_agent = get_registry_agent()
    await registry_agent.delete_learning(learning_id)
    return RedirectResponse(url="/admin/learnings/", status_code=303)
