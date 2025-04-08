from datetime import datetime
import re
import uuid


def parse_time(time_str: str) -> str | None:
    """
    Преобразует строку во время. Возвращает строку в формате HH:MM или None, если невалидно.
    """
    try:
        time_str = time_str.strip().replace('.', ':')

        # Вариант "14" → "14:00"
        if re.fullmatch(r'\d{1,2}', time_str):
            time_str = f"{int(time_str):02d}:00"

        # Вариант "1400" → "14:00"
        elif re.fullmatch(r'\d{4}', time_str):
            time_str = f"{time_str[:2]}:{time_str[2:]}"

        # Пробуем парсить
        parsed = datetime.strptime(time_str, "%H:%M")
        return parsed.strftime("%H:%M")
    except:
        return None


def generate_uuid() -> str:
    return str(uuid.uuid4())

def extract_links(text: str) -> list[str]:
    """
    Извлекает все ссылки из текста и возвращает список строк.
    """
    url_regex = r"https?://[^\s]+"
    return re.findall(url_regex, text or "")


def parse_date(date_str: str) -> datetime | None:
    """
    Принимает дату в формате:
    - '11.04' → подставляет текущий год (или следующий, если уже декабрь и дата в январе)
    - '11.04.2024' → принимает как есть
    - '2024-04-11' → ISO формат
    """
    date_str = date_str.strip()
    now = datetime.now()

    try:
        # Формат YYYY-MM-DD
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            return datetime.strptime(date_str, "%Y-%m-%d")

        # Формат DD.MM.YYYY
        if re.fullmatch(r"\d{2}.\d{2}.\d{4}", date_str):
            return datetime.strptime(date_str, "%d.%m.%Y")

        # Формат DD.MM (добавляем год)
        if re.fullmatch(r"\d{1,2}.\d{1,2}", date_str):
            day, month = map(int, date_str.split("."))
            year = now.year

            # Если сейчас декабрь, а дата указана на январь — значит в следующем году
            if now.month == 12 and month == 1:
                year += 1

            return datetime(year, month, day)

    except:
        return None
