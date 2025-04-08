from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database import add_pending_task, get_pending_task, update_pending_task, delete_pending_task
from gpt_parser import parse_task
from aiogram.fsm.storage.base import StorageKey


def get_collect_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Готово", callback_data="collect_done"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="collect_cancel"),
            InlineKeyboardButton(text="🔁 Сбросить", callback_data="reset_task")
        ]
    ])


async def start_collecting_task(message: Message):
    user_id = message.from_user.id
    task_data = {
        "step": "collecting",
        "messages": [],
        "files": [],
        "forwarded_from": None
    }
    add_pending_task(user_id, task_data)

    await message.answer(
        "📂 Жду сообщения. Перешли фрагменты задачи или напиши текст. Нажми <b>Готово</b>, когда закончишь.",
        reply_markup=get_collect_keyboard()
    )


async def handle_collecting_messages(message: Message):
    user_id = message.from_user.id
    pending = get_pending_task(user_id)
    if not pending:
        return

    messages = pending.get("messages", [])
    files = pending.get("files", [])
    sender = pending.get("forwarded_from")

    if message.text:
        messages.append(message.text)
    elif message.caption:
        messages.append(message.caption)
    else:
        messages.append(None)

    if document := message.document:
        files.append(document.file_name)
    elif photo := message.photo:
        files.append("фотография")

    if not sender:
        if message.forward_from:
            sender = message.forward_from.full_name
        elif message.forward_sender_name:
            sender = message.forward_sender_name

    update_pending_task(user_id, {
        "messages": messages,
        "files": files,
        "forwarded_from": sender,
    })

    await message.answer(
        "✅ Добавлено! Перешли ещё сообщения или нажми «Готово», когда закончишь.",
        reply_markup=get_collect_keyboard()
    )


async def handle_text_reply(message: Message):
    user_id = message.from_user.id
    pending = get_pending_task(user_id)

    if not pending:
        return await message.answer("⚠️ Я не нашёл задачу, которую нужно уточнить. Напиши /задача, чтобы начать заново.")

    step = pending.get("step")

    if step in ["ask_deadline", "edit_deadline"]:
        pending["deadline"] = message.text.strip()
        if step == "ask_deadline":
            pending["step"] = "ask_time"
            update_pending_task(user_id, pending)
            return await message.answer("⏰ Во сколько выполнить задачу?")

    elif step in ["ask_time", "edit_time"]:
        pending["time"] = message.text.strip()

        if step == "ask_time":
            # ✅ Автоматическая подстановка отправителя и подтверждение
            if not pending.get("assigned_by") and pending.get("forwarded_from"):
                pending["assigned_by"] = pending["forwarded_from"]
                pending["step"] = "confirm_assigned_by"
            elif pending.get("assigned_by") and pending["assigned_by"] not in {"", "null", None}:
                pending["step"] = "ask_comment"
            else:
                pending["step"] = "ask_assigned_by"

            update_pending_task(user_id, pending)

            if pending["step"] == "confirm_assigned_by":
                return await message.answer(
                    f"👤 Я определил, что задачу поставил: <b>{pending['assigned_by']}</b>. Это верно?",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Да", callback_data="confirm_assigned_yes"),
                            InlineKeyboardButton(text="❌ Нет", callback_data="confirm_assigned_no")
                        ]
                    ])
                )

            if pending["step"] == "ask_comment":
                return await message.answer("💬 Хочешь оставить комментарий?")
            return await message.answer("👤 Кто поставил задачу?")

    elif step in ["ask_assigned_by", "edit_assigned_by", "edit_assigned"]:
        pending["assigned_by"] = message.text.strip()
        if step == "ask_assigned_by":
            pending["step"] = "ask_comment"
            update_pending_task(user_id, pending)
            return await message.answer("💬 Хочешь оставить комментарий?")

    elif step == "confirm_assigned_by":
        if pending.get("assigned_by") and pending["assigned_by"] not in {"", "null", None}:
            return await message.answer(
                f"👤 Я определил, что задачу поставил: <b>{pending['assigned_by']}</b>. Это верно?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Да", callback_data="confirm_assigned_yes"),
                        InlineKeyboardButton(text="❌ Нет", callback_data="confirm_assigned_no")
                    ]
                ])
            )
        else:
            pending["step"] = "ask_assigned_by"
            update_pending_task(user_id, pending)
            return await message.answer("👤 Кто поставил задачу?")

    elif step in ["ask_comment", "edit_comment"]:
        pending["comment"] = message.text.strip()
        pending["step"] = "confirm"

    elif step == "edit_title":
        pending["title"] = message.text.strip()
        pending["step"] = "confirm"

    else:
        return await message.answer("⚠️ Я немного запутался. Давай начнём заново — напиши /задача.")

    update_pending_task(user_id, pending)

    return await message.answer(
        f"""📌 Задача: {pending.get('title', '–')}
📅 Срок: {pending.get('deadline', '–')}
⏰ Время: {pending.get('time', '–')}
👤 Поставил: {pending.get('assigned_by', '–')}
💬 Комментарий: {pending.get('comment', '–')}

Добавить в таблицу и календарь?""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_add"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel_add")
            ]
        ])
    )




async def route_message(message: Message):
    user_id = message.from_user.id
    pending = get_pending_task(user_id)

    # Проверяем состояние FSM - если у нас есть активное состояние для комментария,
    # то не обрабатываем сообщение как новую задачу
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.memory import MemoryStorage
    from task_actions import TaskStates
    
    # Создаем хранилище состояний и контекст
    storage = MemoryStorage()
    state_context = FSMContext(storage=storage, key=StorageKey(user_id=user_id, chat_id=message.chat.id, bot_id=0))
    
    # Проверяем состояние
    current_state = await state_context.get_state()
    
    # Если мы в состоянии ожидания комментария, не обрабатываем сообщение как новую задачу
    if current_state == TaskStates.waiting_for_comment.state:
        # Позволяем обработчику комментариев обработать это сообщение
        return

    # Регулярный поток обработки сообщений
    if pending and pending.get("step") == "confirm":
        task_data = {
            "step": "collecting",
            "messages": [message.text if message.text else message.caption],
            "files": [],
            "forwarded_from": message.forward_from.full_name if message.forward_from else (
                message.forward_sender_name if message.forward_sender_name else None
            )
        }

        if document := message.document:
            task_data["files"].append(document.file_name)
        elif photo := message.photo:
            task_data["files"].append("фотография")

        add_pending_task(user_id, task_data)

        return await message.answer(
            "🆕️ Начал сбор новой задачи. Перешли ещё сообщения или нажми «Готово».",
            reply_markup=get_collect_keyboard()
        )

    if pending and pending.get("step") == "collecting":
        return await handle_collecting_messages(message)

    if pending and pending.get("step") in {
        "ask_deadline", "ask_time", "ask_assigned_by", "ask_comment",
        "confirm_assigned_by", "edit_title", "edit_deadline", "edit_time",
        "edit_assigned_by", "edit_comment", "edit_assigned"
    }:
        return await handle_text_reply(message)

    # Если дошли до этой точки, значит, это новая задача или сообщение без контекста
    task_data = {
        "step": "collecting",
        "messages": [message.text if message.text else message.caption],
        "files": [],
        "forwarded_from": message.forward_from.full_name if message.forward_from else (
            message.forward_sender_name if message.forward_sender_name else None
        )
    }

    if document := message.document:
        task_data["files"].append(document.file_name)
    elif photo := message.photo:
        task_data["files"].append("фотография")

    add_pending_task(user_id, task_data)

    await message.answer(
        "📂 Начал сбор новой задачи. Перешли ещё сообщения или нажми «Готово».",
        reply_markup=get_collect_keyboard()
    )




async def handle_reset_task(callback: CallbackQuery):
    user_id = callback.from_user.id
    delete_pending_task(user_id)
    await callback.message.answer("🔁 Задача сброшена. Можешь начать заново — напиши /задача.")


async def handle_confirm_assigned_yes(callback: CallbackQuery):
    user_id = callback.from_user.id
    pending = get_pending_task(user_id)
    if not pending:
        return await callback.message.answer("⚠️ Не удалось подтвердить имя.")
    update_pending_task(user_id, {"step": "ask_comment"})
    await callback.message.answer("💬 Хочешь оставить комментарий?")


async def handle_confirm_assigned_no(callback: CallbackQuery):
    user_id = callback.from_user.id
    update_pending_task(user_id, {
        "assigned_by": None,
        "step": "ask_assigned_by"
    })
    await callback.message.answer("👤 Кто тогда поставил задачу?")
