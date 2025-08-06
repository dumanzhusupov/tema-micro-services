from fastapi import FastAPI, Form
from typing import List, Optional
from models import ProcessChunksRequest, ProcessChunksResponse
from utils import process_jsonl_chunks
import tempfile
import os

app = FastAPI(title="Retrieval Service")

@app.post("/process_chunks/", response_model=ProcessChunksResponse)
async def process_chunks_endpoint(
    request: ProcessChunksRequest
):
    """
    API endpoint для обработки чанков через GPT с учетом списка тем.
    Возвращает список результатов и путь к созданному jsonl-файлу.
    """
    output_jsonl_path = request.output_jsonl_path
    if output_jsonl_path is None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", dir=os.getcwd()) as tmp:
            output_jsonl_path = tmp.name
    results, jsonl_path = process_jsonl_chunks(
        chunks=request.chunks,
        toc_text=request.toc_text,
        output_jsonl_path=output_jsonl_path,
        start_chunk=request.start_chunk,
        end_chunk=request.end_chunk
    )
    return ProcessChunksResponse(results=results, jsonl_path=jsonl_path)
