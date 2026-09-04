import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


# ─── Link tables ────────────────────────────────────────────────────────────

class UserProject(SQLModel, table=True):
    __tablename__ = "user_project"
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.id", primary_key=True)


class TaskResponsible(SQLModel, table=True):
    __tablename__ = "task_responsible"
    task_id: uuid.UUID = Field(foreign_key="task.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)


# ─── User ────────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "user"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nickname: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str


# ─── Project ─────────────────────────────────────────────────────────────────

class Project(SQLModel, table=True):
    __tablename__ = "project"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    description: Optional[str] = None
    slug: str = Field(unique=True, index=True)


# ─── Board ───────────────────────────────────────────────────────────────────

class Board(SQLModel, table=True):
    __tablename__ = "board"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    project_id: uuid.UUID = Field(foreign_key="project.id")


# ─── Task ────────────────────────────────────────────────────────────────────

class Task(SQLModel, table=True):
    __tablename__ = "task"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    is_completed: bool = False
    board_id: uuid.UUID = Field(foreign_key="board.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    position: int = Field(default=0)