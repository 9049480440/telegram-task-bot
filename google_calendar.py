from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

def normalize_date(date_str):
    """
    Преобразует дату в формат YYYY-MM-DD
    Поддерживает:
    - 'DD.MM'
    - 'DD.MM.YY'
    - 'YYYY-MM-DD'
    """
    if "." in date_str:
        parts = date_str.strip().split(".")
        if len(parts) == 2:
            day, month = parts
            year = str(datetime.now().year)  # используем текущий год
        elif len(parts) == 3:
            day, month, year = parts
            if len(year) == 2:
                year = "20" + year
        else:
            raise ValueError("Неверный формат даты (ожидается DD.MM или DD.MM.YY)")
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return date_str  # уже в ISO (YYYY-MM-DD)


def get_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    service = build("calendar", "v3", credentials=creds)
    return service

def create_event(task):
    service = get_calendar_service()

    # Используем normalize_date для преобразования формата даты
    iso_date = normalize_date(task['deadline'])
    start_time_str = f"{iso_date}T{task['time']}:00"

    start_time = datetime.fromisoformat(start_time_str)
    end_time = start_time + timedelta(hours=1)

    event = {
        "summary": task["title"],
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "Asia/Yekaterinburg"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "Asia/Yekaterinburg"
        },
        "description": f"Задача из Telegram-бота",
    }

    created_event = service.events().insert(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
        body=event
    ).execute()

    return created_event.get("id")


def update_event(task):
    service = get_calendar_service()

    iso_date = normalize_date(task['deadline'])
    start_time_str = f"{iso_date}T{task['time']}:00"
    start_time = datetime.fromisoformat(start_time_str)
    end_time = start_time + timedelta(hours=1)  # Добавляем определение end_time

    event = service.events().get(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
        eventId=task["calendar_event_id"]
    ).execute()

    event["start"]["dateTime"] = start_time.isoformat()
    event["end"]["dateTime"] = end_time.isoformat()

    updated_event = service.events().update(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
        eventId=task["calendar_event_id"],
        body=event
    ).execute()

    return updated_event.get("id")

def delete_event(event_id):
    """
    Удаляет событие из Google Calendar по его ID.
    Корректно обрабатывает ситуации, когда событие не найдено.
    """
    if not event_id or event_id == "generated_event_id" or event_id == "None":
        print(f"Предупреждение: Попытка удалить событие с недопустимым ID: {event_id}")
        return False
        
    try:
        service = get_calendar_service()
        service.events().delete(
            calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
            eventId=event_id
        ).execute()
        print(f"Событие {event_id} успешно удалено из календаря")
        return True
    except Exception as e:
        # Проверяем, является ли ошибка 404 Not Found
        if hasattr(e, 'resp') and e.resp.status == 404:
            print(f"Предупреждение: Событие {event_id} не найдено в календаре")
        else:
            print(f"Ошибка при удалении события из календаря: {e}")
        return False


def add_task_to_calendar(title, date, time):
    task = {
        "title": title,
        "deadline": date,
        "time": time
    }
    return create_event(task)