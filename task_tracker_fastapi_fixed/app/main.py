
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import User, Project, ProjectMember, Task
from .auth import router as auth_router
from .routers import projects as projects_router
from .routers import admin as admin_router
from .routers import tasks as tasks_router
from passlib.hash import bcrypt

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="CHANGE_ME_secret_for_sessions", same_site="lax")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        def ensure(email, pwd, role, full_name):
            u = db.query(User).filter(User.email==email).first()
            if not u:
                u = User(email=email, password_hash=bcrypt.hash(pwd), role=role, full_name=full_name)
                db.add(u); db.commit()
        ensure("admin@example.com","admin123","ADMIN","Admin")
        ensure("manager@example.com","manager123","MANAGER","Manager")
        ensure("user@example.com","user123","USER","User")

app.include_router(auth_router, prefix="/auth")
app.include_router(projects_router.router, prefix="/projects")
app.include_router(admin_router.router, prefix="/admin")
app.include_router(tasks_router.router, prefix="/tasks")

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=303)
    my_id = request.session["user_id"]
    projects = db.query(Project).join(ProjectMember).filter(ProjectMember.user_id == my_id).all()
    tasks = db.query(Task).filter((Task.assignee_id == my_id)).order_by(Task.updated_at.desc()).limit(10).all()
    return templates.TemplateResponse("index.html", {"request": request, "projects": projects, "tasks": tasks})

@app.exception_handler(401)
async def unauthorized(request, exc):
    return templates.TemplateResponse("errors/401.html", {"request": request}, status_code=401)

@app.exception_handler(403)
async def forbidden(request, exc):
    return templates.TemplateResponse("errors/403.html", {"request": request}, status_code=403)
