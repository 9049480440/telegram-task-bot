import openai
import os
from utils.helpers import generate_uuid

openai.api_key = os.getenv("OPENAI_API_KEY")

def parse_task(text: str) -> dict:
    """
    Отправляет текст задачи в OpenAI и получает JSON с полями:
    title, deadline, time, assigned_by, comment.
    Если есть null, бот должен задавать уточняющие вопросы.
    """
    # Заготовка запроса к OpenAI
    prompt = f"""
Ты помощник по задачам. Получив текст, выдели:
- Название задачи
- Крайний срок (YYYY-MM-DD) или null
- Время задачи (HH:MM) или null
- Кто дал задачу или null
- Комментарий или null

Возвращай строго JSON.
Текст: {text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )
    # Преобразование ответа в JSON (обработка ошибок опущена)
    result = response.choices[0].message.content
    # Здесь добавить разбор и валидацию JSON
    return result

def clarify_missing_fields(task_json: dict) -> dict:
    """
    Если в результате парсинга есть поля со значением null,
    инициировать последовательность уточняющих вопросов.
    """
    # Заготовка логики уточнения
    # Например: если task_json["deadline"] is None, задать вопрос о дате.
    return task_json
