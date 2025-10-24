
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Task, Comment, User
from ..deps import current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["tasks"])
templates = Jinja2Templates(directory="templates")

@router.get("/{task_id}", response_class=HTMLResponse)
def task_detail(task_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("tasks/detail.html", {"request": request, "task": task})

@router.post("/{task_id}/comment")
def add_comment(task_id: int, body: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = Comment(task_id=task_id, author_id=user.id, body=body)
    db.add(c); db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/{task_id}/status")
def update_status(task_id: int, status_value: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, task_id)
    if task:
        task.status = status_value
        db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)
