
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterForm(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""

class LoginForm(BaseModel):
    email: EmailStr
    password: str

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: str = "MEDIUM"
    assignee_id: Optional[int] = None
    deadline: Optional[str] = None
