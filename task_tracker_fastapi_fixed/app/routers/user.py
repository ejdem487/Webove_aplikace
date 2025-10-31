from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256
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
def profile_save(request: Request, full_name: str = Form(""), avatar_url: str = Form(""), bio: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.full_name = full_name
    user.avatar_url = avatar_url
    user.bio = bio
    db.commit()
    return RedirectResponse(url="/user/profile", status_code=303)

@router.post("/password")
def change_password(old_password: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not pbkdf2_sha256.verify(old_password, user.password_hash):
        # můžeš vrátit flash zprávu do šablony, pro simple přesměruj zpět
        return RedirectResponse(url="/user/profile", status_code=303)
    user.password_hash = pbkdf2_sha256.hash(new_password)
    db.commit()
    return RedirectResponse(url="/user/profile", status_code=303)
