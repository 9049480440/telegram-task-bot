import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import scheduler
import handlers.start as start_handler
import handlers.new_task as new_task_handler
import handlers.task_actions as task_actions_handler
import handlers.task_list as task_list_handler
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация обработчиков
    dp.message.register(start_handler.handle_start, Command("start"))
    dp.message.register(new_task_handler.handle_new_task)
    dp.message.register(task_list_handler.handle_task_list, Command("мои_задачи"))
    dp.callback_query.register(task_actions_handler.handle_task_actions)

    # Запуск планировщика уведомлений
    scheduler.start_scheduler()

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
