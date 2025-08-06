import os
from utils import process_chunk, process_jsonl_chunks, run_full_pipeline

def test_process_chunk():
    chunk = "1. Решите уравнение: $x^2 - 4 = 0$"
    toc = "- Квадратные уравнения\n- Решение уравнений\n- Формулы сокращённого умножения"
    result = process_chunk(chunk, toc)
    print("process_chunk result:", result)

def test_process_jsonl_chunks():
    chunks = [
        "1. Решите уравнение: $x^2 - 4 = 0$",
        "2. Найдите значение выражения: $2^3 + 2^2$"
    ]
    toc = "- Квадратные уравнения\n- Решение уравнений\n- Формулы сокращённого умножения"
    output_path = "test_output.jsonl"
    results, path = process_jsonl_chunks(chunks, output_path, toc)
    print("process_jsonl_chunks results:", results)
    print("Output file:", path)

def test_run_full_pipeline():
    chunks = [
        "1. Решите уравнение: $x^2 - 4 = 0$",
        "2. Найдите значение выражения: $2^3 + 2^2$"
    ]
    toc = "- Квадратные уравнения\n- Решение уравнений\n- Формулы сокращённого умножения"
    output_path = "test_full_pipeline.jsonl"
    results, path = run_full_pipeline(chunks, toc, output_path)
    print("run_full_pipeline results:", results)
    print("Output file:", path)

if __name__ == "__main__":
    test_process_chunk()
    test_process_jsonl_chunks()
    test_run_full_pipeline()
