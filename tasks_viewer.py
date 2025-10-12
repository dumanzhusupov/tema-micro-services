import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

# --- Конфигурация ---
# Порт, на котором будет работать сервер
PORT = 5001
# Корневая директория с данными
DATA_ROOT = os.path.join(os.path.dirname(__file__), 'data')
# Имя основного HTML файла
HTML_FILE = 'frontend.html'

# --- Инициализация Flask ---
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Отдаёт основной HTML файл."""
    return send_from_directory('.', HTML_FILE)

@app.route('/api/folders')
def list_folders():
    """Отдаёт список всех папок в data."""
    try:
        folders = []
        for item in os.listdir(DATA_ROOT):
            item_path = os.path.join(DATA_ROOT, item)
            if os.path.isdir(item_path):
                folders.append(item)
        return jsonify(sorted(folders))
    except FileNotFoundError:
        return jsonify({"error": f"Директория не найдена: {DATA_ROOT}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files')
def list_files():
    """Отдаёт список всех .jsonl файлов из выбранной папки."""
    folder = request.args.get('folder', 'retrieved_jsonl')
    
    # Проверка безопасности
    if '/' in folder or '\\' in folder or '..' in folder:
        return jsonify({"error": "Некорректное имя папки"}), 400
    
    folder_path = os.path.join(DATA_ROOT, folder)
    
    try:
        # Получаем все файлы, которые заканчиваются на .jsonl
        files = sorted([f for f in os.listdir(folder_path) if f.endswith('.jsonl')])
        # Возвращаем как JSON
        return jsonify(files)
    except FileNotFoundError:
        return jsonify({"error": f"Директория не найдена: {folder_path}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks')
def get_tasks():
    """Отдаёт содержимое конкретного .jsonl файла."""
    # Получаем имя файла из GET-параметра ?file=...
    filename = request.args.get('file')
    folder = request.args.get('folder', 'retrieved_jsonl')
    
    if not filename:
        return jsonify({"error": "Параметр 'file' обязателен"}), 400

    # Проверка безопасности: убеждаемся, что имя файла не содержит пути
    if '/' in filename or '\\' in filename:
        return jsonify({"error": "Некорректное имя файла"}), 400
    
    if '/' in folder or '\\' in folder or '..' in folder:
        return jsonify({"error": "Некорректное имя папки"}), 400

    file_path = os.path.join(DATA_ROOT, folder, filename)

    try:
        tasks = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Пропускаем пустые строки
                if line.strip():
                    # Каждая строка - это отдельный JSON
                    tasks.append(json.loads(line))
        return jsonify(tasks)
    except FileNotFoundError:
        return jsonify({"error": f"Файл не найден: {filename}"}), 404
    except Exception as e:
        return jsonify({"error": f"Ошибка при чтении файла: {str(e)}"}), 500

if __name__ == '__main__':
    print(f"🚀 Сервер запущен на http://localhost:{PORT}")
    print(f"📂 Обслуживается директория: {DATA_ROOT}")
    # Запускаем сервер
    app.run(host='0.0.0.0', port=PORT, debug=True)
