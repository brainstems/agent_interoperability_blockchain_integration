from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="admin_app/templates")

# --- In-memory task store ---
tasks_db = [
    {
        "id": str(uuid.uuid4()),
        "name": "Example Task 1",
        "description": "Demo task for infrastructure agent",
        "priority": "High",
        "status": "Pending",
        "assigned_to": "AgentA",
        "deadline": "2025-06-01"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Example Task 2",
        "description": "Federated learning round",
        "priority": "Medium",
        "status": "Assigned",
        "assigned_to": "AgentB",
        "deadline": "2025-06-03"
    }
]

# --- Models ---
class TaskCreate(BaseModel):
    name: str
    description: Optional[str]
    priority: str
    deadline: Optional[str]

class TaskUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    priority: Optional[str]
    deadline: Optional[str]
    assigned_to: Optional[str]
    status: Optional[str]

class Task(BaseModel):
    id: str
    name: str
    description: Optional[str]
    priority: str
    deadline: Optional[str]
    assigned_to: Optional[str]
    status: str

# --- HTML Endpoints ---
@router.get("/", response_class=HTMLResponse)
def tasks_admin(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks_db})

@router.get("/new", response_class=HTMLResponse)
def new_task_form(request: Request):
    return templates.TemplateResponse("task_new.html", {"request": request})

@router.post("/new", response_class=HTMLResponse)
def submit_new_task(request: Request, name: str = Form(...), description: str = Form(""), priority: str = Form("Medium"), deadline: str = Form("")):
    task = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "priority": priority,
        "deadline": deadline,
        "assigned_to": None,
        "status": "Pending"
    }
    tasks_db.append(task)
    return RedirectResponse(url="/admin/tasks/", status_code=303)

# --- API Endpoints (JSON, for completeness) ---
@router.get("/api", response_model=List[Task])
def list_tasks_api():
    return [Task(**t) for t in tasks_db]

@router.post("/api", response_model=Task)
def submit_task_api(task: TaskCreate):
    t = task.dict()
    t["id"] = str(uuid.uuid4())
    t["assigned_to"] = None
    t["status"] = "Pending"
    tasks_db.append(t)
    return Task(**t)
