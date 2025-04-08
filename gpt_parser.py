# gpt_parser.py

import openai
import os
import json

openai.api_key = os.getenv("OPENAI_API_KEY")


def parse_task(text: str, files: list[str] = None, sender_name: str = None) -> dict:
    """
    Отправляет текст и метаинформацию в GPT и получает структурированную информацию о задаче.
    """

    files_info = ""
    if files:
        files_info = "\n\nТакже к задаче приложены файлы:\n" + "\n".join(f"📎 {f}" for f in files)

    sender_info = f"\n\nСообщения были пересланы от: {sender_name}" if sender_name else ""

    full_prompt = f"""
Ты — виртуальный помощник по управлению задачами.

Пользователь прислал фрагменты задачи. На их основе:
1. Сформулируй ПОЛНОЕ описание задачи (внятное, связное, в одну фразу).
2. Извлеки:
   - срок (deadline) — формат YYYY-MM-DD
   - время (task_time) — формат HH:MM
   - кто дал задачу (task_giver)
   - комментарий или контекст (comment)
   - ссылки (links) — выдели все, что есть

Если чего-то нет — пиши null.

Формат ответа строго JSON:
{{
  "task_title": "...",
  "deadline": "YYYY-MM-DD" или null,
  "task_time": "HH:MM" или null,
  "task_giver": "Имя или отдел" или null,
  "comment": "Контекст задачи" или null,
  "links": ["https://...", "..."]
}}

Вот фрагменты задачи:
\"\"\"
{text}
\"\"\"{sender_info}{files_info}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3,
            max_tokens=700,
        )
        content = response.choices[0].message["content"]
        return json.loads(content)

    except Exception as e:
        print("GPT error:", e)
        return {}
