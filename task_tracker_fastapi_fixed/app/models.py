
from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db import Base

class Role(Base):
    __tablename__ = "roles"
    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str] = mapped_column(String, unique=True)
    user_links = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    username: Mapped[str] = mapped_column(String, unique=True)
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assigned_to_user_id")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", foreign_keys="Project.created_by", cascade="all, delete-orphan")
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    member_projects = relationship("Project", secondary="project_members", back_populates="members", viewonly=True)

    @property
    def role_names(self) -> list[str]:
        return [link.role.role_name for link in self.roles if link.role]

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id"), primary_key=True)
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_links")
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

class Project(Base):
    __tablename__ = "projects"
    project_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    owner = relationship("User", back_populates="projects", foreign_keys=[created_by])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    memberships = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    members = relationship("User", secondary="project_members", back_populates="member_projects")

    def has_member(self, user_id: Optional[int]) -> bool:
        if user_id is None:
            return False
        if self.created_by == user_id:
            return True
        return any(link.user_id == user_id for link in self.memberships)

class Task(Base):
    __tablename__ = "tasks"
    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="TODO")
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

class ProjectMember(Base):
    __tablename__ = "project_members"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    project = relationship("Project", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

class Comment(Base):
    __tablename__ = "comments"
    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    text: Mapped[str] = mapped_column(Text)
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
