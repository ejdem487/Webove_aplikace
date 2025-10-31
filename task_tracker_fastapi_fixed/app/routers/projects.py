
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from ..db import get_db
from ..models import Project, ProjectMember, Task, User
from ..deps import current_user, role_required
from fastapi.templating import Jinja2Templates
from datetime import date
from fastapi import UploadFile, File
from sqlalchemy import func
import os

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

    # filtrování z query parametrů
    q_status = request.query_params.get("status")
    q_priority = request.query_params.get("priority")
    q_assignee = request.query_params.get("assignee_id")
    q_due_before = request.query_params.get("due_before")

    members = db.query(ProjectMember).filter_by(project_id=project_id).all()
    tasks_q = db.query(Task).filter(Task.project_id == project_id)

    if q_status:
        tasks_q = tasks_q.filter(Task.status == q_status)
    if q_priority:
        tasks_q = tasks_q.filter(Task.priority == q_priority)
    if q_assignee:
        tasks_q = tasks_q.filter(Task.assignee_id == int(q_assignee))
    if q_due_before:
        try:
            d = date.fromisoformat(q_due_before)
            tasks_q = tasks_q.filter(Task.deadline != None, Task.deadline <= d)
        except:
            pass

    tasks = tasks_q.all()
    users = db.query(User).all()

    # jednoduchý report (počet dle stavu/priorit)
    status_counts = db.query(Task.status, func.count(Task.id)).filter(Task.project_id == project_id).group_by(Task.status).all()
    priority_counts = db.query(Task.priority, func.count(Task.id)).filter(Task.project_id == project_id).group_by(Task.priority).all()

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
            "project": project,
            "members": members,
            "tasks": tasks,
            "users": users,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
        },
    )


@router.post("/{project_id}/members", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def add_member(project_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    exists = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
    if not exists:
        db.add(ProjectMember(project_id=project_id, user_id=user_id)); db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/tasks")
def create_task(
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("MEDIUM"),
    assignee_id: Optional[int] = Form(None),
    deadline: Optional[str] = Form(None),
    estimate_hours: Optional[int] = Form(None),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    # deadline parse
    d = date.fromisoformat(deadline) if deadline else None

    # uložení přílohy do static/uploads
    attachment_path = ""
    if attachment and attachment.filename:
        os.makedirs("static/uploads", exist_ok=True)
        save_path = os.path.join("static", "uploads", attachment.filename)
        # pozor na kolize názvu; pro zjednodušení přepíšeme
        with open(save_path, "wb") as f:
            f.write(attachment.file.read())
        attachment_path = "/" + save_path.replace("\\", "/")

    t = Task(
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
        assignee_id=assignee_id,
        deadline=d,
        estimate_hours=estimate_hours,
        attachment_path=attachment_path,
    )
    db.add(t)
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)



@router.post("/{project_id}/archive", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def archive_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if p:
        p.archived = True
        db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/unarchive", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def unarchive_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if p:
        p.archived = False
        db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
