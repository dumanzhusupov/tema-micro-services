from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ProcessChunksRequest(BaseModel):
    chunks: List[str]
    toc_text: str
    output_jsonl_path: Optional[str] = None
    start_chunk: int = 0
    end_chunk: Optional[int] = None

class ProcessChunksResponse(BaseModel):
    results: List[Dict[str, Any]]
    jsonl_path: str
