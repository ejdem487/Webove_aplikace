
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

@router.post("/users/{user_id}/role", response_class=HTMLResponse, dependencies=[Depends(role_required("ADMIN"))])
def change_role(user_id: int, role: str = Form(...), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user:
        user.role = role
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
