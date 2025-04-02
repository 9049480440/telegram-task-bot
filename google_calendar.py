def create_event(task):
    """
    Создаёт событие в Google Календаре:
    Название: task.title,
    Дата и время: используется deadline и время (например, 10:00-11:00 или указанное время из задачи).
    Возвращает event_id, который будет сохранён в SQLite.
    """
    # Заготовка для создания события через Google Calendar API
    event_id = "generated_event_id"
    return event_id

def update_event(task):
    """
    Обновляет событие в календаре при продлении задачи.
    """
    # Логика обновления события
    pass

def delete_event(event_id):
    """
    Удаляет событие из календаря при выполнении задачи.
    """
    # Логика удаления события
    pass
