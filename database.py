import sqlite3
import os

DATABASE = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Создание таблицы tasks
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
    # Создание таблицы pending_tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_tasks (
      user_id INTEGER PRIMARY KEY,
      title TEXT,
      deadline TEXT,
      time TEXT,
      assigned_by TEXT,
      comment TEXT,
      step TEXT
    );
    """)
    conn.commit()
    conn.close()

def add_task(task):
    """
    Добавляет задачу в таблицу tasks.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Пример запроса, необходимо заполнить поля
    cursor.execute("""
    INSERT INTO tasks (id, user_id, title, deadline, time, calendar_event_id, sheet_row, status, msg_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (task.id, task.user_id, task.title, task.deadline, task.time, task.calendar_event_id, task.sheet_row, task.status, task.msg_id, task.created_at))
    conn.commit()
    conn.close()

def update_task_status(task_id, status, completed_at=None, hours_spent=None):
    """
    Обновляет статус задачи в таблице tasks.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks
    SET status = ?, completed_at = ?, hours_spent = ?
    WHERE id = ?
    """, (status, completed_at, hours_spent, task_id))
    conn.commit()
    conn.close()

def get_active_tasks(**filters):
    """
    Возвращает список активных задач. Возможные фильтры: deadline="tomorrow", time_delta=60 (за 60 минут до дедлайна).
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Простейший запрос – нужно доработать в зависимости от фильтров
    cursor.execute("SELECT * FROM tasks WHERE status = 'active'")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def add_pending_task(user_id, data):
    """
    Добавляет запись в таблицу pending_tasks для уточнения данных.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO pending_tasks (user_id, title, deadline, time, assigned_by, comment, step)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, data.get("title"), data.get("deadline"), data.get("time"), data.get("assigned_by"), data.get("comment"), data.get("step")))
    conn.commit()
    conn.close()
