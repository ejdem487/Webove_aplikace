from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import User, Task, Role, UserRole, Project, ProjectMember
from .auth import router as auth_router
from .routers import admin as admin_router
from .routers import projects as projects_router
from .routers import tasks as tasks_router
from .routers import user as user_router
from passlib.hash import bcrypt

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="CHANGE_ME_secret_for_sessions", same_site="lax")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        def ensure_role(role_name: str) -> Role:
            role = db.query(Role).filter(Role.role_name == role_name).first()
            if not role:
                role = Role(role_name=role_name)
                db.add(role)
                db.commit()
            return role

        def ensure_user(email: str, username: str, pwd: str, role_name: str):
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, username=username, password_hash=bcrypt.hash(pwd))
                db.add(user)
                db.commit()
                db.refresh(user)
            role = ensure_role(role_name)
            existing = (
                db.query(UserRole)
                .filter(UserRole.user_id == user.user_id, UserRole.role_id == role.role_id)
                .first()
            )
            if not existing:
                db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
                db.commit()

        def ensure_owner_memberships():
            projects = db.query(Project).all()
            created = False
            for project in projects:
                exists = (
                    db.query(ProjectMember)
                    .filter(
                        ProjectMember.project_id == project.project_id,
                        ProjectMember.user_id == project.created_by,
                    )
                    .first()
                )
                if not exists:
                    db.add(ProjectMember(project_id=project.project_id, user_id=project.created_by))
                    created = True
            if created:
                db.commit()

        ensure_role("USER")
        ensure_role("MANAGER")
        ensure_role("ADMIN")
        ensure_user("admin@example.com", "admin", "admin123", "ADMIN")
        ensure_user("manager@example.com", "manager", "manager123", "MANAGER")
        ensure_user("user@example.com", "user", "user123", "USER")
        ensure_owner_memberships()

app.include_router(auth_router, prefix="/auth")
app.include_router(projects_router.router, prefix="/projects")
app.include_router(admin_router.router, prefix="/admin")
app.include_router(tasks_router.router, prefix="/tasks")
app.include_router(user_router.router, prefix="/user")

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=303)
    my_id = request.session["user_id"]
    tasks = (
        db.query(Task)
        .filter(Task.assigned_to_user_id == my_id)
        .order_by(Task.task_id.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks})

@app.exception_handler(401)
async def unauthorized(request, exc):
    return templates.TemplateResponse("errors/401.html", {"request": request}, status_code=401)

@app.exception_handler(403)
async def forbidden(request, exc):
    return templates.TemplateResponse("errors/403.html", {"request": request}, status_code=403)
