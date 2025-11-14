from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import or_
from ..db import get_db
from ..models import Project, Task, User, ProjectMember
from ..deps import current_user, role_required, highest_role
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["projects"])
templates = Jinja2Templates(directory="templates")

def _is_admin(user: User) -> bool:
    return highest_role(user) == "ADMIN"

def _can_manage_project(user: User, project: Project) -> bool:
    if not project:
        return False
    return _is_admin(user) or (highest_role(user) == "MANAGER" and project.created_by == user.user_id)

@router.get("", response_class=HTMLResponse)
def list_projects(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    role = highest_role(user)
    membership_filter = or_(
        Project.created_by == user.user_id,
        Project.tasks.any(Task.assigned_to_user_id == user.user_id),
        Project.memberships.any(ProjectMember.user_id == user.user_id),
    )
    if role == "ADMIN":
        projects = db.query(Project).all()
    else:
        projects = (
            db.query(Project)
            .filter(membership_filter)
            .distinct()
            .all()
        )
    return templates.TemplateResponse("projects/list.html", {"request": request, "projects": projects, "user": user})

@router.get("/new", response_class=HTMLResponse, dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def new_project_form(request: Request):
    return templates.TemplateResponse("projects/new.html", {"request": request})

@router.post("", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def create_project(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = Project(name=name, description=description, created_by=user.user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    db.add(ProjectMember(project_id=project.project_id, user_id=user.user_id))
    db.commit()
    return RedirectResponse(url=f"/projects/{project.project_id}", status_code=303)

@router.get("/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/projects", status_code=303)

    status_filter = request.query_params.get("status")
    assignee_filter = request.query_params.get("assignee_id")

    tasks_query = db.query(Task).filter(Task.project_id == project_id)
    if status_filter:
        tasks_query = tasks_query.filter(Task.status == status_filter)
    if assignee_filter:
        try:
            assignee_value = int(assignee_filter)
            tasks_query = tasks_query.filter(Task.assigned_to_user_id == assignee_value)
        except ValueError:
            pass

    tasks = tasks_query.all()
    member_users = (
        db.query(User)
        .join(ProjectMember, ProjectMember.user_id == User.user_id)
        .filter(ProjectMember.project_id == project_id)
        .order_by(User.username)
        .all()
    )
    member_ids = {member.user_id for member in member_users}
    if project.owner and project.owner.user_id not in member_ids:
        member_users.append(project.owner)
        member_ids.add(project.owner.user_id)

    available_users_query = db.query(User)
    if member_ids:
        available_users_query = available_users_query.filter(~User.user_id.in_(member_ids))
    available_users = available_users_query.order_by(User.username).all()
    can_manage = _can_manage_project(user, project)

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
            "project": project,
            "tasks": tasks,
            "project_members": member_users,
            "available_users": available_users,
            "user": user,
            "can_manage": can_manage,
        },
    )

@router.post("/{project_id}/tasks", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def create_task(
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("TODO"),
    assignee_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/projects", status_code=303)
    if not _can_manage_project(user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemáš oprávnění spravovat tento projekt.")
    acting_role = highest_role(user)
    if assignee_id and acting_role != "ADMIN" and not project.has_member(assignee_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uživatel není členem projektu.")
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        status=status,
        assigned_to_user_id=assignee_id,
        created_by=user.user_id,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/members", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def add_member(project_id: int, user_id: int = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/projects", status_code=303)
    if not _can_manage_project(user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemáš oprávnění spravovat tento projekt.")
    if project.has_member(user_id):
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
    db.add(ProjectMember(project_id=project_id, user_id=user_id))
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/members/{member_id}/remove", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def remove_member(project_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        return RedirectResponse(url="/projects", status_code=303)
    if not _can_manage_project(user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemáš oprávnění spravovat tento projekt.")
    if member_id == project.created_by:
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == member_id)
        .first()
    )
    if membership:
        db.delete(membership)
        db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/{project_id}/delete", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if project:
        if not _can_manage_project(user, project):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemáš oprávnění smazat tento projekt.")
        db.delete(project)
        db.commit()
    return RedirectResponse(url="/projects", status_code=303)
