from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import google_calendar
import asyncio
from database import get_tasks_due_in_one_hour, get_active_tasks
from aiogram import Bot
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Планирование ежедневной проверки задач с дедлайном на завтра
    scheduler.add_job(daily_deadline_check, 'cron', hour=9)  # Запуск каждый день в 9:00
    # Планирование проверки задач за час до дедлайна
    scheduler.add_job(hourly_deadline_check, 'interval', minutes=60)
    scheduler.start()

async def daily_deadline_check():
    # Получаем список задач с дедлайном на завтра и отправляем уведомления
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tasks = get_active_tasks(deadline=tomorrow)
    
    for task in tasks:
        user_id = task[1]  # user_id
        task_id = task[0]  # task_id
        title = task[2]    # title
        deadline = task[3] # deadline

        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"mark_done_{task_id}"),
                InlineKeyboardButton(text="⏳ Продлить", callback_data=f"extend_deadline_{task_id}")
            ]
        ])

        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"⚠️ <b>Напоминание!</b>\n"
                    f"Завтра дедлайн задачи:\n"
                    f"📌 <b>{title}</b>\n"
                    f"🗓 {deadline}"
                ),
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")

async def hourly_deadline_check():
    """
    Проверка задач: если до дедлайна остаётся примерно 1-1.5 часа, отправить напоминание пользователю.
    """
    print(f"Выполняю проверку задач с приближающимся дедлайном: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    tasks = get_tasks_due_in_one_hour()
    
    if not tasks:
        print("Не найдено задач с приближающимся дедлайном")
        return
        
    for task in tasks:
        user_id = task[1]  # user_id
        task_id = task[0]  # task_id
        title = task[2]    # title
        deadline = task[3] # deadline date
        time = task[4] or "10:00"  # deadline time (HH:MM)
        
        # Рассчитываем оставшееся время более точно
        deadline_dt = datetime.strptime(f"{deadline} {time}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        time_left = deadline_dt - now
        minutes_left = int(time_left.total_seconds() / 60)
        
        # Выбираем правильное сообщение в зависимости от оставшегося времени
        if minutes_left <= 60:
            time_msg = f"До дедлайна осталось менее часа!"
        else:
            hours = minutes_left // 60
            mins = minutes_left % 60
            time_msg = f"До дедлайна осталось {hours} ч {mins} мин"

        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"mark_done_{task_id}"),
                InlineKeyboardButton(text="⏳ Продлить", callback_data=f"extend_deadline_{task_id}")
            ]
        ])

        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"⏰ <b>Напоминание о задаче!</b>\n"
                    f"{time_msg}\n"
                    f"📌 <b>{title}</b>\n"
                    f"🗓 {deadline} {time}"
                ),
                reply_markup=keyboard
            )
            print(f"Отправлено напоминание пользователю {user_id} о задаче {title}")
        except Exception as e:
            print(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")