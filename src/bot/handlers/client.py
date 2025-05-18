import logging
import os
from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Local imports
from src.bot.api_client import api_client, ApiError

# Настройка логгера
logger = logging.getLogger(__name__)

from src.bot.states import ClientStates
from src.bot.keyboards import (
    language_keyboard, section_keyboard, procedure_keyboard,
    master_or_time_keyboard, master_selection_keyboard,
    day_selection_keyboard, time_selection_keyboard, confirmation_keyboard,
    my_appointments_keyboard, appointment_details_keyboard,
    cancel_confirmation_keyboard
)
from src.database import crud
from src.database.models import Procedure
from src.utils.translations import get_text, format_appointment_details


# Start command handler
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle /start command"""
    # Reset state
    await state.clear()
    
    # Если клиент передан как параметр, используем его
    if client:
        # Получаем язык клиента из объекта client
        if isinstance(client, dict):
            lang = client.get("lang", "ru")
        else:
            lang = getattr(client, "lang", "ru")
        
        # Сохраняем язык в состоянии
        await state.update_data(lang=lang)
        
        # Получаем разделы из API и показываем их
        try:
            async with api_client as client_api:
                sections = await client_api.get_sections(lang=lang)
                
                if sections:
                    await message.answer(
                        get_text("select_section", lang),
                        reply_markup=section_keyboard(sections, lang)
                    )
                    
                    # Устанавливаем состояние выбора раздела
                    await state.set_state(ClientStates.section_selection)
                    return
                else:
                    logger.warning(f"No sections found for language: {lang}")
        except ApiError as e:
            logger.error(f"API error: {str(e)}")
    
    # Если клиент не передан или произошла ошибка, проверяем наличие по telegram_id
    try:
        # Получаем telegram_id из сообщения
        telegram_id = message.from_user.id if hasattr(message, 'from_user') and message.from_user else None
        if telegram_id:
            # Проверяем, есть ли клиент в базе данных
            client_db = await crud.get_client_by_telegram_id(session, str(telegram_id))
            if client_db:
                # Если клиент найден, используем его язык
                lang = client_db.get("lang", "ru")
                
                # Сохраняем язык в состоянии
                await state.update_data(lang=lang)
                
                # Получаем разделы из API и показываем их
                try:
                    async with api_client as client_api:
                        sections = await client_api.get_sections(lang=lang)
                        
                        if sections:
                            await message.answer(
                                get_text("select_section", lang),
                                reply_markup=section_keyboard(sections, lang)
                            )
                            
                            # Устанавливаем состояние выбора раздела
                            await state.set_state(ClientStates.section_selection)
                            return
                        else:
                            logger.warning(f"No sections found for language: {lang}")
                except ApiError as e:
                    logger.error(f"API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error checking client existence: {str(e)}")
    
    # Если клиент не найден или произошла ошибка, показываем выбор языка
    await message.answer(
        get_text("welcome"),
        reply_markup=language_keyboard()
    )
    
    # Устанавливаем состояние выбора языка
    await state.set_state(ClientStates.language_selection)


# Language selection handler
async def language_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle language selection"""
    try:
        if not state:
            logger.error("State is None in language_selection")
            if hasattr(callback, 'answer'):
                await callback.answer("Ошибка инициализации. Пожалуйста, начните снова с команды /start")
            return
            
        # Get selected language
        lang = callback.data.split(":")[1] if callback and callback.data and ":" in callback.data else "ru"
        
        # Save language to state
        await state.update_data(lang=lang)
        
        # If client exists, update language
        if client:
            try:
                await crud.update_client(session, client.id, {"lang": lang})
                await session.commit()
            except Exception as e:
                logger.error(f"Error updating client language: {str(e)}")
                await session.rollback()
        else:
            # Если клиент не передан, проверяем наличие по telegram_id
            try:
                # Получаем telegram_id из callback
                telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
                if telegram_id:
                    # Преобразуем telegram_id в строку и проверяем, есть ли клиент в базе данных
                    client_db = await crud.get_client_by_telegram_id(session, str(telegram_id))
                    if not client_db:
                        # Если клиент не найден, перенаправляем на регистрацию
                        logger.info(f"Client with telegram_id {telegram_id} not found, redirecting to registration")
                        if hasattr(callback, 'message') and callback.message:
                            await callback.message.edit_text(
                                get_text("registration_name_required", lang)
                            )
                            # Устанавливаем состояние регистрации имени
                            await state.set_state(ClientStates.registration_name)
                            return
            except Exception as e:
                logger.error(f"Error checking client existence: {str(e)}")
                # Продолжаем выполнение, чтобы не блокировать пользователя
        
        # Get sections from API
        try:
            async with api_client as client_api:
                sections = await client_api.get_sections(lang=lang)
                
                if not sections:
                    logger.warning(f"No sections found for language: {lang}")
                    if hasattr(callback, 'message') and callback.message:
                        await callback.message.answer(
                            get_text("no_sections_found", lang)
                        )
                    return
                
        except ApiError as e:
            logger.error(f"API error: {str(e)}")
            if hasattr(callback, 'message') and callback.message:
                await callback.message.answer(
                    get_text("api_error", lang)
                )
            return
        
        # Show section selection
        if hasattr(callback, 'message') and callback.message:
            await callback.message.edit_text(
                get_text("select_section", lang),
                reply_markup=section_keyboard(sections, lang)
            )
            
            # Set state to section selection
            await state.set_state(ClientStates.section_selection)
        else:
            logger.error("No message in callback")
            if hasattr(callback, 'answer'):
                await callback.answer("Ошибка при обработке запроса. Пожалуйста, попробуйте еще раз.")
                
    except Exception as e:
        logger.error(f"Error in language_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer("Произошла ошибка при выборе языка. Пожалуйста, попробуйте еще раз.")
        # Перезапускаем бота при критической ошибке
        if hasattr(callback, 'message') and callback.message:
            await cmd_start(callback.message, state, session, client)


# Registration name handler
async def registration_name(message: Message, state: FSMContext, session: AsyncSession):
    """Handle registration name input"""
    try:
        # Get language from state
        data = await state.get_data()
        lang = data.get("lang", "ru")  # Default to Russian if not set
        
        # Save name to state
        await state.update_data(name=message.text)
        
        # Ask for phone number
        await message.answer(
            get_text("phone_required", lang),
            reply_markup=None
        )
        
        # Set state to registration phone
        await state.set_state(ClientStates.registration_phone)
        
    except Exception as e:
        logger.error(f"Error in registration_name: {str(e)}", exc_info=True)
        await message.answer(get_text("error_occurred", lang))
        await cmd_start(message, state, session, None)


# Registration phone handler
async def registration_phone(message: Message, state: FSMContext, session: AsyncSession):
    """Handle registration phone input"""
    try:
        # Get data from state
        data = await state.get_data()
        lang = data.get("lang", "ru")
        name = data.get("name", "")
        
        # Create client
        client_data = {
            "telegram_id": str(message.from_user.id),  # Преобразуем telegram_id в строку
            "name": name,
            "phone": message.text,
            "lang": lang,
            "time_coeff": 1.0,
            "is_first_visit": True
        }
        
        # Create client in the database
        try:
            client = await crud.create_client(session, client_data)
            # Важно: выполняем коммит транзакции, чтобы сохранить данные в БД
            await session.commit()
            logger.info(f"Successfully created client with telegram_id: {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error creating client in database: {str(e)}")
            await session.rollback()
            raise
        
        # Show registration completed message
        await message.answer(
            get_text("registration_completed", lang)
        )
        
        # Get sections in selected language using API
        async with api_client as client_api:
            sections = await client_api.get_sections(lang=lang)
            
            if not sections:
                await message.answer(get_text("no_sections_found", lang))
                return
                
            # Show section selection
            await message.answer(
                get_text("select_section", lang),
                reply_markup=section_keyboard(sections, lang)
            )
            
            # Set state to section selection
            await state.set_state(ClientStates.section_selection)
            
    except Exception as e:
        logger.error(f"Error in registration_phone: {str(e)}", exc_info=True)
        await message.answer(get_text("error_occurred", lang))
        await cmd_start(message, state, session, None)


# Section selection handler
async def section_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle section selection"""
    try:
        # Get language from state
        state_data = await state.get_data()
        lang = state_data.get('lang', 'ru')  # Default to Russian if not set
        
        # Check if back button was pressed
        if callback.data.startswith("back:"):
            # Show language selection
            if hasattr(callback, 'message') and callback.message:
                await callback.message.edit_text(
                    get_text("welcome", lang=lang),
                    reply_markup=language_keyboard()
                )
                
                # Set state to language selection
                await state.set_state(ClientStates.language_selection)
            return
        
        # Get selected section ID
        section_id = int(callback.data.split(":")[1])
        
        # Get section and procedures from API
        async with api_client as client_api:
            # Get all sections and find the selected one
            response = await client_api.get_sections(lang=lang)
            
            # Проверяем формат данных
            if isinstance(response, dict) and 'data' in response:
                sections = response['data']
            else:
                sections = response
                
            # Проверяем, что sections - это список словарей
            if not isinstance(sections, list):
                logger.error(f"Unexpected sections format: {type(sections)}, content: {sections}")
                raise ValueError(f"Unexpected sections format: {type(sections)}")
                
            # Ищем секцию по ID
            section = None
            for s in sections:
                if isinstance(s, dict) and s.get('id') == section_id:
                    section = s
                    break
                    
            if not section:
                raise ValueError(f"Section with ID {section_id} not found")
            
            # Get procedures for the selected section
            procedures_response = await client_api.get_procedures(section_id=section_id, lang=lang)
            
            # Проверяем формат данных процедур
            if isinstance(procedures_response, dict) and 'data' in procedures_response:
                procedures = procedures_response['data']
            else:
                procedures = procedures_response
            
            # Show procedures list
            if hasattr(callback, 'message') and callback.message:
                # Получаем имя секции в зависимости от языка
                section_name = section.get(f"name_{lang}") or section.get("name") or section.get("name_ru", f"Section {section_id}")
                await callback.message.edit_text(
                    get_text("select_procedure", lang).format(section_name=section_name),
                    reply_markup=procedure_keyboard(procedures, [], lang)
                )
                
                # Set state to procedure selection with empty selected procedures
                await state.set_state(ClientStates.procedure_selection)
                await state.update_data(
                    section_id=section_id,
                    selected_procedures=[]
                )
    
    except (ValueError, ApiError) as e:
        logger.error(f"Error in section_selection (part 1): {str(e)}", exc_info=True)
        try:
            # Try to reload sections
            async with api_client as client_api:
                sections = await client_api.get_sections(lang=lang or 'ru')
                if hasattr(callback, 'message') and callback.message:
                    await callback.message.edit_text(
                        get_text("select_section", lang or 'ru'),
                        reply_markup=section_keyboard(sections, lang or 'ru')
                    )
                    return
        except Exception as inner_e:
            logger.error(f"Failed to reload sections: {str(inner_e)}")
            
        # If we couldn't recover, show error and restart
        if hasattr(callback, 'answer'):
            await callback.answer("Произошла ошибка. Пожалуйста, начните снова с команды /start")
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)
    
    except Exception as e:
        logger.error(f"Unexpected error in section_selection (part 2): {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer("Произошла непредвиденная ошибка. Пожалуйста, начните снова с команды /start")
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)


# Procedure selection handler
async def procedure_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle procedure selection"""
    try:
        # Get data from state
        state_data = await state.get_data()
        lang = state_data.get('lang', 'ru')  # Default to Russian if not set
        selected_procedures = state_data.get('selected_procedures', [])
        section_id = state_data.get('section_id')
        
        # Check if back button was pressed
        if callback.data == "back":
            # Clear selected procedures and go back to section selection
            await state.update_data(selected_procedures=[])
            
            # Get sections in selected language using API
            async with api_client as client_api:
                sections = await client_api.get_sections(lang=lang)
                
                if not sections:
                    await callback.answer(get_text("no_sections_found", lang))
                    return
                
                # Show section selection
                if hasattr(callback, 'message') and callback.message:
                    await callback.message.edit_text(
                        get_text("select_section", lang),
                        reply_markup=section_keyboard(sections, lang)
                    )
                
                # Set state to section selection
                await state.set_state(ClientStates.section_selection)
            return
            
        # Проверяем, нажата ли кнопка "Далее"
        if callback.data.startswith("next:") or callback.data == "next":
            # Проверяем, выбрана ли хотя бы одна процедура
            if not selected_procedures:
                await callback.answer(get_text("select_at_least_one_procedure", lang))
                return
                
            # Переходим к выбору мастера или времени
            if hasattr(callback, 'message') and callback.message:
                await callback.message.edit_text(
                    get_text("select_master_or_time", lang),
                    reply_markup=master_or_time_keyboard(lang)
                )
                
                # Устанавливаем состояние выбора мастера или времени
                await state.set_state(ClientStates.master_or_time_selection)
            return
        
        # Проверяем, что callback.data имеет правильный формат
        if not callback.data.startswith("procedure:"):
            logger.error(f"Unexpected callback data in procedure_selection: {callback.data}")
            await callback.answer(get_text("error_occurred", lang))
            return
            
        # Получаем ID процедуры из callback data
        try:
            procedure_id = int(callback.data.split(":")[1])
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing procedure_id from callback data: {callback.data}, error: {str(e)}")
            await callback.answer(get_text("error_occurred", lang))
            return
        
        # Get procedure details
        async with api_client as client_api:
            # Get procedure details
            procedure = await client_api.get_procedure(procedure_id, lang=lang)
            if not procedure:
                raise ValueError(f"Procedure with ID {procedure_id} not found")
            
            # Toggle procedure selection
            if procedure_id in selected_procedures:
                selected_procedures.remove(procedure_id)
            else:
                selected_procedures.append(procedure_id)
            
            # Update state with new selected procedures
            await state.update_data(selected_procedures=selected_procedures)
            
            # Get all procedures for the section
            procedures = await client_api.get_procedures(section_id=section_id, lang=lang)
            
            # Update message with new selection
            if hasattr(callback, 'message') and callback.message:
                section = await client_api.get_section(section_id, lang=lang)
                section_name = section.get(f"name_{lang}", section.get("name_ru", f"Section {section_id}"))
                
                await callback.message.edit_text(
                    get_text("select_procedure", lang).format(section_name=section_name),
                    reply_markup=procedure_keyboard(procedures, selected_procedures, lang)
                )
    
    except (ValueError, ApiError) as e:
        logger.error(f"Error in procedure_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'))
        
        # Try to recover by going back to section selection
        try:
            async with api_client as client_api:
                sections = await client_api.get_sections(lang=lang or 'ru')
                if hasattr(callback, 'message') and callback.message:
                    await callback.message.edit_text(
                        get_text("select_section", lang or 'ru'),
                        reply_markup=section_keyboard(sections, lang or 'ru')
                    )
                    await state.set_state(ClientStates.section_selection)
                    return
        except Exception as inner_e:
            logger.error(f"Failed to recover in procedure_selection: {str(inner_e)}")
            
        # If recovery failed, restart the bot
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)
    
    except Exception as e:
        logger.error(f"Unexpected error in procedure_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'))
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)


# Master or time selection handler
async def master_or_time_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle master or time selection"""
    try:
        # Get data from state
        state_data = await state.get_data()
        lang = state_data.get('lang', 'ru')  # Default to Russian if not set
        
        # Check if back button was pressed
        if callback.data == "back" or callback.data == "back:procedures":
            # Go back to procedure selection
            async with api_client as client_api:
                # Get selected section
                selected_section = state_data.get('selected_section')
                
                if not selected_section:
                    # If no section selected, go back to section selection
                    sections = await client_api.get_sections(lang=lang)
                    
                    if not sections:
                        await callback.answer(get_text("no_sections_found", lang))
                        return
                    
                    # Show section selection
                    if hasattr(callback, 'message') and callback.message:
                        await callback.message.edit_text(
                            get_text("select_section", lang),
                            reply_markup=section_keyboard(sections, lang)
                        )
                    
                    # Set state to section selection
                    await state.set_state(ClientStates.section_selection)
                else:
                    # Get procedures for the selected section
                    procedures = await client_api.get_procedures(selected_section, lang=lang)
                    
                    if not procedures:
                        await callback.answer(get_text("no_procedures_found", lang))
                        return
                    
                    # Get selected procedures from state
                    selected_procedures = state_data.get('selected_procedures', [])
                    
                    # Show procedure selection
                    if hasattr(callback, 'message') and callback.message:
                        await callback.message.edit_text(
                            get_text("select_procedures", lang),
                            reply_markup=procedure_keyboard(procedures, selected_procedures, lang)
                        )
                    
                    # Set state to procedure selection
                    await state.set_state(ClientStates.procedure_selection)
            return
            
        # Handle selection
        if callback.data == "select:master" or callback.data == "select_master":
            # Get masters for the selected procedures
            state_data = await state.get_data()
            selected_procedures = state_data.get('selected_procedures', [])
            
            if not selected_procedures:
                await callback.answer(get_text("no_procedures_selected", lang))
                return
                
            async with api_client as client_api:
                # Get masters who can perform the selected procedures
                try:
                    masters = await client_api.get_masters_for_procedures(selected_procedures, lang=lang)
                except AttributeError as e:
                    # Если метод get_masters_for_procedures не существует, используем get_masters
                    logger.warning(f"get_masters_for_procedures не найден, используем get_masters: {str(e)}")
                    masters = await client_api.get_masters(lang=lang)
                except Exception as e:
                    logger.error(f"Ошибка при получении мастеров: {str(e)}")
                    await callback.answer(get_text("error_occurred", lang))
                    return
                
                if not masters:
                    await callback.answer(get_text("no_masters_available", lang))
                    return
                
                # Show master selection
                if hasattr(callback, 'message') and callback.message:
                    await callback.message.edit_text(
                        get_text("select_master", lang),
                        reply_markup=master_selection_keyboard(masters, lang)
                    )
                
                # Set state to master selection
                await state.set_state(ClientStates.master_selection)
                
        elif callback.data == "select:time" or callback.data == "select_time":
            # Вместо прямого выбора времени, сначала показываем выбор дня
            # Получаем текущую дату
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Получаем выбранные процедуры из состояния
            data = await state.get_data()
            selected_procedures = data.get("selected_procedures", [])
            
            # Получаем список всех мастеров
            try:
                async with api_client as client_api:
                    try:
                        masters = await client_api.get_masters_for_procedures(selected_procedures, lang=lang)
                    except AttributeError as e:
                        # Если метод get_masters_for_procedures не существует, используем get_masters
                        logger.warning(f"get_masters_for_procedures не найден, используем get_masters: {str(e)}")
                        masters = await client_api.get_masters(lang=lang)
                    
                    # Получаем всех мастеров, которые умеют делать выбранные процедуры
                    if masters and isinstance(masters, list) and len(masters) > 0:
                        # Сохраняем список мастеров в состоянии
                        master_ids = []
                        for master in masters:
                            if isinstance(master, dict):
                                master_ids.append(master.get("id"))
                            else:
                                master_ids.append(master.id)
                        
                        await state.update_data(available_masters=master_ids)
                        
                        # Собираем все доступные дни для всех мастеров
                        all_available_days = set()
                        for master_id in master_ids:
                            # Получаем доступные дни для текущего мастера
                            master_days = await crud.get_available_days(session, master_id, today, 30)
                            # Добавляем дни в общий набор
                            all_available_days.update(master_days)
                        
                        # Преобразуем множество в список и сортируем
                        available_days = sorted(list(all_available_days))
                        
                        if available_days:
                            # Берем первые 5 доступных дней
                            days_to_show = available_days[:5]
                            has_more = len(available_days) > 5
                            
                            if hasattr(callback, 'message') and callback.message:
                                await callback.message.edit_text(
                                    get_text("select_day", lang),
                                    reply_markup=day_selection_keyboard(days_to_show, 0, lang, has_more)
                                )
                            
                            # Сохраняем доступные дни в состоянии
                            await state.update_data(available_days=available_days)
                            await state.update_data(auto_select_master=True)  # Флаг, что мастер будет выбран автоматически
                            
                            # Устанавливаем состояние выбора дня
                            await state.set_state(ClientStates.day_selection)
                            return
                        else:
                            # Если нет доступных дней, показываем сообщение об ошибке
                            if hasattr(callback, 'message') and callback.message:
                                await callback.message.edit_text(
                                    get_text("no_slots_available", lang),
                                    reply_markup=master_or_time_keyboard(lang)
                                )
                            return
                    else:
                        # Если нет мастеров, показываем сообщение об ошибке
                        if hasattr(callback, 'message') and callback.message:
                            await callback.message.edit_text(
                                get_text("no_masters_available", lang),
                                reply_markup=master_or_time_keyboard(lang)
                            )
                        return
            except Exception as e:
                logger.error(f"Error in master_or_time_selection (time option): {str(e)}", exc_info=True)
                if hasattr(callback, 'answer'):
                    await callback.answer(get_text("error_occurred", lang))
                return
    
    except (ValueError, ApiError) as e:
        logger.error(f"Error in master_or_time_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'))
        
        # Try to recover by going back to section selection
        try:
            async with api_client as client_api:
                sections = await client_api.get_sections(lang=lang or 'ru')
                if hasattr(callback, 'message') and callback.message:
                    await callback.message.edit_text(
                        get_text("select_section", lang or 'ru'),
                        reply_markup=section_keyboard(sections, lang or 'ru')
                    )
                    await state.set_state(ClientStates.section_selection)
                    return
        except Exception as inner_e:
            logger.error(f"Failed to recover in master_or_time_selection: {str(inner_e)}")
            
        # If recovery failed, restart the bot
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)
    
    except Exception as e:
        logger.error(f"Unexpected error in master_or_time_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'))
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)


# Master selection handler
async def master_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle master selection"""
    try:
        # Get data from state
        data = await state.get_data()
        
        # Get language from client or state
        if client and hasattr(client, 'lang'):
            lang = client.lang
        else:
            lang = data.get('lang', 'ru')  # Default to Russian if not set
            
        selected_procedures = data.get("selected_procedures", [])
    
        # Check if back button was pressed
        if callback.data.startswith("back:"):
            # Show master or time selection
            await callback.message.edit_text(
                get_text("select_master_or_time", lang),
                reply_markup=master_or_time_keyboard(lang)
            )
            
            # Set state to master or time selection
            await state.set_state(ClientStates.master_or_time_selection)
            return
        
        # Get selected master ID
    except Exception as e:
        logger.error(f"Error in master_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer("Произошла ошибка. Пожалуйста, начните снова с команды /start")
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)
        return
    try:
        master_id = int(callback.data.split(":")[1])
        
        # Save master ID to state
        await state.update_data(master_id=master_id)
        
        # Получаем данные о клиенте из базы данных, если client равен None
        if client is None:
            # Получаем telegram_id из callback
            telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
            if telegram_id:
                # Получаем клиента из базы данных
                client_db = await crud.get_client_by_telegram_id(session, telegram_id)
                time_coeff = client_db.time_coeff if client_db and hasattr(client_db, 'time_coeff') else 1.0
                is_first_visit = client_db.is_first_visit if client_db and hasattr(client_db, 'is_first_visit') else True
            else:
                # Если не удалось получить telegram_id, используем значения по умолчанию
                time_coeff = 1.0
                is_first_visit = True
        else:
            # Используем данные из объекта client
            time_coeff = client.time_coeff if hasattr(client, 'time_coeff') else 1.0
            is_first_visit = client.is_first_visit if hasattr(client, 'is_first_visit') else True
        
        # Calculate appointment duration
        duration = await crud.calculate_appointment_duration(
            session, selected_procedures, time_coeff, is_first_visit
        )
        
        # Save duration to state
        await state.update_data(duration=duration)
        
        # Get current date
        today = datetime.now()
        
        # Get available days for the next 30 days
        available_days = await crud.get_available_days(session, master_id, today, 30)
        
        if not available_days:
            await callback.answer(get_text("no_slots_available", lang), show_alert=True)
            return
        
        # Save master_id and duration to state for later use
        await state.update_data({
            "master_id": master_id,
            "duration": duration,
            "available_days": available_days,
            "current_page": 0
        })
        
        # Show day selection (first 5 days)
        days_to_show = available_days[:5]
        
        # Create a message with available days
        await callback.message.edit_text(
            get_text("select_day", lang),
            reply_markup=day_selection_keyboard(days_to_show, 0, lang, len(available_days) > 5)
        )
        
        # Set state to day selection
        await state.set_state(ClientStates.day_selection)
    except Exception as e:
        logger.error(f"Error in master_selection (processing master): {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang))
        return


# Day selection handler
async def day_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle day selection"""
    try:
        # Get data from state
        data = await state.get_data()
        
        # Get language from client or state
        if client and hasattr(client, 'lang'):
            lang = client.lang
        else:
            lang = data.get('lang', 'ru')  # Default to Russian if not set
        
        # Get available days from state
        available_days = data.get("available_days", [])
        
        # Check if back button was pressed
        if callback.data == "back:master":
            # Show master or time selection
            try:
                await callback.message.edit_text(
                    get_text("select_master_or_time", lang),
                    reply_markup=master_or_time_keyboard(lang)
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer(get_text("select_master_or_time", lang), show_alert=True)
                else:
                    raise
            
            # Set state to master or time selection
            await state.set_state(ClientStates.master_or_time_selection)
            return
        
        # Check if "later" button was pressed
        if callback.data.startswith("later:"):
            # Get next page
            next_page = int(callback.data.split(":")[1])
            
            # Calculate start and end indices for the next page
            start_idx = next_page * 5
            end_idx = min(start_idx + 5, len(available_days))
            
            # Get days for the next page
            days_to_show = available_days[start_idx:end_idx]
            has_more = end_idx < len(available_days)
            
            # Show next page of days
            try:
                await callback.message.edit_text(
                    get_text("select_day", lang),
                    reply_markup=day_selection_keyboard(days_to_show, next_page, lang, has_more)
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer(get_text("select_day", lang), show_alert=True)
                else:
                    raise
            return
        
        # Get selected day
        selected_day = datetime.fromisoformat(callback.data.split(":")[1])
        
        # Save selected day to state
        await state.update_data(selected_day=selected_day)
        
        # Check if we need to auto-select master
        auto_select_master = data.get("auto_select_master", False)
        
        if auto_select_master:
            # Get available masters from state
            available_masters = data.get("available_masters", [])
            
            # Find all masters that have available slots on the selected day
            masters_with_slots = []
            for master_id in available_masters:
                # Get available slots for this master on the selected day
                slots = await crud.get_available_slots(session, master_id, selected_day)
                if slots:
                    masters_with_slots.append((master_id, len(slots)))
            
            if masters_with_slots:
                # Sort masters by number of available slots (descending)
                masters_with_slots.sort(key=lambda x: x[1], reverse=True)
                
                # Select the master with the most available slots
                selected_master_id = masters_with_slots[0][0]
                
                # Save selected master to state
                await state.update_data(selected_master=selected_master_id)
                await state.update_data(master_id=selected_master_id)
                
                # Get available slots for the selected master on the selected day
                selected_procedures = data.get("selected_procedures", [])
                
                # Получаем данные о клиенте из базы данных, если client равен None
                if client is None:
                    # Получаем telegram_id из callback
                    telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
                    if telegram_id:
                        # Получаем клиента из базы данных
                        client_db = await crud.get_client_by_telegram_id(session, str(telegram_id))
                        if isinstance(client_db, dict):
                            time_coeff = client_db.get("time_coeff", 1.0)
                            is_first_visit = client_db.get("is_first_visit", True)
                        else:
                            time_coeff = getattr(client_db, "time_coeff", 1.0) if client_db else 1.0
                            is_first_visit = getattr(client_db, "is_first_visit", True) if client_db else True
                    else:
                        # Если не удалось получить telegram_id, используем значения по умолчанию
                        time_coeff = 1.0
                        is_first_visit = True
                else:
                    # Используем данные из объекта client
                    if isinstance(client, dict):
                        time_coeff = client.get("time_coeff", 1.0)
                        is_first_visit = client.get("is_first_visit", True)
                    else:
                        time_coeff = getattr(client, "time_coeff", 1.0)
                        is_first_visit = getattr(client, "is_first_visit", True)
                
                # Рассчитываем продолжительность приема
                duration = await crud.calculate_appointment_duration(
                    session, selected_procedures, time_coeff, is_first_visit
                )
                
                # Получаем доступные слоты для выбранного мастера на выбранный день
                slots = await crud.get_available_slots(session, selected_master_id, selected_day, duration)
                
                if slots:
                    # Show time selection
                    try:
                        await callback.message.edit_text(
                            get_text("select_time", lang),
                            reply_markup=time_selection_keyboard(slots, 0, 5, lang)
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            await callback.answer(get_text("select_time", lang), show_alert=True)
                        else:
                            raise
                    
                    # Save slots to state
                    await state.update_data(available_slots=slots)
                    
                    # Set state to time selection
                    await state.set_state(ClientStates.time_selection)
                else:
                    # If no slots available, show message
                    try:
                        await callback.message.edit_text(
                            get_text("no_slots_available", lang),
                            reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            await callback.answer(get_text("no_slots_available", lang), show_alert=True)
                        else:
                            raise
            else:
                # If no masters available, show message
                try:
                    await callback.message.edit_text(
                        get_text("no_masters_available", lang),
                        reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        await callback.answer(get_text("no_masters_available", lang), show_alert=True)
                    else:
                        raise
        else:
            # If not auto-selecting master, proceed with the selected master
            selected_master = data.get("selected_master")
            
            if selected_master:
                # Get available slots for the selected master on the selected day
                selected_procedures = data.get("selected_procedures", [])
                
                # Получаем данные о клиенте из базы данных, если client равен None
                if client is None:
                    # Получаем telegram_id из callback
                    telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
                    if telegram_id:
                        # Получаем клиента из базы данных
                        client_db = await crud.get_client_by_telegram_id(session, str(telegram_id))
                        if isinstance(client_db, dict):
                            time_coeff = client_db.get("time_coeff", 1.0)
                            is_first_visit = client_db.get("is_first_visit", True)
                        else:
                            time_coeff = getattr(client_db, "time_coeff", 1.0) if client_db else 1.0
                            is_first_visit = getattr(client_db, "is_first_visit", True) if client_db else True
                    else:
                        # Если не удалось получить telegram_id, используем значения по умолчанию
                        time_coeff = 1.0
                        is_first_visit = True
                else:
                    # Используем данные из объекта client
                    if isinstance(client, dict):
                        time_coeff = client.get("time_coeff", 1.0)
                        is_first_visit = client.get("is_first_visit", True)
                    else:
                        time_coeff = getattr(client, "time_coeff", 1.0)
                        is_first_visit = getattr(client, "is_first_visit", True)
                
                # Рассчитываем продолжительность приема
                duration = await crud.calculate_appointment_duration(
                    session, selected_procedures, time_coeff, is_first_visit
                )
                
                # Получаем доступные слоты для выбранного мастера на выбранный день
                slots = await crud.get_available_slots(session, selected_master, selected_day, duration)
                
                if slots:
                    # Show time selection
                    try:
                        await callback.message.edit_text(
                            get_text("select_time", lang),
                            reply_markup=time_selection_keyboard(slots, 0, 5, lang)
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            await callback.answer(get_text("select_time", lang), show_alert=True)
                        else:
                            raise
                    
                    # Save slots to state
                    await state.update_data(available_slots=slots)
                    
                    # Set state to time selection
                    await state.set_state(ClientStates.time_selection)
                else:
                    # If no slots available, show message
                    try:
                        await callback.message.edit_text(
                            get_text("no_slots_available", lang),
                            reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            await callback.answer(get_text("no_slots_available", lang), show_alert=True)
                        else:
                            raise
            else:
                # If no selected master, show error message
                try:
                    await callback.message.edit_text(
                        get_text("error_occurred", lang),
                        reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        await callback.answer(get_text("error_occurred", lang), show_alert=True)
                    else:
                        raise
    except Exception as e:
        logger.error(f"Error in day_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'))


# Time selection handler
async def time_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle time selection"""
    try:
        # Get data from state
        data = await state.get_data()
        
        # Get language from client or state
        if client and hasattr(client, 'lang'):
            lang = client.lang
        else:
            lang = data.get('lang', 'ru')  # Default to Russian if not set
        
        master_id = data.get("master_id")
        selected_procedures = data.get("selected_procedures", [])
        slots = data.get("slots", [])
    
        # Check if back button was pressed
        if callback.data.startswith("back:"):
            # Show master or time selection
            await callback.message.edit_text(
                get_text("select_master_or_time", lang),
                reply_markup=master_or_time_keyboard(lang)
            )
            
            # Set state to master or time selection
            await state.set_state(ClientStates.master_or_time_selection)
            return
        
        # Check if page navigation
        if callback.data.startswith("page:"):
            page = int(callback.data.split(":")[1])
            
            # Show time selection for the selected page
            await callback.message.edit_text(
                get_text("select_time", lang),
                reply_markup=time_selection_keyboard(slots, page, 1, lang)
            )
            return
        
        # Get selected time
        selected_time = datetime.fromisoformat(callback.data.split(":")[1])
        
        # Save selected time to state
        await state.update_data(selected_time=selected_time)
        
        # Get procedures details
        procedures = []
        total_price = 0
        
        for procedure_id in selected_procedures:
            # Получаем информацию о процедуре из базы данных
            procedure_data = await crud.get_procedure_by_id(session, procedure_id)
            if procedure_data:
                # Используем данные из функции get_procedure_by_id
                procedures.append({
                    "id": procedure_data["id"],
                    "name": procedure_data["name"],
                    "base_price": procedure_data["base_price"],
                    "discount": procedure_data["discount"]
                })
                total_price += procedure_data["base_price"] * (1 - procedure_data["discount"] / 100)
        
        # Get master details
        master_data = await crud.get_master_by_id(session, master_id)
        
        # Format appointment details
        details = format_appointment_details(
            {"start_time": selected_time},
            procedures,
            {"name": master_data["name"] if master_data else ""},
            lang
        )
    except Exception as e:
        logger.error(f"Error in time_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer("Произошла ошибка. Пожалуйста, начните снова с команды /start")
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)
        return
        
    # Продолжение функции вне блока try-except
    # Show appointment confirmation
    try:
        await callback.message.edit_text(
            get_text("appointment_confirmation", lang, details=details, total_price=total_price),
            reply_markup=confirmation_keyboard(lang)
        )
        
        # Set state to appointment confirmation
        await state.set_state(ClientStates.appointment_confirmation)
    except Exception as e:
        logger.error(f"Error in time_selection (confirmation): {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang))
        return


# Appointment confirmation handler
async def appointment_confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle appointment confirmation"""
    try:
        # Get data from state
        data = await state.get_data()
        
        # Get language from client or state
        if client and hasattr(client, 'lang'):
            lang = client.lang
        else:
            lang = data.get('lang', 'ru')  # Default to Russian if not set
        
        master_id = data.get("master_id")
        selected_procedures = data.get("selected_procedures", [])
        selected_time = data.get("selected_time")
        duration = data.get("duration", 60)  # Default to 60 minutes if not set
        
        # Check if confirmed or canceled
        confirmation = callback.data.split(":")[1]
        
        if confirmation == "no":
            # Show cancellation message
            await callback.message.edit_text(
                get_text("appointment_canceled", lang),
                reply_markup=None
            )
            
            # Reset state
            await state.clear()
            return
        
        # Получаем данные о клиенте из базы данных, если client равен None
        if client is None:
            # Получаем telegram_id из callback
            telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
            if telegram_id:
                # Получаем клиента из базы данных
                client_db = await crud.get_client_by_telegram_id(session, telegram_id)
                if client_db:
                    # client_db - это словарь, поэтому используем ключ "id", а не атрибут
                    client_id = client_db["id"]
                else:
                    # Если клиент не найден, показываем ошибку
                    await callback.answer(get_text("client_not_found", lang), show_alert=True)
                    return
            else:
                # Если не удалось получить telegram_id, показываем ошибку
                await callback.answer(get_text("error_occurred", lang), show_alert=True)
                return
        else:
            # Используем данные из объекта client
            # Проверяем, является ли client словарем или объектом
            if isinstance(client, dict):
                client_id = client["id"]
            else:
                client_id = client.id
        
        # Calculate end time
        end_time = selected_time + timedelta(minutes=duration)
        
        # Create appointment
        appointment_data = {
            "client_id": client_id,
            "master_id": master_id,
            "workplace_id": 1,  # Simplified - in a real app, you'd get this from the master's work slot
            "procedures": selected_procedures,
            "start_time": selected_time,
            "end_time": end_time,
            "status": "active"
        }
        
        appointment = await crud.create_appointment(session, appointment_data)
        
        # Format date and time for confirmation message
        date_str = selected_time.strftime("%d.%m.%Y")
        time_str = selected_time.strftime("%H:%M")
        
        # Show confirmation message
        await callback.message.edit_text(
            get_text("appointment_confirmed", lang, date=date_str, time=time_str),
            reply_markup=None
        )
        
        # Reset state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in appointment_confirmation: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'), show_alert=True)
        if hasattr(callback, 'message') and hasattr(callback.message, 'answer'):
            await cmd_start(callback.message, state, session, client)
        return


# My appointments command handler
async def cmd_my_appointments(message: Message, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle /my_appointments command"""
    try:
        # Check if client exists
        if not client:
            # Получаем telegram_id из message
            telegram_id = message.from_user.id if hasattr(message, 'from_user') and message.from_user else None
            if telegram_id:
                # Получаем клиента из базы данных
                client_db = await crud.get_client_by_telegram_id(session, telegram_id)
                if client_db:
                    client = client_db
                else:
                    # Если клиент не найден, предлагаем зарегистрироваться
                    # Show language selection
                    await message.answer(
                        get_text("welcome"),
                        reply_markup=language_keyboard()
                    )
                    
                    # Set state to language selection
                    await state.set_state(ClientStates.language_selection)
                    return
            else:
                # Если не удалось получить telegram_id, показываем ошибку
                await message.answer("Произошла ошибка. Пожалуйста, начните снова с команды /start")
                return
        
        # Get language from client
        lang = client.lang if hasattr(client, 'lang') else 'ru'
        
        # Get active appointments
        appointments = await crud.get_client_appointments(session, client.id, "active")
        
        if not appointments:
            await message.answer(get_text("no_appointments", lang))
            return
    except Exception as e:
        logger.error(f"Error in cmd_my_appointments: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка. Пожалуйста, начните снова с команды /start")
        return
    
    # Show appointments
    await message.answer(
        get_text("my_appointments", lang),
        reply_markup=my_appointments_keyboard(appointments, lang)
    )
    
    # Set state to my appointments
    await state.set_state(ClientStates.my_appointments)


# Appointment details handler
async def appointment_details(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle appointment details"""
    # Get language from client
    lang = client.lang
    
    # Get appointment ID
    appointment_id = int(callback.data.split(":")[1])
    
    # Get appointment details
    appointment = await session.get(Appointment, appointment_id)
    
    if not appointment or appointment.client_id != client.id:
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        return
    
    # Get procedures details
    procedures = []
    
    for procedure_id in appointment.procedures:
        # In a real app, you'd get this from the database
        # This is a simplified version
        procedure = await session.get(Procedure, procedure_id)
        procedures.append({
            "id": procedure.id,
            "name": procedure.name,
            "base_price": procedure.base_price,
            "discount": procedure.discount
        })
    
    # Get master details
    master = await session.get(Master, appointment.master_id)
    
    # Format appointment details
    details = format_appointment_details(
        {"start_time": appointment.start_time},
        procedures,
        {"name": master.name},
        lang
    )
    
    # Show appointment details
    await callback.message.edit_text(
        get_text("appointment_details", lang, details=details),
        reply_markup=appointment_details_keyboard(appointment_id, lang)
    )
    
    # Set state to appointment details
    await state.set_state(ClientStates.appointment_details)


# Cancel appointment handler
async def cancel_appointment(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle cancel appointment"""
    # Get language from client
    lang = client.lang
    
    # Get appointment ID
    appointment_id = int(callback.data.split(":")[1])
    
    # Show cancel confirmation
    await callback.message.edit_text(
        get_text("cancel_appointment_confirmation", lang),
        reply_markup=cancel_confirmation_keyboard(appointment_id, lang)
    )
    
    # Set state to cancel appointment
    await state.set_state(ClientStates.cancel_appointment)


# Cancel appointment confirmation handler
async def cancel_appointment_confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle cancel appointment confirmation"""
    # Get language from client
    lang = client.lang
    
    # Get confirmation and appointment ID
    parts = callback.data.split(":")
    confirmation = parts[1]
    appointment_id = int(parts[2])
    
    if confirmation == "no":
        # Get appointment details
        appointment = await session.get(Appointment, appointment_id)
        
        if not appointment or appointment.client_id != client.id:
            await callback.answer(get_text("error_occurred", lang), show_alert=True)
            return
        
        # Get procedures details
        procedures = []
        
        for procedure_id in appointment.procedures:
            # In a real app, you'd get this from the database
            # This is a simplified version
            procedure = await session.get(Procedure, procedure_id)
            procedures.append({
                "id": procedure.id,
                "name": procedure.name,
                "base_price": procedure.base_price,
                "discount": procedure.discount
            })
        
        # Get master details
        master = await session.get(Master, appointment.master_id)
        
        # Format appointment details
        details = format_appointment_details(
            {"start_time": appointment.start_time},
            procedures,
            {"name": master.name},
            lang
        )
        
        # Show appointment details
        await callback.message.edit_text(
            get_text("appointment_details", lang, details=details),
            reply_markup=appointment_details_keyboard(appointment_id, lang)
        )
        
        # Set state to appointment details
        await state.set_state(ClientStates.appointment_details)
        return
    
    # Update appointment status
    await crud.update_appointment_status(session, appointment_id, "canceled")
    
    # Show cancellation message
    await callback.message.edit_text(
        get_text("appointment_canceled", lang)
    )
    
    # Reset state
    await state.clear()


def register_client_handlers(dp: Dispatcher):
    """Register client handlers"""
    from functools import partial
    
    # Обертка для обработчиков, чтобы передавать client, session и state
    def wrap_handler(handler):
        async def wrapped_handler(event, **kwargs):
            try:
                # Получаем данные из kwargs или data
                data = kwargs.get("data", {}) if 'data' in kwargs else kwargs
                
                # Получаем state из data или kwargs
                state = data.get("state") if 'state' in data else kwargs.get("state")
                
                # Получаем сессию
                session = data.get("session") if 'session' in data else kwargs.get("session")
                
                # Получаем клиента
                client = data.get("client") if 'client' in data else kwargs.get("client")
                
                # Если state не передан, пробуем получить его из диспетчера
                if state is None and hasattr(event, 'message') and hasattr(event.message, 'chat') and hasattr(event.message.chat, 'id'):
                    from aiogram.fsm.storage.base import StorageKey
                    from aiogram.fsm.storage.memory import MemoryStorage
                    
                    storage = MemoryStorage()
                    state = FSMContext(
                        storage=storage,
                        key=StorageKey(
                            bot_id=event.bot.id,
                            chat_id=event.message.chat.id,
                            user_id=event.from_user.id
                        )
                    )
                
                # Определяем, является ли событие CallbackQuery
                is_callback = isinstance(event, CallbackQuery)
                
                # Формируем базовые аргументы
                handler_args = {
                    'state': state,
                    'session': session,
                    'client': client
                }
                
                # Добавляем правильный аргумент в зависимости от типа события
                if is_callback:
                    handler_args['callback'] = event
                else:
                    handler_args['message'] = event
                
                # Вызываем обработчик с правильными аргументами
                return await handler(**handler_args)
                
            except Exception as e:
                logger.error(f"Error in wrapped_handler: {str(e)}", exc_info=True)
                if hasattr(event, 'answer'):
                    await event.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз.")
                # Перезапускаем бота при критической ошибке
                if hasattr(event, 'message') and hasattr(event.message, 'answer'):
                    await event.message.answer("Произошла критическая ошибка. Начинаем заново...")
                    # Пытаемся перезапустить бота
                    if 'state' in locals() and state:
                        await cmd_start(event, state, session, client)
                raise
                
        return wrapped_handler
    
    # Command handlers
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_my_appointments, Command(commands=["my_appointments"]))
    
    # State handlers
    dp.callback_query.register(wrap_handler(language_selection), ClientStates.language_selection)
    dp.message.register(registration_name, ClientStates.registration_name)
    dp.message.register(registration_phone, ClientStates.registration_phone)
    
    # Register handlers with state and client
    def register_handler(handler, *filters, **kwargs):
        wrapped = wrap_handler(handler)
        return dp.callback_query.register(wrapped, *filters, **kwargs)
    
    # Регистрируем обработчики с состоянием
    register_handler(section_selection, ClientStates.section_selection)
    register_handler(procedure_selection, ClientStates.procedure_selection)
    register_handler(master_or_time_selection, ClientStates.master_or_time_selection)
    register_handler(master_selection, ClientStates.master_selection)
    register_handler(day_selection, ClientStates.day_selection)
    register_handler(time_selection, ClientStates.time_selection)
    register_handler(appointment_confirmation, ClientStates.appointment_confirmation)
    register_handler(appointment_details, ClientStates.my_appointments, F.data.startswith("appointment:"))
    register_handler(cancel_appointment, ClientStates.appointment_details, F.data.startswith("cancel:"))
    register_handler(cancel_appointment_confirmation, ClientStates.cancel_appointment)


# Day selection handler
async def day_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle day selection"""
    try:
        # Get data from state
        data = await state.get_data()
        
        # Get language from client or state
        if client and hasattr(client, 'lang'):
            lang = client.lang
        else:
            lang = data.get('lang', 'ru')  # Default to Russian if not set
        
        # Get available days from state
        available_days = data.get("available_days", [])
        
        # Check if back button was pressed
        if callback.data == "back:master":
            # Show master or time selection
            await callback.message.edit_text(
                get_text("select_master_or_time", lang),
                reply_markup=master_or_time_keyboard(lang)
            )
            
            # Set state to master or time selection
            await state.set_state(ClientStates.master_or_time_selection)
            return
        
        # Check if "later" button was pressed
        if callback.data.startswith("later:"):
            # Get next page
            next_page = int(callback.data.split(":")[1])
            
            # Calculate start and end indices for the next page
            start_idx = next_page * 5
            end_idx = min(start_idx + 5, len(available_days))
            
            # Get days for the next page
            days_to_show = available_days[start_idx:end_idx]
            has_more = end_idx < len(available_days)
            
            # Show next page of days
            await callback.message.edit_text(
                get_text("select_day", lang),
                reply_markup=day_selection_keyboard(days_to_show, next_page, lang, has_more)
            )
            return
        
        # Get selected day
        selected_day = datetime.fromisoformat(callback.data.split(":")[1])
        
        # Save selected day to state
        await state.update_data(selected_day=selected_day)
        
        # Check if we need to auto-select master
        auto_select_master = data.get("auto_select_master", False)
        
        if auto_select_master:
            # Get available masters from state
            available_masters = data.get("available_masters", [])
            
            # Find all masters that have available slots on the selected day
            masters_with_slots = []
            for master_id in available_masters:
                # Get available slots for this master on the selected day
                slots = await crud.get_available_slots(session, master_id, selected_day)
                if slots:
                    masters_with_slots.append((master_id, len(slots)))
            
            if masters_with_slots:
                # Sort masters by number of available slots (descending)
                masters_with_slots.sort(key=lambda x: x[1], reverse=True)
                
                # Select the master with the most available slots
                selected_master_id = masters_with_slots[0][0]
                
                # Save selected master to state
                await state.update_data(selected_master=selected_master_id)
                await state.update_data(master_id=selected_master_id)
                
                # Get available slots for the selected master on the selected day
                selected_procedures = data.get("selected_procedures", [])
                
                # Получаем данные о клиенте из базы данных, если client равен None
                if client is None:
                    # Получаем telegram_id из callback
                    telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
                    if telegram_id:
                        # Получаем клиента из базы данных
                        client_db = await crud.get_client_by_telegram_id(session, str(telegram_id))
                        if isinstance(client_db, dict):
                            time_coeff = client_db.get("time_coeff", 1.0)
                            is_first_visit = client_db.get("is_first_visit", True)
                        else:
                            time_coeff = getattr(client_db, "time_coeff", 1.0) if client_db else 1.0
                            is_first_visit = getattr(client_db, "is_first_visit", True) if client_db else True
                    else:
                        # Если не удалось получить telegram_id, используем значения по умолчанию
                        time_coeff = 1.0
                        is_first_visit = True
                else:
                    # Используем данные из объекта client
                    if isinstance(client, dict):
                        time_coeff = client.get("time_coeff", 1.0)
                        is_first_visit = client.get("is_first_visit", True)
                    else:
                        time_coeff = getattr(client, "time_coeff", 1.0)
                        is_first_visit = getattr(client, "is_first_visit", True)
                
                # Рассчитываем продолжительность приема
                duration = await crud.calculate_appointment_duration(
                    session, selected_procedures, time_coeff, is_first_visit
                )
                
                # Получаем доступные слоты для выбранного мастера на выбранный день
                slots = await crud.get_available_slots(session, selected_master_id, selected_day, duration)
                
                if slots:
                    # Show time selection
                    await callback.message.edit_text(
                        get_text("select_time", lang),
                        reply_markup=time_selection_keyboard(slots, 0, 5, lang)
                    )
                    
                    # Save slots to state
                    await state.update_data(available_slots=slots)
                    
                    # Set state to time selection
                    await state.set_state(ClientStates.time_selection)
                else:
                    # If no slots available, show message
                    await callback.message.edit_text(
                        get_text("no_slots_available", lang),
                        reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                    )
            else:
                # If no masters available, show message
                await callback.message.edit_text(
                    get_text("no_masters_available", lang),
                    reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                )
        else:
            # If not auto-selecting master, proceed with the selected master
            selected_master = data.get("selected_master")
            
            if selected_master:
                # Get available slots for the selected master on the selected day
                selected_procedures = data.get("selected_procedures", [])
                
                # Получаем данные о клиенте из базы данных, если client равен None
                if client is None:
                    # Получаем telegram_id из callback
                    telegram_id = callback.from_user.id if hasattr(callback, 'from_user') and callback.from_user else None
                    if telegram_id:
                        # Получаем клиента из базы данных
                        client_db = await crud.get_client_by_telegram_id(session, str(telegram_id))
                        if isinstance(client_db, dict):
                            time_coeff = client_db.get("time_coeff", 1.0)
                            is_first_visit = client_db.get("is_first_visit", True)
                        else:
                            time_coeff = getattr(client_db, "time_coeff", 1.0) if client_db else 1.0
                            is_first_visit = getattr(client_db, "is_first_visit", True) if client_db else True
                    else:
                        # Если не удалось получить telegram_id, используем значения по умолчанию
                        time_coeff = 1.0
                        is_first_visit = True
                else:
                    # Используем данные из объекта client
                    if isinstance(client, dict):
                        time_coeff = client.get("time_coeff", 1.0)
                        is_first_visit = client.get("is_first_visit", True)
                    else:
                        time_coeff = getattr(client, "time_coeff", 1.0)
                        is_first_visit = getattr(client, "is_first_visit", True)
                
                # Рассчитываем продолжительность приема
                duration = await crud.calculate_appointment_duration(
                    session, selected_procedures, time_coeff, is_first_visit
                )
                
                # Получаем доступные слоты для выбранного мастера на выбранный день
                slots = await crud.get_available_slots(session, selected_master, selected_day, duration)
                
                if slots:
                    # Show time selection
                    await callback.message.edit_text(
                        get_text("select_time", lang),
                        reply_markup=time_selection_keyboard(slots, 0, 5, lang)
                    )
                    
                    # Save slots to state
                    await state.update_data(available_slots=slots)
                    
                    # Set state to time selection
                    await state.set_state(ClientStates.time_selection)
                else:
                    # If no slots available, show message
                    await callback.message.edit_text(
                        get_text("no_slots_available", lang),
                        reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                    )
            else:
                # If no selected master, show error message
                await callback.message.edit_text(
                    get_text("error_occurred", lang),
                    reply_markup=day_selection_keyboard(available_days[:5], 0, lang, len(available_days) > 5)
                )
    except Exception as e:
        logger.error(f"Error in day_selection: {str(e)}", exc_info=True)
        if hasattr(callback, 'answer'):
            await callback.answer(get_text("error_occurred", lang or 'ru'))

# Регистрация функций-обработчиков
def register_client_handlers(router: Router):
    # Команда /start
    router.message.register(cmd_start, CommandStart())
    
    # Выбор языка
    router.callback_query.register(language_selection, ClientStates.language_selection)
    
    # Регистрация имени
    router.message.register(registration_name, ClientStates.registration_name)
    
    # Регистрация телефона
    router.message.register(registration_phone, ClientStates.registration_phone)
    
    # Выбор раздела
    router.callback_query.register(section_selection, ClientStates.section_selection)
    
    # Выбор процедур
    router.callback_query.register(procedure_selection, ClientStates.procedure_selection)
    
    # Выбор мастера или времени
    router.callback_query.register(master_or_time_selection, ClientStates.master_or_time_selection)
    
    # Выбор мастера
    router.callback_query.register(master_selection, ClientStates.master_selection)
    
    # Выбор дня
    router.callback_query.register(day_selection, ClientStates.day_selection)
    
    # Выбор времени
    router.callback_query.register(time_selection, ClientStates.time_selection)
    
    # Подтверждение записи
    router.callback_query.register(appointment_confirmation, ClientStates.appointment_confirmation)
