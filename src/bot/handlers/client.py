from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.bot.states import ClientStates
from src.bot.keyboards import (
    language_keyboard, section_keyboard, procedure_keyboard,
    master_or_time_keyboard, master_selection_keyboard,
    time_selection_keyboard, confirmation_keyboard,
    my_appointments_keyboard, appointment_details_keyboard,
    cancel_confirmation_keyboard
)
from src.database import crud
from src.utils.translations import get_text, format_appointment_details


# Start command handler
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle /start command"""
    # Reset state
    await state.clear()
    
    # Show language selection
    await message.answer(
        get_text("welcome"),
        reply_markup=language_keyboard()
    )
    
    # Set state to language selection
    await state.set_state(ClientStates.language_selection)


# Language selection handler
async def language_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle language selection"""
    # Get selected language
    lang = callback.data.split(":")[1]
    
    # Save language to state
    await state.update_data(lang=lang)
    
    # If client exists, update language
    if client:
        await crud.update_client(session, client.id, {"lang": lang})
    else:
        # Ask for registration if client doesn't exist
        await callback.message.edit_text(
            get_text("registration_required", lang),
            reply_markup=None
        )
        await state.set_state(ClientStates.registration_name)
        return
    
    # Get sections in selected language
    sections = await crud.get_sections(session, lang)
    
    # Show section selection
    await callback.message.edit_text(
        get_text("select_section", lang),
        reply_markup=section_keyboard(sections, lang)
    )
    
    # Set state to section selection
    await state.set_state(ClientStates.section_selection)


# Registration name handler
async def registration_name(message: Message, state: FSMContext, session: AsyncSession):
    """Handle registration name input"""
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "UKR")
    
    # Save name to state
    await state.update_data(name=message.text)
    
    # Ask for phone number
    await message.answer(
        get_text("phone_required", lang),
        reply_markup=None
    )
    
    # Set state to registration phone
    await state.set_state(ClientStates.registration_phone)


# Registration phone handler
async def registration_phone(message: Message, state: FSMContext, session: AsyncSession):
    """Handle registration phone input"""
    # Get data from state
    data = await state.get_data()
    lang = data.get("lang", "UKR")
    name = data.get("name", "")
    
    # Create client
    client_data = {
        "telegram_id": message.from_user.id,
        "name": name,
        "phone": message.text,
        "lang": lang,
        "time_coeff": 1.0,
        "is_first_visit": True
    }
    
    client = await crud.create_client(session, client_data)
    
    # Show registration completed message
    await message.answer(
        get_text("registration_completed", lang)
    )
    
    # Get sections in selected language
    sections = await crud.get_sections(session, lang)
    
    # Show section selection
    await message.answer(
        get_text("select_section", lang),
        reply_markup=section_keyboard(sections, lang)
    )
    
    # Set state to section selection
    await state.set_state(ClientStates.section_selection)


# Section selection handler
async def section_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
    """Handle section selection"""
    # Get language from client
    lang = client.lang
    
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show language selection
        await callback.message.edit_text(
            get_text("welcome"),
            reply_markup=language_keyboard()
        )
        
        # Set state to language selection
        await state.set_state(ClientStates.language_selection)
        return
    
    # Get selected section ID
    section_id = int(callback.data.split(":")[1])
    
    # Save section ID to state
    await state.update_data(section_id=section_id)
    
    # Get procedures for selected section
    procedures = await crud.get_procedures_by_section(session, section_id, lang)
    
    # Initialize empty selected procedures list
    await state.update_data(selected_procedures=[])
    
    # Show procedure selection
    await callback.message.edit_text(
        get_text("select_procedures", lang),
        reply_markup=procedure_keyboard(procedures, [], lang)
    )
    
    # Set state to procedure selection
    await state.set_state(ClientStates.procedure_selection)


# Procedure selection handler
async def procedure_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
    """Handle procedure selection"""
    # Get language from client
    lang = client.lang
    
    # Get data from state
    data = await state.get_data()
    section_id = data.get("section_id")
    selected_procedures = data.get("selected_procedures", [])
    
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Get sections in selected language
        sections = await crud.get_sections(session, lang)
        
        # Show section selection
        await callback.message.edit_text(
            get_text("select_section", lang),
            reply_markup=section_keyboard(sections, lang)
        )
        
        # Set state to section selection
        await state.set_state(ClientStates.section_selection)
        return
    
    # Check if next button was pressed
    if callback.data.startswith("next:"):
        # Check if any procedures are selected
        if not selected_procedures:
            await callback.answer(get_text("no_procedures_selected", lang), show_alert=True)
            return
        
        # Show master or time selection
        await callback.message.edit_text(
            get_text("select_master_or_time", lang),
            reply_markup=master_or_time_keyboard(lang)
        )
        
        # Set state to master or time selection
        await state.set_state(ClientStates.master_or_time_selection)
        return
    
    # Get selected procedure ID
    procedure_id = int(callback.data.split(":")[1])
    
    # Toggle procedure selection
    if procedure_id in selected_procedures:
        selected_procedures.remove(procedure_id)
    else:
        selected_procedures.append(procedure_id)
    
    # Save updated selected procedures to state
    await state.update_data(selected_procedures=selected_procedures)
    
    # Get procedures for selected section
    procedures = await crud.get_procedures_by_section(session, section_id, lang)
    
    # Show updated procedure selection
    await callback.message.edit_text(
        get_text("select_procedures", lang),
        reply_markup=procedure_keyboard(procedures, selected_procedures, lang)
    )


# Master or time selection handler
async def master_or_time_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
    """Handle master or time selection"""
    # Get language from client
    lang = client.lang
    
    # Get data from state
    data = await state.get_data()
    section_id = data.get("section_id")
    selected_procedures = data.get("selected_procedures", [])
    
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Get procedures for selected section
        procedures = await crud.get_procedures_by_section(session, section_id, lang)
        
        # Show procedure selection
        await callback.message.edit_text(
            get_text("select_procedures", lang),
            reply_markup=procedure_keyboard(procedures, selected_procedures, lang)
        )
        
        # Set state to procedure selection
        await state.set_state(ClientStates.procedure_selection)
        return
    
    # Get selection type
    selection_type = callback.data.split(":")[1]
    
    if selection_type == "master":
        # Get masters for selected procedures
        masters = await crud.get_masters_by_procedures(session, selected_procedures)
        
        if not masters:
            await callback.answer(get_text("no_masters_available", lang), show_alert=True)
            return
        
        # Show master selection
        await callback.message.edit_text(
            get_text("select_master", lang),
            reply_markup=master_selection_keyboard(masters, lang)
        )
        
        # Set state to master selection
        await state.set_state(ClientStates.master_selection)
    else:  # time
        # Calculate appointment duration
        duration = await crud.calculate_appointment_duration(
            session, selected_procedures, client.time_coeff, client.is_first_visit
        )
        
        # Save duration to state
        await state.update_data(duration=duration)
        
        # Get available slots for all masters with selected procedures
        # This is a simplified version - in a real app, you'd need to aggregate slots from multiple masters
        masters = await crud.get_masters_by_procedures(session, selected_procedures)
        
        if not masters:
            await callback.answer(get_text("no_masters_available", lang), show_alert=True)
            return
        
        # Get slots for the first available master
        master_id = masters[0]["id"]
        
        # Save master ID to state
        await state.update_data(master_id=master_id)
        
        # Get current date
        today = datetime.now()
        
        # Get available slots
        slots = await crud.get_available_slots(session, master_id, today, duration)
        
        if not slots:
            await callback.answer(get_text("no_slots_available", lang), show_alert=True)
            return
        
        # Save slots to state
        await state.update_data(slots=slots)
        
        # Show time selection
        await callback.message.edit_text(
            get_text("select_time", lang),
            reply_markup=time_selection_keyboard(slots, 0, 1, lang)
        )
        
        # Set state to time selection
        await state.set_state(ClientStates.time_selection)


# Master selection handler
async def master_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
    """Handle master selection"""
    # Get language from client
    lang = client.lang
    
    # Get data from state
    data = await state.get_data()
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
    master_id = int(callback.data.split(":")[1])
    
    # Save master ID to state
    await state.update_data(master_id=master_id)
    
    # Calculate appointment duration
    duration = await crud.calculate_appointment_duration(
        session, selected_procedures, client.time_coeff, client.is_first_visit
    )
    
    # Save duration to state
    await state.update_data(duration=duration)
    
    # Get current date
    today = datetime.now()
    
    # Get available slots
    slots = await crud.get_available_slots(session, master_id, today, duration)
    
    if not slots:
        await callback.answer(get_text("no_slots_available", lang), show_alert=True)
        return
    
    # Save slots to state
    await state.update_data(slots=slots)
    
    # Show time selection
    await callback.message.edit_text(
        get_text("select_time", lang),
        reply_markup=time_selection_keyboard(slots, 0, 1, lang)
    )
    
    # Set state to time selection
    await state.set_state(ClientStates.time_selection)


# Time selection handler
async def time_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
    """Handle time selection"""
    # Get language from client
    lang = client.lang
    
    # Get data from state
    data = await state.get_data()
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
        # In a real app, you'd get this from the database
        # This is a simplified version
        procedure = await session.get(Procedure, procedure_id)
        procedures.append({
            "id": procedure.id,
            "name": procedure.name,
            "base_price": procedure.base_price,
            "discount": procedure.discount
        })
        total_price += procedure.base_price * (1 - procedure.discount / 100)
    
    # Get master details
    master = await session.get(Master, master_id)
    
    # Format appointment details
    details = format_appointment_details(
        {"start_time": selected_time},
        procedures,
        {"name": master.name},
        lang
    )
    
    # Show appointment confirmation
    await callback.message.edit_text(
        get_text("appointment_confirmation", lang, details=details, total_price=total_price),
        reply_markup=confirmation_keyboard(lang)
    )
    
    # Set state to appointment confirmation
    await state.set_state(ClientStates.appointment_confirmation)


# Appointment confirmation handler
async def appointment_confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
    """Handle appointment confirmation"""
    # Get language from client
    lang = client.lang
    
    # Get data from state
    data = await state.get_data()
    master_id = data.get("master_id")
    selected_procedures = data.get("selected_procedures", [])
    selected_time = data.get("selected_time")
    duration = data.get("duration", 60)  # Default to 60 minutes if not set
    
    # Check if confirmed or canceled
    confirmation = callback.data.split(":")[1]
    
    if confirmation == "no":
        # Show cancellation message
        await callback.message.edit_text(
            get_text("appointment_canceled", lang)
        )
        
        # Reset state
        await state.clear()
        
        # Restart the conversation
        await cmd_start(callback.message, state, session, client)
        return
    
    # Calculate end time
    end_time = selected_time + timedelta(minutes=duration)
    
    # Create appointment
    appointment_data = {
        "client_id": client.id,
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
        get_text("appointment_confirmed", lang, date=date_str, time=time_str)
    )
    
    # Reset state
    await state.clear()


# My appointments command handler
async def cmd_my_appointments(message: Message, state: FSMContext, session: AsyncSession, client: Optional[Any] = None):
    """Handle /my_appointments command"""
    # Check if client exists
    if not client:
        # Show language selection
        await message.answer(
            get_text("welcome"),
            reply_markup=language_keyboard()
        )
        
        # Set state to language selection
        await state.set_state(ClientStates.language_selection)
        return
    
    # Get language from client
    lang = client.lang
    
    # Get active appointments
    appointments = await crud.get_client_appointments(session, client.id, "active")
    
    if not appointments:
        await message.answer(get_text("no_appointments", lang))
        return
    
    # Show appointments
    await message.answer(
        get_text("my_appointments", lang),
        reply_markup=my_appointments_keyboard(appointments, lang)
    )
    
    # Set state to my appointments
    await state.set_state(ClientStates.my_appointments)


# Appointment details handler
async def appointment_details(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
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
async def cancel_appointment(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
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
async def cancel_appointment_confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession, client: Any):
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
    # Command handlers
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_my_appointments, Command(commands=["my_appointments"]))
    
    # State handlers
    dp.callback_query.register(language_selection, ClientStates.language_selection)
    dp.message.register(registration_name, ClientStates.registration_name)
    dp.message.register(registration_phone, ClientStates.registration_phone)
    dp.callback_query.register(section_selection, ClientStates.section_selection)
    dp.callback_query.register(procedure_selection, ClientStates.procedure_selection)
    dp.callback_query.register(master_or_time_selection, ClientStates.master_or_time_selection)
    dp.callback_query.register(master_selection, ClientStates.master_selection)
    dp.callback_query.register(time_selection, ClientStates.time_selection)
    dp.callback_query.register(appointment_confirmation, ClientStates.appointment_confirmation)
    dp.callback_query.register(appointment_details, ClientStates.my_appointments, F.data.startswith("appointment:"))
    dp.callback_query.register(cancel_appointment, ClientStates.appointment_details, F.data.startswith("cancel:"))
    dp.callback_query.register(cancel_appointment_confirmation, ClientStates.cancel_appointment)
