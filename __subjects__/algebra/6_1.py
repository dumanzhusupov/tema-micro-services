import sys
import os
from dotenv import load_dotenv

# Текущий файл находится в __subjects__\algebra\6_1.py
# Нужно подняться на 2 уровня вверх до корня проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

import tema.pipeline
import __subjects__.algebra.toc_file as toc_file

import asyncio

if __name__ == "__main__":
    load_dotenv()
    
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
        
    load_dotenv()

    print(os.getenv("OPENAI_API_KEY"))

    toc = toc_file.toc_algebra_6_1

    async def main():
        #data\books_md\algebra_6_1.md
        res = await tema.pipeline.process_book(
            input_file=os.path.join(project_root, "data", "books_md", "algebra_6_1.md"),
            output_dir=os.path.join(project_root, "data", "algebra_6_1"),
            toc=toc)
        print(res)

    asyncio.run(main())


