import uuid
from datetime import datetime

def generate_uuid() -> str:
    return str(uuid.uuid4())

def parse_date(date_str: str) -> datetime:
    """
    Преобразует строку в дату. Ожидаемый формат: YYYY-MM-DD.
    """
    return datetime.strptime(date_str, "%Y-%m-%d")

def parse_time(time_str: str) -> datetime:
    """
    Преобразует строку во время. Ожидаемый формат: HH:MM.
    """
    return datetime.strptime(time_str, "%H:%M")
    
def format_datetime(date_str: str, time_str: str) -> datetime:
    """
    Объединяет дату и время в один объект datetime.
    """
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
