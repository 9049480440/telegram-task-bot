from aiogram import types

async def handle_start(message: types.Message):
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и краткую инструкцию по использованию бота.
    """
    await message.answer("Привет! Я твой помощник по задачам. Отправь мне текст задачи для начала.")
