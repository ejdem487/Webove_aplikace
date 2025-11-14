from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from ..db import get_db
from ..models import Task, Comment, User, ProjectMember
from ..deps import current_user, ROLE_HIERARCHY, role_required, highest_role
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["tasks"])
templates = Jinja2Templates(directory="templates")

def _is_admin(user: User) -> bool:
    return highest_role(user) == "ADMIN"

def _can_manage_task(user: User, task: Task) -> bool:
    if _is_admin(user):
        return True
    return highest_role(user) == "MANAGER" and task.project and task.project.created_by == user.user_id

def _is_assignee(user: User, task: Task) -> bool:
    return task.assigned_to_user_id == user.user_id

@router.get("/{task_id}", response_class=HTMLResponse)
def task_detail(task_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/", status_code=303)
    member_users = (
        db.query(User)
        .join(ProjectMember, ProjectMember.user_id == User.user_id)
        .filter(ProjectMember.project_id == task.project_id)
        .order_by(User.username)
        .all()
    )
    member_ids = {member.user_id for member in member_users}
    if task.project and task.project.owner and task.project.owner.user_id not in member_ids:
        member_users.append(task.project.owner)
    can_manage = _can_manage_task(user, task)
    is_assignee = _is_assignee(user, task)
    return templates.TemplateResponse(
        "tasks/detail.html",
        {
            "request": request,
            "task": task,
            "user": user,
            "project_members": member_users,
            "can_manage": can_manage,
            "is_assignee": is_assignee,
        },
    )

@router.post("/{task_id}/comment")
def add_comment(task_id: int, request: Request, body: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/", status_code=303)
    if not (_can_manage_task(user, task) or _is_assignee(user, task)):
        return templates.TemplateResponse("errors/403_assignee.html", {"request": request}, status_code=403)
    comment = Comment(task_id=task_id, author_id=user.user_id, text=body)
    db.add(comment)
    db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/{task_id}/status")
def update_status(task_id: int, request: Request, status_value: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/", status_code=303)
    if not (_can_manage_task(user, task) or _is_assignee(user, task)):
        return templates.TemplateResponse("errors/403_assignee.html", {"request": request}, status_code=403)
    task.status = status_value
    db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/{task_id}/assign", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def update_assignee(task_id: int, assignee_id: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/projects", status_code=303)
    if not _can_manage_task(user, task):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemáš oprávnění spravovat tento úkol.")

    new_assignee: Optional[int] = int(assignee_id) if assignee_id else None
    if new_assignee:
        exists = db.get(User, new_assignee)
        if not exists:
            return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

    acting_role = highest_role(user)
    if new_assignee and acting_role != "ADMIN" and not task.project.has_member(new_assignee):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uživatel není členem projektu.")
    task.assigned_to_user_id = new_assignee
    db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/{task_id}/delete", dependencies=[Depends(role_required("ADMIN", "MANAGER"))])
def delete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/projects", status_code=303)
    if not _can_manage_task(user, task):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemáš oprávnění spravovat tento úkol.")
    project_id = task.project_id
    db.delete(task)
    db.commit()
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
