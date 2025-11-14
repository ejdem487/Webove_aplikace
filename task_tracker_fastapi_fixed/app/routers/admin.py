from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from ..db import get_db
from ..models import User, Project, Task, Comment, Role, UserRole
from ..deps import role_required, current_user, highest_role
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="templates")

def _ensure_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.role_name == role_name).first()
    if not role:
        role = Role(role_name=role_name)
        db.add(role)
        db.commit()
    return role

@router.get("/users", response_class=HTMLResponse, dependencies=[Depends(role_required("ADMIN"))])
def list_users(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    roles = db.query(Role).all()
    return templates.TemplateResponse("admin/users.html", {"request": request, "users": users, "roles": roles})

@router.post("/users/{user_id}/role", dependencies=[Depends(role_required("ADMIN"))])
def change_role(user_id: int, request: Request, role: str = Form(...), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user:
        db.query(UserRole).filter(UserRole.user_id == user.user_id).delete()
        target_role = _ensure_role(db, role)
        db.add(UserRole(user_id=user.user_id, role_id=target_role.role_id))
        db.commit()
        db.refresh(user)
        if request.session.get("user_id") == user.user_id:
            request.session["role"] = highest_role(user)
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/create", dependencies=[Depends(role_required("ADMIN"))])
def create_user(email: str = Form(...), username: str = Form(...), password: str = Form(...), role: str = Form("USER"), db: Session = Depends(get_db)):
    user = User(email=email, username=username, password_hash=bcrypt.hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    target_role = _ensure_role(db, role)
    db.add(UserRole(user_id=user.user_id, role_id=target_role.role_id))
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/{user_id}/delete", dependencies=[Depends(role_required("ADMIN"))])
def delete_user(user_id: int, db: Session = Depends(get_db), acting_admin: User = Depends(current_user)):
    user = db.get(User, user_id)
    if not user:
        return RedirectResponse(url="/admin/users", status_code=303)

    owned_projects = db.query(Project).filter(Project.created_by == user_id).all()
    if owned_projects:
        replacement = acting_admin if acting_admin.user_id != user_id else None
        if not replacement:
            replacement = (
                db.query(User)
                .join(UserRole, User.user_id == UserRole.user_id)
                .join(Role, Role.role_id == UserRole.role_id)
                .filter(Role.role_name == "ADMIN", User.user_id != user_id)
                .first()
            )
        if not replacement:
            return RedirectResponse(url="/admin/users", status_code=303)
        for project in owned_projects:
            project.created_by = replacement.user_id

    db.query(Task).filter(Task.assigned_to_user_id == user_id).update({Task.assigned_to_user_id: None})
    db.query(Task).filter(Task.created_by == user_id).update({Task.created_by: acting_admin.user_id})
    db.query(Comment).filter(Comment.author_id == user_id).delete()
    db.query(UserRole).filter(UserRole.user_id == user_id).delete()

    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
