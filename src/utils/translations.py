from typing import Dict, Any

# Translations for common phrases
TRANSLATIONS = {
    # Welcome message
    "welcome": {
        "UKR": "Вітаємо у боті салону краси! Оберіть мову:",
        "ENG": "Welcome to the beauty salon bot! Choose your language:",
        "POR": "Bem-vindo ao bot do salão de beleza! Escolha seu idioma:",
        "RUS": "Добро пожаловать в бот салона красоты! Выберите язык:"
    },
    
    # Main menu
    "main_menu": {
        "UKR": "Головне меню. Оберіть опцію:",
        "ENG": "Main menu. Choose an option:",
        "POR": "Menu principal. Escolha uma opção:",
        "RUS": "Главное меню. Выберите опцию:"
    },
    
    # Section selection
    "select_section": {
        "UKR": "Оберіть секцію послуг:",
        "ENG": "Choose a service section:",
        "POR": "Escolha uma seção de serviço:",
        "RUS": "Выберите секцию услуг:"
    },
    
    # Procedure selection
    "select_procedures": {
        "UKR": "Оберіть процедури (можна вибрати декілька):",
        "ENG": "Choose procedures (multiple selection allowed):",
        "POR": "Escolha procedimentos (seleção múltipla permitida):",
        "RUS": "Выберите процедуры (можно выбрать несколько):"
    },
    
    # No procedures selected
    "no_procedures_selected": {
        "UKR": "Ви не вибрали жодної процедури. Будь ласка, оберіть хоча б одну процедуру.",
        "ENG": "You haven't selected any procedures. Please choose at least one procedure.",
        "POR": "Você não selecionou nenhum procedimento. Por favor, escolha pelo menos um procedimento.",
        "RUS": "Вы не выбрали ни одной процедуры. Пожалуйста, выберите хотя бы одну процедуру."
    },
    
    # Registration name required
    "registration_name_required": {
        "UKR": "Для продовження нам потрібно зареєструвати вас. Будь ласка, введіть ваше ім'я:",
        "ENG": "To continue, we need to register you. Please enter your name:",
        "POR": "Para continuar, precisamos registrá-lo. Por favor, digite seu nome:",
        "RUS": "Для продолжения нам необходимо зарегистрировать вас. Пожалуйста, введите ваше имя:"
    },
    
    # Master or time selection
    "select_master_or_time": {
        "UKR": "Оберіть, як ви хочете записатись:",
        "ENG": "Choose how you want to book:",
        "POR": "Escolha como deseja agendar:",
        "RUS": "Выберите, как вы хотите записаться:"
    },
    
    # Master selection
    "select_master": {
        "UKR": "Оберіть майстра:",
        "ENG": "Choose a master:",
        "POR": "Escolha um mestre:",
        "RUS": "Выберите мастера:"
    },
    
    # Day selection
    "select_day": {
        "UKR": "Оберіть день для запису:",
        "ENG": "Choose a day for your appointment:",
        "POR": "Escolha um dia para o seu agendamento:",
        "RUS": "Выберите день для записи:"
    },
    
    # No masters available
    "no_masters_available": {
        "UKR": "На жаль, немає доступних майстрів для обраних процедур. Будь ласка, оберіть інші процедури або спробуйте пізніше.",
        "ENG": "Unfortunately, there are no masters available for the selected procedures. Please choose other procedures or try again later.",
        "POR": "Infelizmente, não há mestres disponíveis para os procedimentos selecionados. Por favor, escolha outros procedimentos ou tente novamente mais tarde.",
        "RUS": "К сожалению, нет доступных мастеров для выбранных процедур. Пожалуйста, выберите другие процедуры или попробуйте позже."
    },
    
    # Time selection
    "select_time": {
        "UKR": "Оберіть зручний час для запису:",
        "ENG": "Choose a convenient time for your appointment:",
        "POR": "Escolha um horário conveniente para seu agendamento:",
        "RUS": "Выберите удобное время для записи:"
    },
    
    # No slots available
    "no_slots_available": {
        "UKR": "На жаль, немає доступних слотів для обраного майстра. Будь ласка, оберіть іншого майстра або спробуйте пізніше.",
        "ENG": "Unfortunately, there are no available slots for the selected master. Please choose another master or try again later.",
        "POR": "Infelizmente, não há horários disponíveis para o mestre selecionado. Por favor, escolha outro mestre ou tente novamente mais tarde.",
        "RUS": "К сожалению, нет доступных слотов для выбранного мастера. Пожалуйста, выберите другого мастера или попробуйте позже."
    },
    
    # Appointment confirmation
    "appointment_confirmation": {
        "UKR": "Підтвердіть запис:\n\n{details}\n\nЗагальна вартість: {total_price}₴",
        "ENG": "Confirm your appointment:\n\n{details}\n\nTotal price: {total_price}₴",
        "POR": "Confirme seu agendamento:\n\n{details}\n\nPreço total: {total_price}₴",
        "RUS": "Подтвердите запись:\n\n{details}\n\nОбщая стоимость: {total_price}₴"
    },
    
    # Appointment confirmed
    "appointment_confirmed": {
        "UKR": "✅ Ваш запис підтверджено! Чекаємо на вас {date} о {time}.",
        "ENG": "✅ Your appointment is confirmed! We are waiting for you on {date} at {time}.",
        "POR": "✅ Seu agendamento está confirmado! Estamos esperando por você em {date} às {time}.",
        "RUS": "✅ Ваша запись подтверждена! Ждем вас {date} в {time}."
    },
    
    # Appointment canceled
    "appointment_canceled": {
        "UKR": "❌ Запис скасовано.",
        "ENG": "❌ Appointment canceled.",
        "POR": "❌ Agendamento cancelado.",
        "RUS": "❌ Запись отменена."
    },
    
    # My appointments
    "my_appointments": {
        "UKR": "Ваші активні записи:",
        "ENG": "Your active appointments:",
        "POR": "Seus agendamentos ativos:",
        "RUS": "Ваши активные записи:"
    },
    
    # No appointments
    "no_appointments": {
        "UKR": "У вас немає активних записів.",
        "ENG": "You have no active appointments.",
        "POR": "Você não tem agendamentos ativos.",
        "RUS": "У вас нет активных записей."
    },
    
    # Appointment details
    "appointment_details": {
        "UKR": "Деталі запису:\n\n{details}",
        "ENG": "Appointment details:\n\n{details}",
        "POR": "Detalhes do agendamento:\n\n{details}",
        "RUS": "Детали записи:\n\n{details}"
    },
    
    # Cancel appointment confirmation
    "cancel_appointment_confirmation": {
        "UKR": "Ви впевнені, що хочете скасувати цей запис?",
        "ENG": "Are you sure you want to cancel this appointment?",
        "POR": "Tem certeza de que deseja cancelar este agendamento?",
        "RUS": "Вы уверены, что хотите отменить эту запись?"
    },
    
    # Registration required
    "registration_required": {
        "UKR": "Будь ласка, введіть ваше ім'я для реєстрації:",
        "ENG": "Please enter your name for registration:",
        "POR": "Por favor, insira seu nome para registro:",
        "RUS": "Пожалуйста, введите ваше имя для регистрации:"
    },
    
    # Phone required
    "phone_required": {
        "UKR": "Будь ласка, введіть ваш номер телефону:",
        "ENG": "Please enter your phone number:",
        "POR": "Por favor, insira seu número de telefone:",
        "RUS": "Пожалуйста, введите ваш номер телефона:"
    },
    
    # Registration completed
    "registration_completed": {
        "UKR": "Дякуємо за реєстрацію! Тепер ви можете записатися на процедури.",
        "ENG": "Thank you for registering! Now you can book procedures.",
        "POR": "Obrigado por se registrar! Agora você pode agendar procedimentos.",
        "RUS": "Спасибо за регистрацию! Теперь вы можете записаться на процедуры."
    },
    
    # Admin welcome
    "admin_welcome": {
        "UKR": "Вітаємо в адміністративній панелі! Оберіть опцію:",
        "ENG": "Welcome to the admin panel! Choose an option:",
        "POR": "Bem-vindo ao painel de administração! Escolha uma opção:",
        "RUS": "Добро пожаловать в административную панель! Выберите опцию:"
    },
    
    # Error messages
    "error_occurred": {
        "UKR": "Сталася помилка. Будь ласка, спробуйте пізніше або зверніться до адміністратора.",
        "ENG": "An error occurred. Please try again later or contact the administrator.",
        "POR": "Ocorreu um erro. Por favor, tente novamente mais tarde ou entre em contato com o administrador.",
        "RUS": "Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь к администратору."
    }
}


def get_text(key: str, lang: str = "UKR", **kwargs) -> str:
    """
    Get translated text for the given key and language
    
    Args:
        key: Translation key
        lang: Language code (UKR, ENG, POR, RUS)
        **kwargs: Format parameters for the text
        
    Returns:
        Translated text
    """
    # Default to UKR if language not found
    if lang not in ["UKR", "ENG", "POR", "RUS"]:
        lang = "UKR"
    
    # Get text for the key and language
    text = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("UKR", f"Missing translation: {key}"))
    
    # Format text with provided parameters
    if kwargs:
        text = text.format(**kwargs)
    
    return text


def format_date(date, lang: str = "UKR") -> str:
    """
    Format date according to the language
    
    Args:
        date: Datetime object
        lang: Language code
        
    Returns:
        Formatted date string
    """
    if lang == "ENG":
        return date.strftime("%m/%d/%Y")
    else:  # UKR, RUS, POR
        return date.strftime("%d.%m.%Y")


def format_time(time, lang: str = "UKR") -> str:
    """
    Format time according to the language
    
    Args:
        time: Datetime object
        lang: Language code
        
    Returns:
        Formatted time string
    """
    if lang == "ENG":
        return time.strftime("%I:%M %p")
    else:  # UKR, RUS, POR
        return time.strftime("%H:%M")


def format_price(price: float, lang: str = "UKR") -> str:
    """
    Format price according to the language
    
    Args:
        price: Price value
        lang: Language code
        
    Returns:
        Formatted price string
    """
    # All languages use the same currency symbol for now
    return f"{price:.2f}₴"


def format_appointment_details(appointment: Dict[str, Any], procedures: list, master: Dict[str, Any], lang: str = "UKR") -> str:
    """
    Format appointment details for display
    
    Args:
        appointment: Appointment data
        procedures: List of procedures
        master: Master data
        lang: Language code
        
    Returns:
        Formatted appointment details
    """
    # Format date and time
    date_str = format_date(appointment["start_time"], lang)
    time_str = format_time(appointment["start_time"], lang)
    
    # Texts based on language
    if lang == "UKR":
        procedures_label = "Процедури"
        master_label = "Майстер"
        date_label = "Дата"
        time_label = "Час"
    elif lang == "ENG":
        procedures_label = "Procedures"
        master_label = "Master"
        date_label = "Date"
        time_label = "Time"
    elif lang == "POR":
        procedures_label = "Procedimentos"
        master_label = "Mestre"
        date_label = "Data"
        time_label = "Hora"
    else:  # RUS
        procedures_label = "Процедуры"
        master_label = "Мастер"
        date_label = "Дата"
        time_label = "Время"
    
    # Format procedures list
    procedures_text = "\n".join([f"- {proc['name']} ({format_price(proc['base_price'], lang)})" for proc in procedures])
    
    # Format details
    details = f"<b>{procedures_label}:</b>\n{procedures_text}\n\n"
    details += f"<b>{master_label}:</b> {master['name']}\n"
    details += f"<b>{date_label}:</b> {date_str}\n"
    details += f"<b>{time_label}:</b> {time_str}"
    
    return details
