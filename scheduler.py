from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_pending_tasks, get_active_tasks, update_task_status
import google_calendar
import asyncio

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Планирование ежедневной проверки задач с дедлайном на завтра
    scheduler.add_job(daily_deadline_check, 'cron', hour=9)  # Пример: запуск каждый день в 9:00
    # Планирование проверки задач за час до дедлайна
    scheduler.add_job(hourly_deadline_check, 'interval', minutes=60)  # Можно настроить более точно
    scheduler.start()

async def daily_deadline_check():
    # Получаем список задач с дедлайном на завтра и отправляем уведомления
    tasks = get_active_tasks(deadline="tomorrow")
    for task in tasks:
        # Отправка уведомления через бота (реализовать отправку)
        print(f"Напоминание: Завтра дедлайн задачи {task.title}")

async def hourly_deadline_check():
    # Проверка: если до дедлайна задачи остается 1 час и задача не выполнена, отправить напоминание
    tasks = get_active_tasks(time_delta=60)  # time_delta в минутах
    for task in tasks:
        # Отправляем уведомление о задаче, которая должна выполниться через час
        print(f"Напоминание: Через час дедлайн задачи {task.title}")
        # Здесь можно добавить кнопки для подтверждения выполнения или продления
