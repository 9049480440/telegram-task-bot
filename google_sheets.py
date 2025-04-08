# google_sheets.py

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Авторизация
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)

def add_task_to_sheet(task):
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    tab_name = os.getenv("GOOGLE_SHEET_TAB_NAME", "Катя Бачинина")

    sheet = client.open_by_key(sheet_id).worksheet(tab_name)

    values = [
        task.title or "—",                                # A — Задача
        datetime.now().strftime("%Y-%m-%d"),              # B — Дата постановки
        task.deadline or "—",                             # C — Дата окончания
        "—",                                              # D — Прогресс
        task.assigned_by or "—",                          # E — Кто дал задачу
        f"{task.comment or ''}\n{format_links(task.links)}" if task.links else (task.comment or "—"),  # F — Комментарий и ссылки
        "",                                               # G — Трудозатраты
        task.status,                                      # H — Статус
        task.id,                                          # I — Task ID
        str(task.msg_id or ""),                           # J — Msg ID
    ]

    col_a = sheet.col_values(1)
    row = len(col_a) + 1 if col_a else 2

    sheet.insert_row(values, index=row)
    return row

def format_links(links):
    if not links:
        return ""
    return "\n".join([f"- {link}" for link in links])
