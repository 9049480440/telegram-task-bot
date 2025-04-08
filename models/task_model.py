from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Task:
    id: str                     # UUID
    user_id: int                # Telegram ID
    title: str
    deadline: str               # Формат YYYY-MM-DD
    time: str                   # Время задачи в формате HH:MM
    calendar_event_id: str = None
    sheet_row: int = None
    status: str = "active"      # active / done
    msg_id: int = None
    created_at: str = datetime.now().isoformat()
    completed_at: str = None
    hours_spent: float = 0.0

    # Новые поля, которые использует task_actions.py
    assigned_by: Optional[str] = None
    comment: Optional[str] = None
    links: Optional[List[str]] = None
