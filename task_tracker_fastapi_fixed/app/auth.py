
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from .db import get_db
from .models import User
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "Neplatné přihlašovací údaje."}, status_code=400)
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    return RedirectResponse(url="/", status_code=303)

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register")
def register(request: Request, email: str = Form(...), password: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "E-mail už existuje."}, status_code=400)
    user = User(email=email, password_hash=bcrypt.hash(password), full_name=full_name, role="USER")
    db.add(user); db.commit()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
