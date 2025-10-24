
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from ..db import get_db
from ..models import Project, ProjectMember, Task, User
from ..deps import current_user, role_required
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["projects"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
def list_projects(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    projects = db.query(Project).join(ProjectMember, isouter=True).filter(
        (Project.owner_id == user.id) | (ProjectMember.user_id == user.id)
    ).distinct().all()
    return templates.TemplateResponse("projects/list.html", {"request": request, "projects": projects, "user": user})

@router.get("/new", response_class=HTMLResponse, dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def new_project_form(request: Request):
    return templates.TemplateResponse("projects/new.html", {"request": request})

@router.post("", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def create_project(request: Request, name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = Project(name=name, description=description, owner_id=user.id)
    db.add(p); db.commit()
    db.add(ProjectMember(project_id=p.id, user_id=user.id)); db.commit()
    return RedirectResponse(url=f"/projects/{p.id}", status_code=303)

@router.get("/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/projects", status_code=303)
    members = db.query(ProjectMember).filter_by(project_id=project_id).all()
    tasks = db.query(Task).filter_by(project_id=project_id).all()
    users = db.query(User).all()
    return templates.TemplateResponse("projects/detail.html", {"request": request, "project": project, "members": members, "tasks": tasks, "users": users})

@router.post("/{project_id}/members", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def add_member(project_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    exists = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
    if not exists:
        db.add(ProjectMember(project_id=project_id, user_id=user_id)); db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/tasks")
def create_task(project_id: int, title: str = Form(...), description: str = Form(""), priority: str = Form("MEDIUM"), assignee_id: Optional[int] = Form(None), db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = Task(project_id=project_id, title=title, description=description, priority=priority, assignee_id=assignee_id)
    db.add(t); db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
