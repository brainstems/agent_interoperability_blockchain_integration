from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from admin_app.routers import tasks, federated, crews, performance, learnings

app = FastAPI(title="Agent Infrastructure Admin UI")

# Jinja2 template setup
templates = Jinja2Templates(directory="admin_app/templates")

# Static file serving (for custom CSS/JS if needed)
app.mount("/static", StaticFiles(directory="admin_app/static"), name="static")

# Dashboard home page
@app.get("/admin/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Include routers for each admin area
app.include_router(tasks.router, prefix="/admin/tasks", tags=["Tasks"])
app.include_router(federated.router, prefix="/admin/federated", tags=["Federated Learning"])
app.include_router(crews.router, prefix="/admin/crews", tags=["Crew Config"])
app.include_router(performance.router, prefix="/admin/performance", tags=["Performance"])
app.include_router(learnings.router, prefix="/admin/learnings", tags=["Learnings"])
