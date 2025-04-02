from aiogram import types
from gpt_parser import parse_task, clarify_missing_fields
from database import add_pending_task
from utils.helpers import generate_uuid

async def handle_new_task(message: types.Message):
    """
    Обработка нового сообщения с задачей.
    1. Отправляет текст в gpt_parser для первичного извлечения данных.
    2. Если какие-то поля равны null, запрашивает уточнения.
    3. Сохраняет промежуточные данные в таблицу pending_tasks.
    """
    text = message.text
    task_data = parse_task(text)
    # Если есть незаполненные поля – инициируем уточнение
    if any(value is None for value in task_data.values()):
        task_data = clarify_missing_fields(task_data)
        # Сохранить в pending_tasks для дальнейшего уточнения
        add_pending_task(message.from_user.id, task_data)
        await message.answer("Пожалуйста, уточните недостающие данные.")
    else:
        # Если все данные собраны, показать сводное сообщение с кнопками подтверждения
        confirmation_text = (
            f"📌 Задача: {task_data.get('title')}\n"
            f"📅 Срок: {task_data.get('deadline')} {task_data.get('time')}\n"
            f"👤 Поставил: {task_data.get('assigned_by')}\n"
            f"💬 Комментарий: {task_data.get('comment')}\n\n"
            "Добавить в таблицу и календарь?"
        )
        await message.answer(confirmation_text)
        # Далее – логика обработки кнопок подтверждения (в task_actions.py)
