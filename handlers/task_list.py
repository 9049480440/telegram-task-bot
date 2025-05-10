from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_active_tasks, get_connection
import math

# Количество задач на одной странице
TASKS_PER_PAGE = 3

async def handle_task_list(message: types.Message, page=0):
    """
    Обработка команды /мои_задачи.
    Выводит список активных задач постранично с кнопками управления.
    """
    # Получаем все активные задачи
    tasks = get_active_tasks()

    if not tasks:
        # Просто выводим сообщение без дополнительных параметров
        await message.answer("У вас нет активных задач.")
        return

    # Сортируем задачи по дате и времени
    # Преобразуем None в "23:59" для сортировки заданий без времени в конец дня
    sorted_tasks = sorted(tasks, key=lambda task: (task[3] or "9999-12-31", task[4] or "23:59"))

    total_pages = math.ceil(len(sorted_tasks) / TASKS_PER_PAGE)
    # Убедимся, что запрошенная страница существует
    page = max(0, min(page, total_pages - 1))

    # Выбираем задачи для текущей страницы
    start_idx = page * TASKS_PER_PAGE
    end_idx = min(start_idx + TASKS_PER_PAGE, len(sorted_tasks))
    current_tasks = sorted_tasks[start_idx:end_idx]

    # Формируем сообщение со списком задач
    response = f"📋 <b>Ваши активные задачи</b> (страница {page+1}/{total_pages}):\n\n"

    # Создаем кнопки для каждой задачи
    keyboard = []

    for i, task in enumerate(current_tasks):
        task_id = task[0]    # id
        title = task[2]      # title
        deadline = task[3]   # deadline
        time = task[4] if task[4] else "—"  # time

        # Форматируем дату для отображения (ДД.ММ)
        try:
            from datetime import datetime
            date_obj = datetime.strptime(deadline, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m")

            # Получаем день недели
            weekdays_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            weekday = weekdays_short[date_obj.weekday()]
        except:
            formatted_date = deadline
            weekday = ""

        # Сокращаем название задачи, если оно слишком длинное
        short_title = (title[:25] + "...") if title and len(title) > 25 else (title or "Без названия")

        # Добавляем информацию о задаче в список
        response += f"<b>{i+1}.</b> {short_title}\n"
        response += f"    📅 {formatted_date} ({weekday}) {time}\n\n"

        # Добавляем кнопку для этой задачи с датой и временем
        button_text = f"📌 {formatted_date} {time} | {short_title[:20]}"
        keyboard.append([
            types.InlineKeyboardButton(text=button_text, callback_data=f"view_task_{task_id}")
        ])

    # Добавляем кнопки навигации, если их больше 1 страницы
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(types.InlineKeyboardButton(text="◀️", callback_data=f"task_page_{page-1}"))

        # Добавляем номер текущей страницы
        nav_row.append(types.InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data=f"none"))

        if page < total_pages - 1:
            nav_row.append(types.InlineKeyboardButton(text="▶️", callback_data=f"task_page_{page+1}"))

        if nav_row:
            keyboard.append(nav_row)

    # Добавляем кнопку создания новой задачи
    keyboard.append([
        types.InlineKeyboardButton(text="➕ Новая задача", callback_data="new_task")
    ])

    # Создаем клавиатуру из кнопок
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(response, reply_markup=markup)

async def handle_view_task(callback: types.CallbackQuery):
    """
    Обработчик для просмотра детальной информации о задаче
    """
    task_id = callback.data.split('_')[-1]

    # Получаем информацию о задаче из базы данных
    from database import get_task_by_id
    task = get_task_by_id(task_id)

    if not task:
        await callback.message.answer("⚠️ Задача не найдена.")
        return

    # Формируем детальную информацию о задаче
    title = task[2]        # title
    deadline = task[3]     # deadline
    time = task[4] if task[4] else "—" # time

    # Форматируем дату для удобного отображения
    formatted_date = deadline
    weekday = ""
    try:
        from datetime import datetime
        date_obj = datetime.strptime(deadline, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")

        # Получаем день недели
        weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday = weekdays_ru[date_obj.weekday()]
    except:
        pass

    # Формируем текст карточки задачи
    task_details = (
        f"📌 <b>{title}</b>\n"
        f"📅 Срок: {formatted_date} ({weekday})\n"
        f"⏰ Время: {time}\n"
    )

    # Добавляем информацию о создании задачи, если она есть
    if task[9]:  # created_at
        try:
            created_at = datetime.fromisoformat(task[9])
            created_date = created_at.strftime("%d.%m.%Y")
            task_details += f"🆕 Создана: {created_date}\n"
        except:
            pass

    # Создаем клавиатуру с действиями для задачи
    keyboard = [
        [
            types.InlineKeyboardButton(text="✅ Выполнено", callback_data=f"mark_done_{task_id}"),
            types.InlineKeyboardButton(text="⏳ Продлить", callback_data=f"extend_deadline_{task_id}")
        ],
        [
            types.InlineKeyboardButton(text="🔙 К списку", callback_data="task_list")
        ]
    ]

    # Создаем клавиатуру из кнопок
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    # Пробуем отредактировать существующее сообщение, если это callback
    try:
        await callback.message.edit_text(task_details, reply_markup=markup, parse_mode="HTML")
        await callback.answer()
    except:
        # Если не получилось отредактировать, отправляем новое сообщение
        await callback.message.answer(task_details, reply_markup=markup)

async def handle_task_page_navigation(callback: types.CallbackQuery):
    """
    Обработчик навигации по страницам списка задач
    """
    page = int(callback.data.split('_')[-1])
    await handle_task_list(callback.message, page=page)

async def handle_task_list_menu(callback: types.CallbackQuery):
    """
    Обработчик для возврата к списку задач
    """
    await handle_task_list(callback.message)