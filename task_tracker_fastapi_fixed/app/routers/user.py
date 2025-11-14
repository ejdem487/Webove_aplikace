from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from ..db import get_db
from ..deps import current_user
from ..models import User
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["user"])
templates = Jinja2Templates(directory="templates")

@router.get("/profile", response_class=HTMLResponse)
def profile_form(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse("user/profile.html", {"request": request, "user": user})

@router.post("/profile")
def profile_save(request: Request, username: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not username.strip():
        return RedirectResponse(url="/user/profile", status_code=303)
    exists = db.query(User).filter(User.username == username, User.user_id != user.user_id).first()
    if exists:
        return RedirectResponse(url="/user/profile", status_code=303)
    user.username = username.strip()
    db.commit()
    return RedirectResponse(url="/user/profile", status_code=303)

@router.post("/password")
def change_password(old_password: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not bcrypt.verify(old_password, user.password_hash):
        return RedirectResponse(url="/user/profile", status_code=303)
    user.password_hash = bcrypt.hash(new_password)
    db.commit()
    return RedirectResponse(url="/user/profile", status_code=303)
