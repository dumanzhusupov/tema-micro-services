from fastapi import FastAPI, UploadFile, File, HTTPException
from models import ChunkResponse
from utils import chunk_text, extract_table_of_contents, beautify_topics
import os

app = FastAPI(title="Chunking/Preprocess Service")

@app.post("/chunk/", response_model=ChunkResponse)
async def chunk_endpoint(file: UploadFile = File(...), warn_tokens: int = 0, model: str = "gpt-3.5-turbo"):
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Требуется .md файл")
    content = await file.read()
    text = content.decode("utf-8")
    chunks = chunk_text(text, warn_tokens=warn_tokens, model=model)
    return ChunkResponse(chunks=chunks)

@app.post("/extract_toc/")
async def extract_toc_endpoint(file: UploadFile = File(...)):
    if not (file.filename.lower().endswith(".md") or file.filename.lower().endswith(".txt")):
        raise HTTPException(status_code=400, detail="Требуется .md или .txt файл")
    content = await file.read()
    text = content.decode("utf-8")
    toc = extract_table_of_contents(text)
    #TODO добавить обработку случая, когда оглавление не найдено 
    # (вызвать функцию которая чекнет превые 15 стр и послдежние 15 стр и 
    # с помощью ГПТ вернет отформатированный Table Of Contents)
    if toc is None:
        return {"toc": None}
    beautified = await beautify_topics(toc)
    return {"toc": beautified}
