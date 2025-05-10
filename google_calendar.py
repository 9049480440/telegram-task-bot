from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

def normalize_date(date_str):
    """
    Преобразует дату в формат YYYY-MM-DD
    Поддерживает разные форматы:
    - 'DD.MM' - текущий год
    - 'DD.MM.YY' - 20YY год
    - 'DD.MM.YYYY' - полный формат
    - 'DD/MM' - текущий год
    - 'DD/MM/YY' - 20YY год
    - 'YYYY-MM-DD' - ISO формат
    - 'завтра' - завтрашний день
    - 'сегодня' - сегодняшний день
    - 'понедельник', 'вторник' и т.д. - ближайший указанный день недели
    """
    date_str = date_str.strip().lower()
    today = datetime.now()

    # Проверяем специальные ключевые слова
    if date_str in ['сегодня', 'today']:
        return today.strftime("%Y-%m-%d")

    if date_str in ['завтра', 'tomorrow']:
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")

    # Дни недели
    days_ru = {
        'понедельник': 0, 'вторник': 1, 'среда': 2, 'четверг': 3,
        'пятница': 4, 'суббота': 5, 'воскресенье': 6
    }
    days_en = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }

    # Сокращенные названия дней недели
    short_days_ru = {
        'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5, 'вс': 6
    }
    short_days_en = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }

    # Объединяем все словари
    all_days = {**days_ru, **days_en, **short_days_ru, **short_days_en}

    if date_str in all_days:
        target_day = all_days[date_str]
        current_day = today.weekday()
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Если день уже прошел на этой неделе, берем следующую
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
        return target_date.strftime("%Y-%m-%d")

    # Обработка обычных дат в разных форматах
    if "." in date_str:
        parts = date_str.split(".")
    elif "/" in date_str:
        parts = date_str.split("/")
    elif "-" in date_str and len(date_str.split("-")) == 3:
        # Проверяем, что это формат YYYY-MM-DD
        parts = date_str.split("-")
        if len(parts[0]) == 4:  # Если первая часть - год (YYYY)
            return date_str  # Возвращаем как есть
        # Иначе обрабатываем как DD-MM-YYYY
        day, month, year = parts
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    else:
        raise ValueError("Неверный формат даты")

    if len(parts) == 2:
        day, month = parts
        year = str(today.year)  # Используем текущий год
    elif len(parts) == 3:
        day, month, year = parts
        if len(year) == 2:
            year = "20" + year
    else:
        raise ValueError("Неверный формат даты")

    # Проверяем корректность даты
    try:
        # Проверяем, что день и месяц - числа
        day = int(day)
        month = int(month)
        year = int(year)

        # Проверяем диапазоны
        if not (1 <= day <= 31) or not (1 <= month <= 12):
            raise ValueError("Неверный день или месяц")

        # Проверяем существование даты (например, 30 февраля)
        datetime(year, month, day)
    except ValueError as e:
        raise ValueError(f"Некорректная дата: {e}")

    return f"{year}-{month:02d}-{day:02d}"


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