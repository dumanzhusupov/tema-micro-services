from fastapi import FastAPI
from models import TaskMessage
from utils import generate_task_one, generate_tasks_from_jsonl
from typing import Optional

app = FastAPI(title="Task Generator Service")

@app.post("/generate-task/")
async def generate_task_api(task: TaskMessage, subject: Optional[str] = "Алгебра"):
    """
    Генерирует одну новую задачу по примеру (payload TaskMessage).
    """
    new_task = generate_task_one(task.payload, subject=subject)
    return {"generated_task": new_task}

@app.post("/generate-tasks-from-jsonl/")
async def generate_tasks_from_jsonl_api(jsonl_path: str, subject: Optional[str] = "Алгебра"):
    """
    Генерирует задачи по всем примерам из указанного jsonl-файла.
    """
    tasks = generate_tasks_from_jsonl(jsonl_path, subject=subject)
    return {"generated_tasks": tasks}
