from enum import Enum
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .langgraph_graph import create_graph, get_read_plan


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
    allow_file_read: bool = False
    target_file_path: str | None = None
    allow_full_repo_read: bool = False


class TaskResult(BaseModel):
    job_id: str
    task_type: str
    result: str
    quality_score: float
    architecture_summary: str
    architecture_diagram: str
    custom_answer: str
    read_files: list[str]


class ReadPlanRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    allow_file_read: bool = False
    target_file_path: str | None = None
    allow_full_repo_read: bool = False


class ReadPlanResponse(BaseModel):
    read_files: list[str]


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
            "allow_file_read": body.allow_file_read,
            "target_file_path": body.target_file_path or "",
            "allow_full_repo_read": body.allow_full_repo_read,
            "result": "",
            "quality_score": 0.0,
            "repo_overview": "",
            "architecture_summary": "",
            "architecture_diagram": "",
            "custom_answer": "",
            "repo_full_context": "",
            "target_file_content": "",
            "read_files": [],
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
        read_files=state.get("read_files", []),
    )


@app.post("/repos/read-plan", response_model=ReadPlanResponse)
async def read_plan(body: ReadPlanRequest) -> ReadPlanResponse:
    files = get_read_plan(
        repo_url=body.repo_url,
        branch=body.branch,
        allow_file_read=body.allow_file_read,
        target_file_path=body.target_file_path or "",
        allow_full_repo_read=body.allow_full_repo_read,
    )
    return ReadPlanResponse(read_files=files)
