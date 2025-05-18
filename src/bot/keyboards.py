from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton
from typing import List, Dict, Any
from datetime import datetime, timedelta


def language_keyboard():
    """Create keyboard for language selection"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:UKR"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:ENG"),
        InlineKeyboardButton(text="🇵🇹 Português", callback_data="lang:POR"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:RUS")
    )
    builder.adjust(2)
    return builder.as_markup()


def section_keyboard(sections_data, lang):
    """Create keyboard for section selection"""
    builder = InlineKeyboardBuilder()
    
    # Проверяем формат данных
    # Если это ответ API, извлекаем секции из поля data
    if isinstance(sections_data, dict) and 'data' in sections_data:
        sections = sections_data['data']
    else:
        sections = sections_data
    
    # Если sections пустой или не является списком, возвращаем только кнопку "Назад"
    if not sections or not isinstance(sections, list):
        # Add back button with appropriate text based on language
        back_text = {
            "UKR": "⬅️ Назад",
            "ENG": "⬅️ Back",
            "POR": "⬅️ Voltar",
            "RUS": "⬅️ Назад"
        }.get(lang, "⬅️ Back")
        
        builder.add(InlineKeyboardButton(
            text=back_text,
            callback_data="back:language"
        ))
        return builder.as_markup()
    
    for section in sections:
        # Получаем имя секции в зависимости от формата данных
        if isinstance(section, dict):
            # Если есть поле name_{lang}, используем его
            section_name = section.get(f"name_{lang}") or section.get("name") or section.get("name_ru", f"Раздел {section.get('id', '?')}")
            section_id = section.get('id')
        else:
            # Если section не словарь, пропускаем его
            continue
        
        if section_id is not None:
            builder.add(InlineKeyboardButton(
                text=section_name,
                callback_data=f"section:{section_id}"
            ))
    
    # Add back button with appropriate text based on language
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.add(InlineKeyboardButton(
        text=back_text,
        callback_data="back:language"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def procedure_keyboard(procedures_data, selected_procedures: List[int], lang: str):
    """Create keyboard for procedure selection with checkboxes"""
    builder = InlineKeyboardBuilder()
    
    # Проверяем формат данных
    # Если это ответ API, извлекаем процедуры из поля data
    if isinstance(procedures_data, dict) and 'data' in procedures_data:
        procedures = procedures_data['data']
    else:
        procedures = procedures_data
    
    # Если procedures пустой или не является списком, возвращаем только кнопки навигации
    if not procedures or not isinstance(procedures, list):
        # Добавляем кнопки навигации ниже
        pass
    else:
        for procedure in procedures:
            if not isinstance(procedure, dict):
                continue
                
            # Получаем ID процедуры
            procedure_id = procedure.get('id')
            if procedure_id is None:
                continue
                
            # Получаем имя процедуры в зависимости от языка
            procedure_name = procedure.get(f"name_{lang}") or procedure.get("name") or procedure.get("name_ru", f"Процедура {procedure_id}")
            
            # Получаем цену процедуры
            base_price = procedure.get('base_price', 0)
            
            # Add checkbox if procedure is selected
            prefix = "✅ " if procedure_id in selected_procedures else ""
            builder.add(InlineKeyboardButton(
                text=f"{prefix}{procedure_name} ({base_price}₴)",
                callback_data=f"procedure:{procedure_id}"
            ))
    
    # Add next and back buttons with appropriate text based on language
    next_text = {
        "UKR": "➡️ Далі",
        "ENG": "➡️ Next",
        "POR": "➡️ Próximo",
        "RUS": "➡️ Далее"
    }.get(lang, "➡️ Next")
    
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.row(
        InlineKeyboardButton(text=back_text, callback_data="back:section"),
        InlineKeyboardButton(text=next_text, callback_data="next:master_or_time")
    )
    
    builder.adjust(1)
    return builder.as_markup()


def master_or_time_keyboard(lang: str):
    """Create keyboard for choosing between master or time selection"""
    builder = InlineKeyboardBuilder()
    
    # Texts based on language
    master_text = {
        "UKR": "👩‍💼 Вибрати майстра",
        "ENG": "👩‍💼 Choose master",
        "POR": "👩‍💼 Escolher mestre",
        "RUS": "👩‍💼 Выбрать мастера"
    }.get(lang, "👩‍💼 Choose master")
    
    time_text = {
        "UKR": "🕒 Вибрати час",
        "ENG": "🕒 Choose time",
        "POR": "🕒 Escolher tempo",
        "RUS": "🕒 Выбрать время"
    }.get(lang, "🕒 Choose time")
    
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.add(
        InlineKeyboardButton(text=master_text, callback_data="select:master"),
        InlineKeyboardButton(text=time_text, callback_data="select:time"),
        InlineKeyboardButton(text=back_text, callback_data="back:procedures")
    )
    
    builder.adjust(1)
    return builder.as_markup()


def master_selection_keyboard(masters_data, lang: str):
    """Create keyboard for master selection"""
    builder = InlineKeyboardBuilder()
    
    # Проверяем формат данных
    if isinstance(masters_data, dict) and 'data' in masters_data:
        masters = masters_data['data']
    else:
        masters = masters_data
    
    # Если masters пустой или не является списком, возвращаем только кнопку "Назад"
    if not masters or not isinstance(masters, list):
        # Добавляем кнопку "Назад"
        back_text = {
            "UKR": "⬅️ Назад",
            "ENG": "⬅️ Back",
            "POR": "⬅️ Voltar",
            "RUS": "⬅️ Назад"
        }.get(lang, "⬅️ Back")
        
        builder.add(InlineKeyboardButton(
            text=back_text,
            callback_data="back:master_or_time"
        ))
        return builder.as_markup()
    
    for master in masters:
        if not isinstance(master, dict):
            continue
            
        # Получаем ID мастера
        master_id = master.get('id')
        if master_id is None:
            continue
            
        # Получаем имя мастера в зависимости от языка
        master_name = master.get(f"name_{lang}") or master.get("name") or master.get("name_ru", f"Мастер {master_id}")
        
        builder.add(InlineKeyboardButton(
            text=master_name,
            callback_data=f"master:{master_id}"
        ))
    
    # Add back button with appropriate text based on language
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.add(InlineKeyboardButton(
        text=back_text,
        callback_data="back:master_or_time"
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def time_selection_keyboard(slots: List[datetime], page: int, items_per_page: int, lang: str):
    """Create keyboard for time selection"""
    builder = InlineKeyboardBuilder()
    
    # Calculate start and end indices for the current page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(slots))
    
    # Add time buttons
    for slot in slots[start_idx:end_idx]:
        time_str = slot.strftime("%H:%M")
        builder.add(InlineKeyboardButton(
            text=time_str,
            callback_data=f"time:{slot.isoformat()}"
        ))
    
    # Add navigation buttons if needed
    if page > 0:
        prev_text = {
            "UKR": "⬅️ Попередня сторінка",
            "ENG": "⬅️ Previous page",
            "POR": "⬅️ Página anterior",
            "RUS": "⬅️ Предыдущая страница"
        }.get(lang, "⬅️ Previous page")
        
        builder.add(InlineKeyboardButton(
            text=prev_text,
            callback_data=f"page:{page-1}"
        ))
    
    if end_idx < len(slots):
        next_text = {
            "UKR": "Наступна сторінка ➡️",
            "ENG": "Next page ➡️",
            "POR": "Próxima página ➡️",
            "RUS": "Следующая страница ➡️"
        }.get(lang, "Next page ➡️")
        
        builder.add(InlineKeyboardButton(
            text=next_text,
            callback_data=f"page:{page+1}"
        ))
    
    # Add back button with appropriate text based on language
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.add(InlineKeyboardButton(
        text=back_text,
        callback_data="back:day"
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def day_selection_keyboard(days: List[datetime], page: int, lang: str, has_more: bool = False):
    """Create keyboard for day selection"""
    builder = InlineKeyboardBuilder()
    
    # Add day buttons
    for day in days:
        # Format day based on language
        if lang in ["UKR", "RUS"]:
            # Формат для украинского и русского
            day_names = {
                0: "Пн",
                1: "Вт",
                2: "Ср",
                3: "Чт",
                4: "Пт",
                5: "Сб",
                6: "Вс"
            }
            day_str = f"{day_names[day.weekday()]}, {day.day:02d}.{day.month:02d}"
        else:
            # Формат для английского и португальского
            day_names = {
                0: "Mon",
                1: "Tue",
                2: "Wed",
                3: "Thu",
                4: "Fri",
                5: "Sat",
                6: "Sun"
            }
            day_str = f"{day_names[day.weekday()]}, {day.day:02d}/{day.month:02d}"
        
        builder.add(InlineKeyboardButton(
            text=day_str,
            callback_data=f"day:{day.isoformat()}"
        ))
    
    # Add "Later" button if there are more days
    if has_more:
        later_text = {
            "UKR": "Пізніше ➡️",
            "ENG": "Later ➡️",
            "POR": "Mais tarde ➡️",
            "RUS": "Позже ➡️"
        }.get(lang, "Later ➡️")
        
        builder.add(InlineKeyboardButton(
            text=later_text,
            callback_data=f"later:{page+1}"
        ))
    
    # Add back button with appropriate text based on language
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.add(InlineKeyboardButton(
        text=back_text,
        callback_data="back:master"
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def confirmation_keyboard(lang: str):
    """Create keyboard for appointment confirmation"""
    builder = InlineKeyboardBuilder()
    
    # Texts based on language
    confirm_text = {
        "UKR": "✅ Підтвердити",
        "ENG": "✅ Confirm",
        "POR": "✅ Confirmar",
        "RUS": "✅ Подтвердить"
    }.get(lang, "✅ Confirm")
    
    cancel_text = {
        "UKR": "❌ Скасувати",
        "ENG": "❌ Cancel",
        "POR": "❌ Cancelar",
        "RUS": "❌ Отменить"
    }.get(lang, "❌ Cancel")
    
    builder.add(
        InlineKeyboardButton(text=confirm_text, callback_data="confirm:yes"),
        InlineKeyboardButton(text=cancel_text, callback_data="confirm:no")
    )
    
    return builder.as_markup()


def my_appointments_keyboard(appointments: List[Dict[str, Any]], lang: str):
    """Create keyboard for viewing appointments"""
    builder = InlineKeyboardBuilder()
    
    for i, appointment in enumerate(appointments):
        # Format date and time based on language
        start_time = appointment["start_time"]
        if lang == "UKR":
            date_str = start_time.strftime("%d.%m.%Y %H:%M")
        elif lang == "ENG":
            date_str = start_time.strftime("%m/%d/%Y %I:%M %p")
        else:
            date_str = start_time.strftime("%d.%m.%Y %H:%M")
            
        builder.add(InlineKeyboardButton(
            text=f"{i+1}. {date_str}",
            callback_data=f"appointment:{appointment['id']}"
        ))
    
    # Add back to main menu button
    main_menu_text = {
        "UKR": "🏠 Головне меню",
        "ENG": "🏠 Main Menu",
        "POR": "🏠 Menu Principal",
        "RUS": "🏠 Главное меню"
    }.get(lang, "🏠 Main Menu")
    
    builder.add(InlineKeyboardButton(
        text=main_menu_text,
        callback_data="back:main_menu"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def appointment_details_keyboard(appointment_id: int, lang: str):
    """Create keyboard for appointment details"""
    builder = InlineKeyboardBuilder()
    
    # Cancel appointment button
    cancel_text = {
        "UKR": "❌ Скасувати запис",
        "ENG": "❌ Cancel Appointment",
        "POR": "❌ Cancelar Agendamento",
        "RUS": "❌ Отменить запись"
    }.get(lang, "❌ Cancel Appointment")
    
    # Back button
    back_text = {
        "UKR": "⬅️ Назад",
        "ENG": "⬅️ Back",
        "POR": "⬅️ Voltar",
        "RUS": "⬅️ Назад"
    }.get(lang, "⬅️ Back")
    
    builder.add(
        InlineKeyboardButton(text=cancel_text, callback_data=f"cancel:{appointment_id}"),
        InlineKeyboardButton(text=back_text, callback_data="back:my_appointments")
    )
    
    builder.adjust(1)
    return builder.as_markup()


def cancel_confirmation_keyboard(appointment_id: int, lang: str):
    """Create keyboard for confirming appointment cancellation"""
    builder = InlineKeyboardBuilder()
    
    # Texts based on language
    yes_text = {
        "UKR": "✅ Так, скасувати",
        "ENG": "✅ Yes, cancel",
        "POR": "✅ Sim, cancelar",
        "RUS": "✅ Да, отменить"
    }.get(lang, "✅ Yes, cancel")
    
    no_text = {
        "UKR": "❌ Ні, залишити",
        "ENG": "❌ No, keep it",
        "POR": "❌ Não, manter",
        "RUS": "❌ Нет, оставить"
    }.get(lang, "❌ No, keep it")
    
    builder.add(
        InlineKeyboardButton(text=yes_text, callback_data=f"cancel_confirm:yes:{appointment_id}"),
        InlineKeyboardButton(text=no_text, callback_data=f"cancel_confirm:no:{appointment_id}")
    )
    
    return builder.as_markup()


# Admin keyboards
def admin_main_keyboard():
    """Create keyboard for admin main menu"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="🏢 Управління робочими місцями", callback_data="admin:workplaces"),
        InlineKeyboardButton(text="📅 Управління робочим часом", callback_data="admin:workslots"),
        InlineKeyboardButton(text="📝 Управління записами", callback_data="admin:appointments"),
        InlineKeyboardButton(text="➕ Створити запис вручну", callback_data="admin:create_appointment")
    )
    
    builder.adjust(1)
    return builder.as_markup()


def admin_workplace_keyboard(workplaces: List[Dict[str, Any]]):
    """Create keyboard for workplace management"""
    builder = InlineKeyboardBuilder()
    
    # Add button to create new workplace
    builder.add(InlineKeyboardButton(
        text="➕ Створити нове робоче місце",
        callback_data="workplace:create"
    ))
    
    # Add buttons for existing workplaces
    for workplace in workplaces:
        builder.add(InlineKeyboardButton(
            text=f"🏢 {workplace['name']}",
            callback_data=f"workplace:{workplace['id']}"
        ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back:admin_main"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def admin_workplace_actions_keyboard(workplace_id: int):
    """Create keyboard for workplace actions"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"workplace_edit:{workplace_id}"),
        InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"workplace_delete:{workplace_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back:workplaces")
    )
    
    builder.adjust(2)
    return builder.as_markup()


def admin_master_selection_keyboard(masters: List[Dict[str, Any]]):
    """Create keyboard for admin to select a master"""
    builder = InlineKeyboardBuilder()
    
    for master in masters:
        builder.add(InlineKeyboardButton(
            text=master["name"],
            callback_data=f"admin_master:{master['id']}"
        ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back:admin_main"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def admin_date_selection_keyboard(days: int = 7):
    """Create keyboard for date selection"""
    builder = InlineKeyboardBuilder()
    
    today = datetime.now()
    
    for i in range(days):
        date = today + timedelta(days=i)
        # Format: "Mon, 01.01" for weekday and date
        date_str = date.strftime("%a, %d.%m")
        builder.add(InlineKeyboardButton(
            text=date_str,
            callback_data=f"date:{date.strftime('%Y-%m-%d')}"
        ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back:admin_main"
    ))
    
    builder.adjust(2)
    return builder.as_markup()


def admin_time_selection_keyboard(start_hour: int = 9, end_hour: int = 20):
    """Create keyboard for time selection"""
    builder = InlineKeyboardBuilder()
    
    for hour in range(start_hour, end_hour + 1):
        builder.add(InlineKeyboardButton(
            text=f"{hour:02d}:00",
            callback_data=f"time:{hour:02d}:00"
        ))
        
        if hour < end_hour:  # Don't add 30 minutes for the last hour
            builder.add(InlineKeyboardButton(
                text=f"{hour:02d}:30",
                callback_data=f"time:{hour:02d}:30"
            ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back:date_selection"
    ))
    
    builder.adjust(2)
    return builder.as_markup()


def admin_appointments_keyboard(appointments: List[Dict[str, Any]], page: int = 0, page_size: int = 5):
    """Create keyboard for viewing appointments with pagination"""
    builder = InlineKeyboardBuilder()
    
    # Calculate total pages
    total_pages = (len(appointments) + page_size - 1) // page_size
    
    # Get appointments for current page
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(appointments))
    page_appointments = appointments[start_idx:end_idx]
    
    for appointment in page_appointments:
        # Format date and time
        start_time = appointment["start_time"]
        date_str = start_time.strftime("%d.%m.%Y %H:%M")
        
        builder.add(InlineKeyboardButton(
            text=f"{date_str} - {appointment['client_name']}",
            callback_data=f"admin_appointment:{appointment['id']}"
        ))
    
    # Navigation buttons
    nav_row = []
    
    # Previous page button
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text="⬅️ Попередні",
            callback_data=f"admin_page:{page-1}"
        ))
    
    # Next page button
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(
            text="➡️ Наступні",
            callback_data=f"admin_page:{page+1}"
        ))
    
    if nav_row:
        builder.row(*nav_row)
    
    # Add back button
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back:admin_main"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def admin_appointment_actions_keyboard(appointment_id: int):
    """Create keyboard for appointment actions"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"admin_delete:{appointment_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back:admin_appointments")
    )
    
    builder.adjust(1)
    return builder.as_markup()


def admin_client_search_keyboard(clients: List[Dict[str, Any]]):
    """Create keyboard for client search results"""
    builder = InlineKeyboardBuilder()
    
    for client in clients:
        builder.add(InlineKeyboardButton(
            text=f"{client['name']} ({client.get('phone', 'No phone')})",
            callback_data=f"client:{client['id']}"
        ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back:admin_main"
    ))
    
    builder.adjust(1)
    return builder.as_markup()
