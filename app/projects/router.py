import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import Board, Project, Task, TaskResponsible, User, UserProject

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    slug: str


class CreateProjectRequest(BaseModel):
    title: str
    description: Optional[str] = None
    slug: str


@router.get("", response_model=List[ProjectResponse])
def get_my_projects(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    memberships = session.exec(
        select(UserProject).where(UserProject.user_id == current_user.id)
    ).all()
    project_ids = [m.project_id for m in memberships]
    if not project_ids:
        return []
    projects = session.exec(select(Project).where(Project.id.in_(project_ids))).all()
    return [ProjectResponse(id=str(p.id), title=p.title, description=p.description, slug=p.slug) for p in projects]


@router.post("", response_model=ProjectResponse)
def create_project(
    body: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if session.exec(select(Project).where(Project.slug == body.slug)).first():
        raise HTTPException(status_code=400, detail="Slug already taken")

    project = Project(title=body.title, description=body.description, slug=body.slug)
    session.add(project)
    session.flush()

    membership = UserProject(user_id=current_user.id, project_id=project.id)
    session.add(membership)
    session.commit()
    session.refresh(project)

    return ProjectResponse(id=str(project.id), title=project.title, description=project.description, slug=project.slug)


@router.post("/join")
def join_project(
    body: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    slug = body.get("slug")
    project = session.exec(select(Project).where(Project.slug == slug)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = session.exec(
        select(UserProject).where(
            UserProject.user_id == current_user.id,
            UserProject.project_id == project.id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    session.add(UserProject(user_id=current_user.id, project_id=project.id))
    session.commit()

    return ProjectResponse(id=str(project.id), title=project.title, description=project.description, slug=project.slug)


@router.delete("/{project_id}/leave")
def leave_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    membership = session.exec(
        select(UserProject).where(
            UserProject.user_id == current_user.id,
            UserProject.project_id == project_id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    session.delete(membership)
    session.commit()
    return {"ok": True}


class MemberResponse(BaseModel):
    id: str
    nickname: str


@router.get("/{project_id}/members", response_model=List[MemberResponse])
def get_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    memberships = session.exec(
        select(UserProject).where(UserProject.project_id == project_id)
    ).all()
    user_ids = [m.user_id for m in memberships]
    users = session.exec(select(User).where(User.id.in_(user_ids))).all()
    return [MemberResponse(id=str(u.id), nickname=u.nickname) for u in users]


def _require_member(user_id: uuid.UUID, project_id: uuid.UUID, session: Session):
    membership = session.exec(
        select(UserProject).where(
            UserProject.user_id == user_id,
            UserProject.project_id == project_id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")