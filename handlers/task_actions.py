from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_pending_task, delete_pending_task, update_pending_task, add_task
from database import complete_task, update_task_deadline, add_completion_comment
from gpt_parser import parse_task
import re
import uuid
from datetime import datetime
from google_sheets import add_task_to_sheet
from google_calendar import add_task_to_calendar, update_event, delete_event
from models.task_model import Task
import sqlite3

# Добавьте этот класс для работы с состояниями
class TaskStates(StatesGroup):
    waiting_for_hours = State()
    waiting_for_comment = State()  # Новое состояние для комментария
    waiting_for_new_deadline = State()
    waiting_for_new_time = State()


def extract_links(text):
    url_pattern = r'https?://\S+'
    return re.findall(url_pattern, text)


def get_confirmation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_add"),
         InlineKeyboardButton(text="❌ Нет", callback_data="cancel_add")]
    ])


def get_confirm_edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm_add"),
            InlineKeyboardButton(text="📝 Исправить", callback_data="edit_fields"),
            InlineKeyboardButton(text="✅ Отметить как выполнено", callback_data="mark_done")
        ]
    ])


def get_edit_field_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Задача", callback_data="edit_title"),
         InlineKeyboardButton(text="📅 Срок", callback_data="edit_deadline")],
        [InlineKeyboardButton(text="⏰ Время", callback_data="edit_time"),
         InlineKeyboardButton(text="👤 Кто дал", callback_data="edit_assigned")],
        [InlineKeyboardButton(text="💬 Комментарий", callback_data="edit_comment")]
    ])


def format_task_card(pending):
    files = pending.get("files", [])
    messages = pending.get("messages", [])
    comment = pending.get("comment") or "—"

    full_text = "\n".join(messages)
    links = extract_links(full_text)

    files_text = "\n".join(f"📎 {f}" for f in files) if files else "—"
    links_text = "\n".join(f"🔗 {l}" for l in links) if links else "—"

    comment_block = comment
    if files or links:
        comment_block += "\n📂 Вложения:"
        if files:
            comment_block += f"\n{files_text}"
        if links:
            comment_block += f"\n{links_text}"

    return (
        f"📌 Задача: {pending.get('title', '—') or '—'}\n"
        f"📅 Срок: {pending.get('deadline', '—') or '—'}\n"
        f"⏰ Время: {pending.get('time', '—') or '—'}\n"
        f"👤 Поставил: {pending.get('assigned_by', '—') or '—'}\n"
        f"💬 Комментарий: {comment_block}"
    )


async def handle_show_final(callback_or_message, user_id=None):
    if not user_id:
        user_id = callback_or_message.from_user.id
    pending = get_pending_task(user_id)
    if not pending:
        return await callback_or_message.answer("⚠️ Не найдено активной задачи.")

    text = format_task_card(pending) + "\n\nДобавить в таблицу или отметить как выполненное?"
    await callback_or_message.answer(text, reply_markup=get_confirm_edit_keyboard())


async def handle_edit_fields(callback: CallbackQuery):
    await callback.message.answer("✏️ Что хочешь изменить?", reply_markup=get_edit_field_keyboard())


async def handle_edit_field_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    field_map = {
        "edit_title": ("title", "📝 Как звучит задача?"),
        "edit_deadline": ("deadline", "📅 До какого числа?"),
        "edit_time": ("time", "⏰ Во сколько?"),
        "edit_assigned": ("assigned_by", "👤 Кто поставил задачу?"),
        "edit_comment": ("comment", "💬 Новый комментарий?")
    }
    field, prompt = field_map[callback.data]
    update_pending_task(user_id, {"step": f"edit_{field}"})
    await callback.message.answer(prompt)


# Модифицированная функция handle_collect_done, улучшенная обработка файлов
async def handle_collect_done(callback: CallbackQuery):
    user_id = callback.from_user.id
    pending = get_pending_task(user_id)
    sender_name = pending.get("forwarded_from", None)

    if not pending:
        return await callback.message.answer("⚠️ Нет активной задачи. Напиши текст задачи.")

    messages = pending.get("messages", [])
    files = pending.get("files", [])

    safe_messages = [m for m in messages if isinstance(m, str)]
    combined_text = "\n".join(safe_messages)

    # Добавляем информацию о файлах в text перед отправкой в GPT
    task_data = parse_task(combined_text, files=files, sender_name=sender_name)

    # Обрабатываем случай, когда у нас есть файлы, но GPT не добавил их в комментарий
    if files and (not task_data.get("comment") or "файл" not in task_data.get("comment", "").lower()):
        # Если комментария нет или в нем нет упоминания файлов
        files_text = "\n".join(f"📎 {f}" for f in files)
        
        if task_data.get("comment"):
            task_data["comment"] += f"\n\n📂 Вложения:\n{files_text}"
        else:
            task_data["comment"] = f"📂 Вложения:\n{files_text}"

    update_fields = {
        "title": task_data.get("task_title"),
        "deadline": task_data.get("deadline"),
        "time": task_data.get("task_time"),
        "assigned_by": task_data.get("task_giver"),
        "comment": task_data.get("comment"),
        "files": files,  # Убедимся, что files всегда сохраняются в pending_task
    }

    update_pending_task(user_id, update_fields)

    print("[DEBUG] assigned_by из GPT =", update_fields["assigned_by"])
    print("[DEBUG] forwarded_from из pending =", sender_name)
    print("[DEBUG] files =", files)

    if not update_fields["deadline"]:
        update_pending_task(user_id, {**update_fields, "step": "ask_deadline"})
        return await callback.message.answer("📅 До какого числа нужно сделать задачу?")

    if not update_fields["time"]:
        update_pending_task(user_id, {**update_fields, "step": "ask_time"})
        return await callback.message.answer("⏰ Во сколько выполнить задачу?")

    if not update_fields["assigned_by"] or update_fields["assigned_by"] in {"", "null", None}:
        if sender_name:
            update_pending_task(user_id, {**update_fields, "step": "forwarded_confirm"})
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="forwarded_yes"),
                 InlineKeyboardButton(text="❌ Нет", callback_data="forwarded_no")]
            ])
            return await callback.message.answer(
                f"👤 Вижу, что сообщение переслано от <b>{sender_name}</b>. Записать его как поставившего задачу?",
                reply_markup=keyboard
            )
        else:
            update_pending_task(user_id, {**update_fields, "step": "ask_assigned_by"})
            return await callback.message.answer("👤 Кто поставил задачу?")
    else:
        update_pending_task(user_id, {**update_fields, "step": "confirm_assigned_by"})
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_assigned_yes"),
             InlineKeyboardButton(text="❌ Нет", callback_data="confirm_assigned_no")]
        ])
        return await callback.message.answer(
            f"👤 Я определил, что задачу поставил: <b>{update_fields['assigned_by']}</b>. Это верно?",
            reply_markup=keyboard
        )


async def handle_confirm_add(callback: CallbackQuery):
    user_id = callback.from_user.id
    pending = get_pending_task(user_id)

    if not pending or pending.get("step") != "confirm":
        return await callback.message.answer("⚠️ Не могу подтвердить задачу. Попробуй ещё раз.")

    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    task_obj = Task(
        id=task_id,
        user_id=user_id,
        title=pending["title"],
        deadline=pending["deadline"],
        time=pending["time"],
        calendar_event_id=None,
        sheet_row=None,
        status="active",
        msg_id=callback.message.message_id,
        created_at=now,
        completed_at=None,
        hours_spent=0.0,
        assigned_by=pending.get("assigned_by"),
        comment=pending.get("comment"),
        links=[]
    )

    sheet_row = add_task_to_sheet(task_obj)
    task_obj.sheet_row = sheet_row

    calendar_event_id = add_task_to_calendar(
        title=task_obj.title,
        date=task_obj.deadline,
        time=task_obj.time
    )
    task_obj.calendar_event_id = calendar_event_id

    add_task(task_obj.__dict__)
    delete_pending_task(user_id)

    await callback.message.answer("✅ Задача добавлена в таблицу и календарь!")


async def handle_collect_cancel(callback: CallbackQuery):
    user_id = callback.from_user.id
    delete_pending_task(user_id)
    await callback.message.answer("❌ Задача отменена.")


async def handle_forwarded_yes(callback: CallbackQuery):
    user_id = callback.from_user.id
    pending = get_pending_task(user_id)

    if not pending or not pending.get("forwarded_from"):
        return await callback.message.answer("⚠️ Нет информации о пересланном сообщении.")

    update_pending_task(user_id, {
        "assigned_by": pending["forwarded_from"],
        "step": "ask_comment"
    })
    return await callback.message.answer("💬 Хочешь оставить комментарий?")


async def handle_forwarded_no(callback: CallbackQuery):
    user_id = callback.from_user.id

    update_pending_task(user_id, {
        "step": "ask_assigned_by"
    })
    return await callback.message.answer("👤 Кто поставил задачу?")


async def handle_confirm_assigned_yes(callback: CallbackQuery):
    user_id = callback.from_user.id
    update_pending_task(user_id, {"step": "ask_comment"})
    await handle_show_final(callback)


async def handle_confirm_assigned_no(callback: CallbackQuery):
    user_id = callback.from_user.id
    update_pending_task(user_id, {
        "assigned_by": None,
        "step": "ask_assigned_by"
    })
    await callback.message.answer("👤 Кто тогда поставил задачу?")



# Функция для получения задачи по ID
def get_task_by_id(task_id):
    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    return row

# Обработчик для кнопки "Выполнено"
async def handle_mark_done(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split('_')[-1]
    task = get_task_by_id(task_id)
    
    if not task:
        await callback.message.answer("⚠️ Задача не найдена.")
        return
    
    await state.update_data(task_id=task_id)
    await state.set_state(TaskStates.waiting_for_hours)
    await callback.message.answer("⏱️ Сколько часов вы потратили на выполнение этой задачи? (введите число, например, 2.5)")

# Обработчик для ввода трудозатрат
# Обновленная функция для файла task_actions.py

# Обновленная функция handle_hours_input с дополнительной проверкой состояния
async def handle_hours_input(message: Message, state: FSMContext):
    # Проверяем, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != TaskStates.waiting_for_hours.state:
        return
        
    try:
        hours = float(message.text.replace(',', '.'))
        if hours < 0:
            raise ValueError("Отрицательное значение")
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите корректное число часов.")
        return
    
    # Сохраняем трудозатраты в состоянии
    await state.update_data(hours_spent=hours)
    
    # Спрашиваем о комментарии
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="add_comment_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="add_comment_no")
        ]
    ])
    
    await message.answer("💬 Хотите добавить комментарий или ссылку на отчет?", reply_markup=keyboard)

# Обновленные обработчики для кнопок выбора добавления комментария
async def handle_add_comment_yes(callback: CallbackQuery, state: FSMContext):
    # Очень важно: меняем состояние ДО отправки сообщения
    await state.set_state(TaskStates.waiting_for_comment)
    await callback.message.answer("💬 Введите комментарий или ссылку на отчет:")
    await callback.answer()

async def handle_add_comment_no(callback: CallbackQuery, state: FSMContext):
    # Завершаем задачу без комментария
    await complete_task_with_data(callback.message, state, None)
    await callback.answer()
    
# Исправленный обработчик для ввода комментария
async def handle_comment_input(message: Message, state: FSMContext):
    # Явно проверяем, что мы находимся в правильном состоянии
    current_state = await state.get_state()
    if current_state == TaskStates.waiting_for_comment.state:
        comment = message.text
        # Завершаем задачу с комментарием
        await complete_task_with_data(message, state, comment)
    else:
        # Если мы не в состоянии ожидания комментария, ничего не делаем
        pass

# Добавить новую функцию для завершения задачи с комментарием
async def complete_task_with_data(message: Message, state: FSMContext, comment=None):
    data = await state.get_data()
    task_id = data.get("task_id")
    hours = data.get("hours_spent")
    
    task = get_task_by_id(task_id)
    if not task:
        await message.answer("⚠️ Задача не найдена.")
        await state.clear()
        return
    
    # Обновляем статус задачи в базе данных
    completion_time = complete_task(task_id, hours)
    
    # Если есть комментарий, сохраняем его
    if comment:
        add_completion_comment(task_id, comment)
    
    # Обновляем статус в Google Sheets
    update_task_in_sheet(task[6], "done", hours, comment)  # task[6] - sheet_row
    
    # Удаляем событие из календаря
    calendar_event_id = task[5]  # task[5] - calendar_event_id
    if calendar_event_id and calendar_event_id != "None" and calendar_event_id != "generated_event_id":
        delete_event(calendar_event_id)
    
    # Форматируем дату для вывода пользователю
    from datetime import datetime
    completion_date = datetime.fromisoformat(completion_time).strftime("%d.%m.%Y")
    
    # Формируем сообщение с результатом
    completion_message = (
        f"✅ Задача \"{task[2]}\" отмечена как выполненная!\n"
        f"⏱️ Трудозатраты: {hours} ч.\n"
        f"📅 Дата выполнения: {completion_date}"
    )
    
    if comment:
        completion_message += f"\n💬 Комментарий: {comment}"
    
    await message.answer(completion_message)
    await state.clear()

# Обработчик для кнопки "Продлить"
async def handle_extend_deadline(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split('_')[-1]
    task = get_task_by_id(task_id)
    
    if not task:
        await callback.message.answer("⚠️ Задача не найдена.")
        return
    
    await state.update_data(task_id=task_id)
    await state.set_state(TaskStates.waiting_for_new_deadline)
    await callback.message.answer("📅 Введите новый срок в формате ДД.ММ.ГГ или ГГГГ-ММ-ДД")

# Обработчик для ввода нового срока
async def handle_new_deadline_input(message: Message, state: FSMContext):
    from google_calendar import normalize_date
    
    try:
        new_deadline = normalize_date(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ Некорректный формат даты: {str(e)}")
        return
    
    await state.update_data(new_deadline=new_deadline)
    await state.set_state(TaskStates.waiting_for_new_time)
    await message.answer("⏰ Введите новое время в формате ЧЧ:ММ (например, 10:00)")

# Обновленная функция для нормализации времени
def normalize_time(time_str):
    """
    Преобразует время в формат HH:MM
    Поддерживает:
    - 'HH' (например, '10' -> '10:00')
    - 'H' (например, '9' -> '09:00')
    - 'HH:MM' (например, '10:30')
    - 'H:MM' (например, '9:30' -> '09:30')
    """
    import re
    
    # Если строка пустая, вернуть значение по умолчанию
    if not time_str or time_str.strip() == "":
        return "10:00"  # Значение по умолчанию
    
    time_str = time_str.strip()
    
    # Если введено только число (часы)
    if re.match(r"^\d{1,2}$", time_str):
        hours = int(time_str)
        if 0 <= hours <= 23:
            return f"{hours:02d}:00"
        else:
            raise ValueError("Часы должны быть от 0 до 23")
    
    # Если введено время в формате HH:MM или H:MM
    time_pattern = r"^(\d{1,2}):(\d{2})$"
    match = re.match(time_pattern, time_str)
    if match:
        hours, minutes = map(int, match.groups())
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return f"{hours:02d}:{minutes:02d}"
        else:
            raise ValueError("Неверный формат времени")
    
    raise ValueError("Неверный формат времени")

# Обновленный обработчик для ввода нового времени
async def handle_new_time_input(message: Message, state: FSMContext):
    try:
        # Используем новую функцию для нормализации времени
        new_time = normalize_time(message.text)
        
        data = await state.get_data()
        task_id = data.get("task_id")
        new_deadline = data.get("new_deadline")
        
        task = get_task_by_id(task_id)
        if not task:
            await message.answer("⚠️ Задача не найдена.")
            await state.clear()
            return
        
        # Обновляем срок в базе данных
        conn = sqlite3.connect("db.sqlite3")
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET deadline = ?, time = ? WHERE id = ?", 
                      (new_deadline, new_time, task_id))
        conn.commit()
        conn.close()
        
        # Обновляем срок в Google Sheets
        update_deadline_in_sheet(task[6], new_deadline)  # task[6] - sheet_row
        
        # Обновляем событие в календаре
        if task[5]:  # task[5] - calendar_event_id
            task_obj = {
                "calendar_event_id": task[5],
                "deadline": new_deadline,
                "time": new_time
            }
            update_event(task_obj)
        
        await message.answer(f"⏳ Срок задачи \"{task[2]}\" продлен до {new_deadline} {new_time}")
        await state.clear()
        
    except ValueError as e:
        await message.answer(f"⚠️ {str(e)}. Пожалуйста, введите время в одном из форматов: 10 (для 10:00) или 10:30")

# Функция для обновления статуса задачи в Google Sheets
# Обновленная функция для файла task_actions.py

def update_task_in_sheet(row, status, hours=None, comment=None):
    import gspread
    import json
    from oauth2client.service_account import ServiceAccountCredentials
    import os
    from datetime import datetime
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Получаем JSON из переменной окружения
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    # Преобразуем строку в словарь
    creds_dict = json.loads(creds_json)
    
    # Авторизуемся с помощью словаря
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    tab_name = os.getenv("GOOGLE_SHEET_TAB_NAME", "Tasks")
    
    sheet = client.open_by_key(sheet_id).worksheet(tab_name)
    
    # Обновляем статус
    sheet.update_cell(row, 8, status)  # 8 - колонка H (Статус)
    
    # Если задача выполнена, обновляем трудозатраты и прогресс
    if status == "done" and hours is not None:
        # Обновляем трудозатраты
        sheet.update_cell(row, 7, str(hours))  # 7 - колонка G (Трудозатраты)
        
        # Обновляем прогресс - колонка D
        current_date = datetime.now().strftime("%Y-%m-%d")
        progress_text = f"Выполнено {current_date}"
        
        # Если есть комментарий, добавляем его в поле прогресса
        if comment:
            progress_text += f"\nКомментарий: {comment}"
            
            # Обновляем также поле комментария (F - колонка 6)
            sheet.update_cell(row, 6, comment)
            
        sheet.update_cell(row, 4, progress_text)  # 4 - колонка D (Прогресс)

# Функция для обновления срока в Google Sheets
def update_deadline_in_sheet(row, new_deadline):
    import gspread
    import json
    from oauth2client.service_account import ServiceAccountCredentials
    import os
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Получаем JSON из переменной окружения
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    # Преобразуем строку в словарь
    creds_dict = json.loads(creds_json)
    
    # Авторизуемся с помощью словаря
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    tab_name = os.getenv("GOOGLE_SHEET_TAB_NAME", "Tasks")
    
    sheet = client.open_by_key(sheet_id).worksheet(tab_name)
    
    # Обновляем дату окончания
    sheet.update_cell(row, 3, new_deadline)  # 3 - колонка C (Дата окончания)