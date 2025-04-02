from aiogram import types
from database import get_active_tasks

async def handle_task_list(message: types.Message):
    """
    Обработка команды /мои_задачи.
    Выводит список всех активных задач с кнопкой [✅] для завершения.
    """
    tasks = get_active_tasks()
    if tasks:
        response = "Ваши активные задачи:\n"
        for task in tasks:
            response += f"• {task[2]} (ID: {task[0]})\n"  # task[2] – title, task[0] – id
        await message.answer(response)
    else:
        await message.answer("Нет активных задач.")
