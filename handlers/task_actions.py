from aiogram import types
from database import update_task_status
import google_calendar

async def handle_task_actions(callback_query: types.CallbackQuery):
    """
    Обработка нажатий кнопок:
    [✅ Выполнено] – отмечает задачу как выполненную, запрашивает количество затраченных часов,
    обновляет БД, удаляет событие из календаря.
    [⏳ Продлить] – запрашивает новый срок/время, обновляет данные в календаре и БД.
    """
    data = callback_query.data
    if data == "completed":
        # Логика завершения задачи
        await callback_query.message.answer("Задача отмечена как выполненная. Сколько часов ты потратил(а)?")
        # После получения ответа – обновить статус и удалить событие из календаря:
        # update_task_status(...), google_calendar.delete_event(...)
    elif data == "postpone":
        await callback_query.message.answer("Укажите новый срок и время для задачи.")
        # Логика обновления задачи
