import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import Board, Task, TaskResponsible, User, UserProject
from app.email import send_responsible_email


router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


def _require_member(user_id: uuid.UUID, project_id: uuid.UUID, session: Session):
    membership = session.exec(
        select(UserProject).where(
            UserProject.user_id == user_id,
            UserProject.project_id == project_id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")


class TaskResponse(BaseModel):
    id: str
    title: str
    isCompleted: bool
    boardId: str
    createdAt: str
    responsibleIds: List[str]
    position: int


class CreateTaskRequest(BaseModel):
    title: str
    board_id: uuid.UUID


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    is_completed: Optional[bool] = None
    board_id: Optional[uuid.UUID] = None
    position: Optional[int] = None


def _task_to_response(task: Task, session: Session) -> TaskResponse:
    responsibles = session.exec(
        select(TaskResponsible).where(TaskResponsible.task_id == task.id)
    ).all()
    return TaskResponse(
        id=str(task.id),
        title=task.title,
        isCompleted=task.is_completed,
        boardId=str(task.board_id),
        createdAt=task.created_at.isoformat(),
        responsibleIds=[str(r.user_id) for r in responsibles],
        position=task.position,
    )

@router.get("", response_model=List[TaskResponse])
def get_tasks(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    boards = session.exec(select(Board).where(Board.project_id == project_id)).all()
    board_ids = [b.id for b in boards]
    if not board_ids:
        return []
    tasks = session.exec(select(Task).where(Task.board_id.in_(board_ids))).all()
    return [_task_to_response(t, session) for t in tasks]


@router.post("", response_model=TaskResponse)
def create_task(
    project_id: uuid.UUID,
    body: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    board = session.get(Board, body.board_id)
    if not board or board.project_id != project_id:
        raise HTTPException(status_code=404, detail="Board not found")

    task = Task(title=body.title, board_id=body.board_id)
    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_to_response(task, session)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    body: UpdateTaskRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.title is not None:
        task.title = body.title
    if body.is_completed is not None:
        task.is_completed = body.is_completed
    if body.board_id is not None:
        # проверяем что доска принадлежит этому проекту
        board = session.get(Board, body.board_id)
        if not board or board.project_id != project_id:
            raise HTTPException(status_code=404, detail="Board not found")
        task.board_id = body.board_id
    if body.position is not None:
        task.position = body.position

    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_to_response(task, session)


@router.delete("/{task_id}")
def delete_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    responsibles = session.exec(
        select(TaskResponsible).where(TaskResponsible.task_id == task_id)
    ).all()

    for r in responsibles:
        session.delete(r)

    session.flush()  # сначала удаляем task_responsible из бд

    session.delete(task)
    session.commit()
    return {"ok": True}

@router.post("/{task_id}/responsible/{user_id}", response_model=TaskResponse)
def add_responsible(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    _require_member(user_id, project_id, session)

    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing = session.exec(
        select(TaskResponsible).where(
            TaskResponsible.task_id == task_id,
            TaskResponsible.user_id == user_id,
        )
    ).first()
    if not existing:
        session.add(TaskResponsible(task_id=task_id, user_id=user_id))
        session.commit()

        user = session.get(User, user_id)
        if user and user.email:
            background_tasks.add_task(send_responsible_email, user.email, task.title)

    return _task_to_response(task, session)


@router.delete("/{task_id}/responsible/{user_id}", response_model=TaskResponse)
def remove_responsible(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_member(current_user.id, project_id, session)
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    responsible = session.exec(
        select(TaskResponsible).where(
            TaskResponsible.task_id == task_id,
            TaskResponsible.user_id == user_id,
        )
    ).first()
    if responsible:
        session.delete(responsible)
        session.commit()

    return _task_to_response(task, session)