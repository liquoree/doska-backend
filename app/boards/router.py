import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import Board, Task, TaskResponsible, User, UserProject

router = APIRouter(prefix="/projects/{project_id}/boards", tags=["boards"])


def _require_member(user_id: uuid.UUID, project_id: uuid.UUID, session: Session):
    membership = session.exec(
        select(UserProject).where(
            UserProject.user_id == user_id,
            UserProject.project_id == project_id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")


class BoardResponse(BaseModel):
    id: str
    title: str
    projectId: str


class CreateBoardRequest(BaseModel):
    title: str


@router.get("", response_model=List[BoardResponse])
def get_boards(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    boards = session.exec(select(Board).where(Board.project_id == project_id)).all()
    return [BoardResponse(id=str(b.id), title=b.title, projectId=str(b.project_id)) for b in boards]


@router.post("", response_model=BoardResponse)
def create_board(
    project_id: uuid.UUID,
    body: CreateBoardRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    board = Board(title=body.title, project_id=project_id)
    session.add(board)
    session.commit()
    session.refresh(board)
    return BoardResponse(id=str(board.id), title=board.title, projectId=str(board.project_id))


@router.delete("/{board_id}")
def delete_board(
    project_id: uuid.UUID,
    board_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    board = session.get(Board, board_id)
    if not board or board.project_id != project_id:
        raise HTTPException(status_code=404, detail="Board not found")

    # Delete tasks and their responsibles
    tasks = session.exec(select(Task).where(Task.board_id == board_id)).all()
    for task in tasks:
        responsibles = session.exec(select(TaskResponsible).where(TaskResponsible.task_id == task.id)).all()
        for r in responsibles:
            session.delete(r)
        session.delete(task)

    session.delete(board)
    session.commit()
    return {"ok": True}