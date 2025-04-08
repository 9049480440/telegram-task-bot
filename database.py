import sqlite3
import json
from datetime import datetime, timedelta

DB_FILE = "db.sqlite3"

def get_connection():
    return sqlite3.connect(DB_FILE)

# 🧱 Создание таблиц
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        title TEXT,
        deadline TEXT,
        time TEXT,
        calendar_event_id TEXT,
        sheet_row INTEGER,
        status TEXT,
        msg_id INTEGER,
        created_at TEXT,
        completed_at TEXT,
        hours_spent REAL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_tasks (
        user_id INTEGER PRIMARY KEY,
        title TEXT,
        deadline TEXT,
        time TEXT,
        assigned_by TEXT,
        comment TEXT,
        step TEXT,
        messages TEXT,
        files TEXT,
        forwarded_from TEXT
    );
    """)

    conn.commit()
    conn.close()

# ✅ Tasks (основные задачи)
def add_task(task):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO tasks (id, user_id, title, deadline, time, calendar_event_id, sheet_row,
        status, msg_id, created_at, completed_at, hours_spent)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task["id"],
        task["user_id"],
        task["title"],
        task["deadline"],
        task.get("time", "10:00"),
        task["calendar_event_id"],
        task["sheet_row"],
        task["status"],
        task["msg_id"],
        task["created_at"],
        task["completed_at"],
        task["hours_spent"]
    ))

    conn.commit()
    conn.close()

def get_active_tasks(user_id=None, deadline=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM tasks WHERE status = 'active'"
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    if deadline == "tomorrow":
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        query += " AND deadline = ?"
        params.append(tomorrow)

    # Добавляем сортировку по дате дедлайна и времени
    query += " ORDER BY date(deadline), time"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

# Обновленная функция для файла database.py

def complete_task(task_id, hours_spent):
    conn = get_connection()
    cursor = conn.cursor()
    
    current_time = datetime.now().isoformat()
    
    cursor.execute("""
    UPDATE tasks
    SET status = 'done',
        completed_at = ?,
        hours_spent = ?
    WHERE id = ?
    """, (current_time, hours_spent, task_id))

    conn.commit()
    conn.close()
    
    return current_time  # Возвращаем время завершения для использования в других функциях

def update_task_deadline(task_id, new_deadline):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks SET deadline = ? WHERE id = ?
    """, (new_deadline, task_id))
    conn.commit()
    conn.close()

def update_task_status(task_id, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE tasks 
    SET status = ? 
    WHERE id = ?
    """, (status, task_id))

    conn.commit()
    conn.close()
    print(f"Статус задачи {task_id} обновлён на {status}")

# 🔔 Задачи с дедлайном через 1 час
# Улучшенная функция для database.py
def get_tasks_due_in_one_hour():
    """
    Получает задачи, до дедлайна которых осталось примерно 1-1.5 часа.
    Использует диапазон времени для более надежного обнаружения.
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()
    
    # Верхняя граница: задачи с дедлайном через 45-90 минут
    min_time = now + timedelta(minutes=45)
    max_time = now + timedelta(minutes=90)
    
    min_str = min_time.strftime("%Y-%m-%d %H:%M")
    max_str = max_time.strftime("%Y-%m-%d %H:%M")
    
    print(f"Ищу задачи с дедлайном между {min_str} и {max_str}")

    cursor.execute("""
        SELECT * FROM tasks
        WHERE status = 'active'
        AND datetime(deadline || ' ' || COALESCE(time, '10:00')) BETWEEN ? AND ?
    """, (min_str, max_str))

    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        print(f"Найдено {len(rows)} задач с приближающимся дедлайном")
    
    return rows

# ⏳ Pending tasks (в процессе заполнения)
def add_pending_task(user_id, data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("REPLACE INTO pending_tasks (user_id, step, messages, files, forwarded_from) VALUES (?, ?, ?, ?, ?)", (
        user_id,
        data.get("step"),
        json.dumps(data.get("messages", [])),
        json.dumps(data.get("files", [])),
        data.get("forwarded_from")
    ))

    conn.commit()
    conn.close()

def get_pending_task(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_tasks WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    columns = [column[0] for column in cursor.description]
    result = dict(zip(columns, row))
    conn.close()

    # Преобразуем JSON-строки в списки
    for key in ["messages", "files"]:
        try:
            result[key] = json.loads(result[key]) if result[key] else []
        except:
            result[key] = []

    return result

def update_pending_task(user_id, updates: dict):
    conn = get_connection()
    cursor = conn.cursor()

    # Загружаем текущую задачу
    cursor.execute("SELECT * FROM pending_tasks WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return

    columns = [column[0] for column in cursor.description]
    existing = dict(zip(columns, row))

    # Обновляем поля
    for key, value in updates.items():
        if key in ["messages", "files"] and isinstance(value, list):
            existing[key] = json.dumps(value)
        else:
            existing[key] = value

    # Преобразуем JSON-списки обратно, если нужно
    if isinstance(existing["messages"], list):
        existing["messages"] = json.dumps(existing["messages"])
    if isinstance(existing["files"], list):
        existing["files"] = json.dumps(existing["files"])

    # Записываем всё
    cursor.execute("""
        UPDATE pending_tasks SET
            title = ?,
            deadline = ?,
            time = ?,
            assigned_by = ?,
            comment = ?,
            step = ?,
            messages = ?,
            files = ?,
            forwarded_from = ?
        WHERE user_id = ?
    """, (
        existing.get("title"),
        existing.get("deadline"),
        existing.get("time"),
        existing.get("assigned_by"),
        existing.get("comment"),
        existing.get("step"),
        existing.get("messages"),
        existing.get("files"),
        existing.get("forwarded_from"),
        user_id
    ))

    conn.commit()
    conn.close()



def delete_pending_task(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_tasks WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Добавьте эту функцию в database.py, если она еще не существует

def get_task_by_id(task_id):
    """
    Получить задачу по её ID.
    Возвращает кортеж с данными задачи или None, если задача не найдена.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    
    conn.close()
    return task

# Функция для сохранения комментария к выполненной задаче
def add_completion_comment(task_id, comment):
    """
    Добавляет комментарий к выполненной задаче.
    Обновляет поле comment в таблице tasks.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE tasks
    SET comment = ?
    WHERE id = ?
    """, (comment, task_id))
    
    conn.commit()
    conn.close()
    
    return True

# Добавляем новую функцию в database.py для добавления колонки

def add_comment_column():
    """
    Добавляет колонку comment в таблицу tasks, если она еще не существует.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем, существует ли уже колонка comment
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if "comment" not in column_names:
        # Добавляем колонку comment
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN comment TEXT")
            print("Колонка comment успешно добавлена в таблицу tasks")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при добавлении колонки: {e}")
    else:
        print("Колонка comment уже существует в таблице tasks")
    
    conn.commit()
    conn.close()

# Добавьте вызов этой функции в блок if __name__ == "__main__": в конце файла

if __name__ == "__main__":
    create_tables()
    add_comment_column()  # Добавьте эту строку

# 🛠 Инициализация таблиц при первом запуске
if __name__ == "__main__":
    create_tables()
