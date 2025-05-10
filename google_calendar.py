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
    try:
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        print(f"Данные для аутентификации: client_id={client_id[:5]}..., refresh_token={refresh_token[:5] if refresh_token else None}...")

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=creds)
        print("Сервис календаря успешно создан")
        return service
    except Exception as e:
        print(f"ОШИБКА при создании сервиса календаря: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        raise

def create_event(task):
    try:
        print(f"Начинаю создание события календаря для задачи: {task['title']}")
        service = get_calendar_service()
        print(f"Сервис календаря получен")

        # Используем normalize_date для преобразования формата даты
        iso_date = normalize_date(task['deadline'])
        start_time_str = f"{iso_date}T{task['time']}:00"
        print(f"Дата и время начала: {start_time_str}")

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
        print(f"Сформирован объект события: {event}")

        calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        print(f"ID календаря: {calendar_id}")

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        event_id = created_event.get("id")
        print(f"Событие успешно создано в календаре, ID: {event_id}")
        return event_id
    except Exception as e:
        print(f"ОШИБКА при создании события в календаре: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        return None


def update_event(task):
    try:
        print(f"Начинаю обновление события в календаре для задачи с ID: {task['calendar_event_id']}")
        service = get_calendar_service()

        iso_date = normalize_date(task['deadline'])
        start_time_str = f"{iso_date}T{task['time']}:00"
        print(f"Новая дата и время начала: {start_time_str}")

        start_time = datetime.fromisoformat(start_time_str)
        end_time = start_time + timedelta(hours=1)

        calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        print(f"ID календаря: {calendar_id}, ID события: {task['calendar_event_id']}")

        event = service.events().get(
            calendarId=calendar_id,
            eventId=task["calendar_event_id"]
        ).execute()
        print(f"Получено существующее событие")

        event["start"]["dateTime"] = start_time.isoformat()
        event["end"]["dateTime"] = end_time.isoformat()

        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=task["calendar_event_id"],
            body=event
        ).execute()

        event_id = updated_event.get("id")
        print(f"Событие успешно обновлено в календаре, ID: {event_id}")
        return event_id
    except Exception as e:
        print(f"ОШИБКА при обновлении события в календаре: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        return None

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
    try:
        print(f"Добавление задачи в календарь: '{title}', дата={date}, время={time}")
        task = {
            "title": title,
            "deadline": date,
            "time": time
        }
        return create_event(task)
    except Exception as e:
        print(f"ОШИБКА при добавлении задачи в календарь: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        return None