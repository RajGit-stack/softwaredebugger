from enum import Enum
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .langgraph_graph import create_graph


class TaskType(str, Enum):
    repo_analyser = "repo_analyser"
    bug_fixer = "bug_fixer"
    test_generator = "test_generator"
    doc_generator = "doc_generator"
    code_search = "code_search"


class CreateTaskBody(BaseModel):
    repo_url: str
    task_type: TaskType
    branch: str = "main"
    description: str | None = None
    custom_question: str | None = None


class TaskResult(BaseModel):
    job_id: str
    task_type: str
    result: str
    quality_score: float
    architecture_summary: str
    architecture_diagram: str
    custom_answer: str


app = FastAPI(title="AI Software Debugger Agent Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can replace "*" with your Vercel URL for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = create_graph()


@app.post("/tasks", response_model=TaskResult)
async def create_task(body: CreateTaskBody) -> TaskResult:
    state = graph.invoke(
        {
            "repo_url": body.repo_url,
            "task_type": body.task_type.value,
            "branch": body.branch,
            "description": body.description or "",
            "custom_question": body.custom_question or "",
            "result": "",
            "quality_score": 0.0,
            "repo_overview": "",
            "architecture_summary": "",
            "architecture_diagram": "",
            "custom_answer": "",
        }
    )
    return TaskResult(
        job_id=str(uuid4()),
        task_type=body.task_type.value,
        result=state.get("result", ""),
        quality_score=float(state.get("quality_score", 0.0) or 0.0),
        architecture_summary=state.get("architecture_summary", ""),
        architecture_diagram=state.get("architecture_diagram", ""),
        custom_answer=state.get("custom_answer", ""),
    )
