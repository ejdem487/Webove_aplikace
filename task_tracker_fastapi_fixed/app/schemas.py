
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterForm(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str = Field(min_length=3, max_length=60)

class LoginForm(BaseModel):
    email: EmailStr
    password: str

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: str = "TODO"
    assignee_id: Optional[int] = None
