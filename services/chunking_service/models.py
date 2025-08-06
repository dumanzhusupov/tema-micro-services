from pydantic import BaseModel
from typing import List

class ChunkRequest(BaseModel):
    text: str

class ChunkResponse(BaseModel):
    chunks: List[str]
