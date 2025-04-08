from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Создаем постоянную клавиатуру с кнопками
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Новая задача")]
    ],
    resize_keyboard=True,  # Уменьшает размер кнопок
    persistent=True        # Клавиатура остается всегда
)

async def handle_start(message: types.Message):
    """
    Обработка команды /start
    Показывает приветственное сообщение и выводит клавиатуру
    """
    await message.answer(
        "👋 Привет! Я помогу тебе управлять задачами.\n\n"
        "📝 Что я умею:\n"
        "• Добавлять новые задачи\n"
        "• Отслеживать сроки выполнения\n"
        "• Отмечать задачи выполненными\n"
        "• Записывать трудозатраты\n\n"
        "Используй кнопки внизу для быстрого доступа!",
        reply_markup=main_keyboard
    )