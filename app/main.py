from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth_router import router as auth_router
from app.projects.router import router as projects_router
from app.boards.router import router as boards_router
from app.tasks.router import router as tasks_router

app = FastAPI(title="Doska API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(boards_router)
app.include_router(tasks_router)


@app.get("/")
def root():
    return {"status": "ok"}