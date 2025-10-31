
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..deps import role_required
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/users", response_class=HTMLResponse, dependencies=[Depends(role_required("ADMIN"))])
def list_users(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    return templates.TemplateResponse("admin/users.html", {"request": request, "users": users})

@router.post("/users/{user_id}/role", dependencies=[Depends(role_required("ADMIN"))])
def change_role(user_id: int, role: str = Form(...), db: Session = Depends(get_db), request: Request = None):
    user = db.get(User, user_id)
    if user:
        user.role = role
        db.commit()
        if request and request.session.get("user_id") == user.id:
            request.session["role"] = role
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/create", dependencies=[Depends(role_required("ADMIN"))])
def create_user(email: str = Form(...), full_name: str = Form(""), password: str = Form(...), role: str = Form("USER"), db: Session = Depends(get_db)):
    from passlib.hash import pbkdf2_sha256
    u = User(email=email, full_name=full_name, role=role, password_hash=pbkdf2_sha256.hash(password))
    db.add(u); db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/{user_id}/delete", dependencies=[Depends(role_required("ADMIN"))])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u:
        db.delete(u); db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
