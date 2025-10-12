# 📚 Инструкция по использованию Tasks Viewer

## Новые возможности

### ✨ Выбор папки с данными

Теперь вы можете выбирать папку в директории `data/` для просмотра задач из разных источников:

1. **Запустите сервер:**
   ```powershell
   python tasks_viewer.py
   ```

2. **Откройте браузер:**
   ```
   http://localhost:5001
   ```

3. **Выберите папку:**
   - В выпадающем меню "Выберите папку" появятся все папки из `data/`
   - Например: `retrieved_jsonl`, `algebra_6_1`, и т.д.
   - По умолчанию выбирается `retrieved_jsonl` (если она существует)

4. **Выберите файл:**
   - После выбора папки появятся доступные `.jsonl` файлы из этой папки
   - Выберите нужный файл для просмотра задач

## Структура данных

```
data/
├── retrieved_jsonl/
│   ├── algebra_6_1_mini_sample_retrieved_tasks.jsonl
│   ├── algebra_6_1_mini_sample_generated_tasks.jsonl
│   └── ...
├── algebra_6_1/
│   ├── algebra_6_1_retrieved_tasks.jsonl
│   ├── algebra_6_1_generated_tasks.jsonl
│   └── ...
└── другие_папки/
    └── ...
```

## API Endpoints

### GET `/api/folders`
Возвращает список всех папок в `data/`

**Пример:**
```javascript
fetch('http://localhost:5001/api/folders')
```

**Ответ:**
```json
["algebra_6_1", "retrieved_jsonl"]
```

### GET `/api/files?folder=<folder_name>`
Возвращает список `.jsonl` файлов из указанной папки

**Пример:**
```javascript
fetch('http://localhost:5001/api/files?folder=retrieved_jsonl')
```

**Ответ:**
```json
[
  "algebra_6_1_mini_sample_generated_tasks.jsonl",
  "algebra_6_1_mini_sample_retrieved_tasks.jsonl"
]
```

### GET `/api/tasks?folder=<folder_name>&file=<file_name>`
Возвращает задачи из указанного файла

**Пример:**
```javascript
fetch('http://localhost:5001/api/tasks?folder=retrieved_jsonl&file=algebra_6_1_mini_sample_retrieved_tasks.jsonl')
```

## Безопасность

- Реализована проверка на path traversal атаки
- Запрещены пути с `../`, `/`, `\` в именах папок и файлов
- Обрабатываются только `.jsonl` файлы

## Фильтрация и поиск

После загрузки задач доступны:
- 📁 Фильтр по теме
- 🎯 Фильтр по сложности (A, B, C)
- 🔧 Фильтр по типу (извлеченные/сгенерированные)
- 🔍 Поиск по тексту задач
- 🔄 Кнопка сброса всех фильтров

## Режим отладки

Кнопка "Показать исходный текст" позволяет переключаться между:
- Форматированным текстом (с рендерингом LaTeX)
- Исходным текстом (как в `.jsonl` файле)

Полезно для отладки проблем с форматированием.
