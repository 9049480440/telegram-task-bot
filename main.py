# main.py

import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

from database import create_tables, get_pending_task, add_comment_column
import scheduler
import handlers.start as start_handler
import handlers.new_task as new_task_handler
import handlers.task_actions as task_actions_handler
import handlers.task_list as task_list_handler

load_dotenv()
print("DEBUG: BOT_TOKEN =", os.getenv("BOT_TOKEN"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")


def clear_pending_tasks():
    import sqlite3
    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_tasks")
    conn.commit()
    conn.close()


async def handle_keyboard_tasks(message: types.Message):
    """Обработчик кнопки 'Мои задачи' с клавиатуры"""
    await task_list_handler.handle_task_list(message)

async def handle_keyboard_new_task(message: types.Message):
    """Обработчик кнопки 'Новая задача' с клавиатуры"""
    await new_task_handler.start_collecting_task(message)


async def main():
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Команды
    dp.message.register(start_handler.handle_start, Command("start"))
    dp.message.register(task_list_handler.handle_task_list, Command("мои_задачи"))
    dp.message.register(new_task_handler.start_collecting_task, Command("задача"))

    # Обработчики кнопок клавиатуры
    dp.message.register(handle_keyboard_tasks, F.text == "📋 Мои задачи")
    dp.message.register(handle_keyboard_new_task, F.text == "➕ Новая задача")

    # Важно! Сначала регистрируем обработчики для состояний FSM
    dp.message.register(task_actions_handler.handle_hours_input, task_actions_handler.TaskStates.waiting_for_hours)
    dp.message.register(task_actions_handler.handle_comment_input, task_actions_handler.TaskStates.waiting_for_comment)
    dp.message.register(task_actions_handler.handle_new_deadline_input, task_actions_handler.TaskStates.waiting_for_new_deadline)
    dp.message.register(task_actions_handler.handle_new_time_input, task_actions_handler.TaskStates.waiting_for_new_time)

    # Затем регистрируем обработчики для callback_query
    dp.callback_query.register(task_actions_handler.handle_add_comment_yes, F.data == "add_comment_yes")
    dp.callback_query.register(task_actions_handler.handle_add_comment_no, F.data == "add_comment_no")
    dp.callback_query.register(task_actions_handler.handle_collect_done, F.data == "collect_done")
    dp.callback_query.register(task_actions_handler.handle_collect_cancel, F.data == "collect_cancel")
    dp.callback_query.register(task_actions_handler.handle_confirm_add, F.data == "confirm_add")
    dp.callback_query.register(task_actions_handler.handle_collect_cancel, F.data == "cancel_add")
    dp.callback_query.register(task_actions_handler.handle_forwarded_yes, F.data == "forwarded_yes")
    dp.callback_query.register(task_actions_handler.handle_forwarded_no, F.data == "forwarded_no")
    dp.callback_query.register(new_task_handler.handle_reset_task, F.data == "reset_task")
    dp.callback_query.register(new_task_handler.handle_confirm_assigned_yes, F.data == "confirm_assigned_yes")
    dp.callback_query.register(new_task_handler.handle_confirm_assigned_no, F.data == "confirm_assigned_no")
    dp.callback_query.register(task_actions_handler.handle_edit_fields, F.data == "edit_fields")
    dp.callback_query.register(task_actions_handler.handle_edit_field_selection, F.data.startswith("edit_"))
    
    # Регистрация обработчиков для задач
    dp.callback_query.register(task_actions_handler.handle_mark_done, F.data.startswith("mark_done_"))
    dp.callback_query.register(task_actions_handler.handle_extend_deadline, F.data.startswith("extend_deadline_"))
    
    # Регистрация обработчиков для улучшенного списка задач
    dp.callback_query.register(task_list_handler.handle_view_task, F.data.startswith("view_task_"))
    dp.callback_query.register(task_list_handler.handle_task_page_navigation, F.data.startswith("task_page_"))
    dp.callback_query.register(task_list_handler.handle_task_list_menu, F.data == "task_list")
    dp.callback_query.register(new_task_handler.start_collecting_task, F.data == "new_task")
    
    # В конце регистрируем самый общий обработчик
    dp.message.register(new_task_handler.route_message)

    scheduler.start_scheduler()
    await dp.start_polling(bot)


if __name__ == "__main__":
    create_tables()
    add_comment_column()
    clear_pending_tasks()
    asyncio.run(main())