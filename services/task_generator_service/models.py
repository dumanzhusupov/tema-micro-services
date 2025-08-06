from pydantic import BaseModel
from typing import Any, Dict

class TaskMessage(BaseModel):
    task_id: str
    payload: Dict[str, Any]
    created_at: str
