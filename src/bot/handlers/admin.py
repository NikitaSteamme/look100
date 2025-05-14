from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Any, Optional, List, Dict

from src.bot.states import AdminStates
from src.bot.keyboards import (
    admin_main_keyboard, admin_workplace_keyboard,
    admin_workplace_actions_keyboard, admin_master_selection_keyboard,
    admin_date_selection_keyboard, admin_time_selection_keyboard,
    admin_appointments_keyboard, admin_appointment_actions_keyboard,
    admin_client_search_keyboard
)
from src.database import crud
from src.utils.translations import get_text
import os


# List of admin Telegram IDs from environment variable
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]


# Admin command handler
async def cmd_admin(message: Message, state: FSMContext, session: AsyncSession, admin: Optional[Any] = None):
    """Handle /admin command"""
    # Check if user is admin
    if message.from_user.id not in ADMIN_IDS and not admin:
        # Ignore if not admin
        return
    
    # Reset state
    await state.clear()
    
    # Show admin main menu
    await message.answer(
        "Вітаємо в адміністративній панелі! Оберіть опцію:",
        reply_markup=admin_main_keyboard()
    )
    
    # Set state to admin main menu
    await state.set_state(AdminStates.main_menu)


# Admin main menu handler
async def admin_main_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle admin main menu"""
    # Get selected option
    option = callback.data.split(":")[1]
    
    if option == "workplaces":
        # Get workplaces
        workplaces = await crud.get_workplaces(session)
        
        # Show workplace management
        await callback.message.edit_text(
            "Управління робочими місцями:",
            reply_markup=admin_workplace_keyboard(workplaces)
        )
        
        # Set state to workplace management
        await state.set_state(AdminStates.workplace_management)
    
    elif option == "workslots":
        # Get masters
        masters = await crud.get_masters(session)
        
        # Show master selection for work slot management
        await callback.message.edit_text(
            "Оберіть майстра для управління робочим часом:",
            reply_markup=admin_master_selection_keyboard(masters)
        )
        
        # Set state to workslot management
        await state.set_state(AdminStates.workslot_create_select_master)
    
    elif option == "appointments":
        # Show date selection for appointment management
        await callback.message.edit_text(
            "Оберіть дату для перегляду записів:",
            reply_markup=admin_date_selection_keyboard()
        )
        
        # Set state to appointment view by date
        await state.set_state(AdminStates.appointment_view_by_date)
    
    elif option == "create_appointment":
        # Show client search prompt
        await callback.message.edit_text(
            "Введіть ім'я або номер телефону клієнта для пошуку:"
        )
        
        # Set state to manual appointment search client
        await state.set_state(AdminStates.manual_appointment_search_client)


# Workplace management handlers
async def workplace_management(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle workplace management"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show admin main menu
        await callback.message.edit_text(
            "Вітаємо в адміністративній панелі! Оберіть опцію:",
            reply_markup=admin_main_keyboard()
        )
        
        # Set state to admin main menu
        await state.set_state(AdminStates.main_menu)
        return
    
    # Check if create button was pressed
    if callback.data == "workplace:create":
        # Show workplace create prompt
        await callback.message.edit_text(
            "Введіть назву нового робочого місця:"
        )
        
        # Set state to workplace create
        await state.set_state(AdminStates.workplace_create)
        return
    
    # Get selected workplace ID
    workplace_id = int(callback.data.split(":")[1])
    
    # Save workplace ID to state
    await state.update_data(workplace_id=workplace_id)
    
    # Get workplace details
    workplace = await session.get(Workplace, workplace_id)
    
    # Show workplace actions
    await callback.message.edit_text(
        f"Робоче місце: {workplace.name}\n\nОберіть дію:",
        reply_markup=admin_workplace_actions_keyboard(workplace_id)
    )
    
    # Set state to workplace edit
    await state.set_state(AdminStates.workplace_edit)


async def workplace_create(message: Message, state: FSMContext, session: AsyncSession):
    """Handle workplace creation"""
    # Create workplace
    workplace_data = {
        "name": message.text
    }
    
    workplace = await crud.create_workplace(session, workplace_data)
    
    # Get all workplaces
    workplaces = await crud.get_workplaces(session)
    
    # Show workplace management
    await message.answer(
        f"Робоче місце '{workplace.name}' створено!\n\nУправління робочими місцями:",
        reply_markup=admin_workplace_keyboard(workplaces)
    )
    
    # Set state to workplace management
    await state.set_state(AdminStates.workplace_management)


async def workplace_edit(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle workplace edit"""
    # Get data from state
    data = await state.get_data()
    workplace_id = data.get("workplace_id")
    
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Get workplaces
        workplaces = await crud.get_workplaces(session)
        
        # Show workplace management
        await callback.message.edit_text(
            "Управління робочими місцями:",
            reply_markup=admin_workplace_keyboard(workplaces)
        )
        
        # Set state to workplace management
        await state.set_state(AdminStates.workplace_management)
        return
    
    # Get action
    action = callback.data.split(":")[0]
    
    if action == "workplace_edit":
        # Show workplace edit prompt
        await callback.message.edit_text(
            "Введіть нову назву робочого місця:"
        )
        
        # Set state to workplace edit name
        await state.set_state(AdminStates.workplace_edit_name)
    
    elif action == "workplace_delete":
        # Delete workplace
        await session.delete(Workplace, workplace_id)
        await session.commit()
        
        # Get workplaces
        workplaces = await crud.get_workplaces(session)
        
        # Show workplace management
        await callback.message.edit_text(
            "Робоче місце видалено!\n\nУправління робочими місцями:",
            reply_markup=admin_workplace_keyboard(workplaces)
        )
        
        # Set state to workplace management
        await state.set_state(AdminStates.workplace_management)


async def workplace_edit_name(message: Message, state: FSMContext, session: AsyncSession):
    """Handle workplace name edit"""
    # Get data from state
    data = await state.get_data()
    workplace_id = data.get("workplace_id")
    
    # Update workplace name
    await crud.update_workplace(session, workplace_id, {"name": message.text})
    
    # Get workplaces
    workplaces = await crud.get_workplaces(session)
    
    # Show workplace management
    await message.answer(
        f"Назву робочого місця змінено на '{message.text}'!\n\nУправління робочими місцями:",
        reply_markup=admin_workplace_keyboard(workplaces)
    )
    
    # Set state to workplace management
    await state.set_state(AdminStates.workplace_management)


# Work slot management handlers
async def workslot_select_master(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle master selection for work slot"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show admin main menu
        await callback.message.edit_text(
            "Вітаємо в адміністративній панелі! Оберіть опцію:",
            reply_markup=admin_main_keyboard()
        )
        
        # Set state to admin main menu
        await state.set_state(AdminStates.main_menu)
        return
    
    # Get selected master ID
    master_id = int(callback.data.split(":")[1])
    
    # Save master ID to state
    await state.update_data(master_id=master_id)
    
    # Get workplaces
    workplaces = await crud.get_workplaces(session)
    
    # Show workplace selection
    await callback.message.edit_text(
        "Оберіть робоче місце:",
        reply_markup=admin_workplace_keyboard(workplaces)
    )
    
    # Set state to workslot select workplace
    await state.set_state(AdminStates.workslot_create_select_workplace)


async def workslot_select_workplace(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle workplace selection for work slot"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Get masters
        masters = await crud.get_masters(session)
        
        # Show master selection
        await callback.message.edit_text(
            "Оберіть майстра для управління робочим часом:",
            reply_markup=admin_master_selection_keyboard(masters)
        )
        
        # Set state to workslot select master
        await state.set_state(AdminStates.workslot_create_select_master)
        return
    
    # Check if create button was pressed
    if callback.data == "workplace:create":
        # Show workplace create prompt
        await callback.message.edit_text(
            "Введіть назву нового робочого місця:"
        )
        
        # Set state to workplace create from workslot
        await state.set_state(AdminStates.workplace_create_from_workslot)
        return
    
    # Get selected workplace ID
    workplace_id = int(callback.data.split(":")[1])
    
    # Save workplace ID to state
    await state.update_data(workplace_id=workplace_id)
    
    # Show date selection
    await callback.message.edit_text(
        "Оберіть дату:",
        reply_markup=admin_date_selection_keyboard()
    )
    
    # Set state to workslot select date
    await state.set_state(AdminStates.workslot_create_select_date)


async def workslot_select_date(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle date selection for work slot"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Get workplaces
        workplaces = await crud.get_workplaces(session)
        
        # Show workplace selection
        await callback.message.edit_text(
            "Оберіть робоче місце:",
            reply_markup=admin_workplace_keyboard(workplaces)
        )
        
        # Set state to workslot select workplace
        await state.set_state(AdminStates.workslot_create_select_workplace)
        return
    
    # Get selected date
    date_str = callback.data.split(":")[1]
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Save date to state
    await state.update_data(date=date)
    
    # Show time selection
    await callback.message.edit_text(
        "Оберіть час початку роботи:",
        reply_markup=admin_time_selection_keyboard()
    )
    
    # Set state to workslot select start time
    await state.set_state(AdminStates.workslot_create_select_start_time)


async def workslot_select_start_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle start time selection for work slot"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show date selection
        await callback.message.edit_text(
            "Оберіть дату:",
            reply_markup=admin_date_selection_keyboard()
        )
        
        # Set state to workslot select date
        await state.set_state(AdminStates.workslot_create_select_date)
        return
    
    # Get selected time
    time_str = callback.data.split(":")[1]
    hour, minute = map(int, time_str.split(":"))
    
    # Get date from state
    data = await state.get_data()
    date = data.get("date")
    
    # Create start time
    start_time = date.replace(hour=hour, minute=minute)
    
    # Save start time to state
    await state.update_data(start_time=start_time)
    
    # Show end time selection
    await callback.message.edit_text(
        "Оберіть час закінчення роботи:",
        reply_markup=admin_time_selection_keyboard(hour)
    )
    
    # Set state to workslot select end time
    await state.set_state(AdminStates.workslot_create_select_end_time)


async def workslot_select_end_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle end time selection for work slot"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show start time selection
        await callback.message.edit_text(
            "Оберіть час початку роботи:",
            reply_markup=admin_time_selection_keyboard()
        )
        
        # Set state to workslot select start time
        await state.set_state(AdminStates.workslot_create_select_start_time)
        return
    
    # Get selected time
    time_str = callback.data.split(":")[1]
    hour, minute = map(int, time_str.split(":"))
    
    # Get data from state
    data = await state.get_data()
    date = data.get("date")
    master_id = data.get("master_id")
    workplace_id = data.get("workplace_id")
    start_time = data.get("start_time")
    
    # Create end time
    end_time = date.replace(hour=hour, minute=minute)
    
    # Check if end time is after start time
    if end_time <= start_time:
        await callback.answer("Час закінчення має бути пізніше часу початку!", show_alert=True)
        return
    
    # Create work slot
    work_slot_data = {
        "master_id": master_id,
        "workplace_id": workplace_id,
        "date": date,
        "start_time": start_time,
        "end_time": end_time
    }
    
    work_slot = await crud.create_work_slot(session, work_slot_data)
    
    # Show success message
    await callback.message.edit_text(
        f"Робочий час створено!\n\n"
        f"Дата: {date.strftime('%d.%m.%Y')}\n"
        f"Час: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n\n"
        f"Бажаєте створити ще один робочий час?",
        reply_markup=admin_workslot_continue_keyboard()
    )
    
    # Set state to workslot continue
    await state.set_state(AdminStates.workslot_continue)


# Appointment management handlers
async def appointment_view_by_date(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle appointment view by date"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show admin main menu
        await callback.message.edit_text(
            "Вітаємо в адміністративній панелі! Оберіть опцію:",
            reply_markup=admin_main_keyboard()
        )
        
        # Set state to admin main menu
        await state.set_state(AdminStates.main_menu)
        return
    
    # Get selected date
    date_str = callback.data.split(":")[1]
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Save date to state
    await state.update_data(date=date)
    
    # Get appointments for the date
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    appointments = await crud.get_appointments_by_date_range(session, start_of_day, end_of_day)
    
    if not appointments:
        await callback.message.edit_text(
            f"Немає записів на {date.strftime('%d.%m.%Y')}.\n\n"
            f"Оберіть іншу дату:",
            reply_markup=admin_date_selection_keyboard()
        )
        return
    
    # Show appointments
    await callback.message.edit_text(
        f"Записи на {date.strftime('%d.%m.%Y')}:",
        reply_markup=admin_appointments_keyboard(appointments)
    )
    
    # Set state to appointment management
    await state.set_state(AdminStates.appointment_management)


async def appointment_management(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle appointment management"""
    # Check if back button was pressed
    if callback.data.startswith("back:"):
        # Show date selection
        await callback.message.edit_text(
            "Оберіть дату для перегляду записів:",
            reply_markup=admin_date_selection_keyboard()
        )
        
        # Set state to appointment view by date
        await state.set_state(AdminStates.appointment_view_by_date)
        return
    
    # Check if page navigation
    if callback.data.startswith("admin_page:"):
        # Get page number
        page = int(callback.data.split(":")[1])
        
        # Get date from state
        data = await state.get_data()
        date = data.get("date")
        
        # Get appointments for the date
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        appointments = await crud.get_appointments_by_date_range(session, start_of_day, end_of_day)
        
        # Show appointments for the page
        await callback.message.edit_text(
            f"Записи на {date.strftime('%d.%m.%Y')}:",
            reply_markup=admin_appointments_keyboard(appointments, page)
        )
        return
    
    # Get selected appointment ID
    appointment_id = int(callback.data.split(":")[1])
    
    # Save appointment ID to state
    await state.update_data(appointment_id=appointment_id)
    
    # Get appointment details
    appointment = await session.get(Appointment, appointment_id)
    client = await session.get(Client, appointment.client_id)
    master = await session.get(Master, appointment.master_id)
    
    # Get procedures details
    procedures = []
    for procedure_id in appointment.procedures:
        procedure = await session.get(Procedure, procedure_id)
        procedures.append({
            "id": procedure.id,
            "name": procedure.name,
            "base_price": procedure.base_price,
            "discount": procedure.discount
        })
    
    # Format appointment details
    details = f"Клієнт: {client.name}\n"
    details += f"Телефон: {client.phone}\n"
    details += f"Майстер: {master.name}\n"
    details += f"Дата: {appointment.start_time.strftime('%d.%m.%Y')}\n"
    details += f"Час: {appointment.start_time.strftime('%H:%M')} - {appointment.end_time.strftime('%H:%M')}\n\n"
    details += "Процедури:\n"
    
    total_price = 0
    for procedure in procedures:
        price = procedure["base_price"] * (1 - procedure["discount"] / 100)
        total_price += price
        details += f"- {procedure['name']} ({price:.2f}₴)\n"
    
    details += f"\nЗагальна вартість: {total_price:.2f}₴"
    
    # Show appointment details
    await callback.message.edit_text(
        details,
        reply_markup=admin_appointment_actions_keyboard(appointment_id)
    )
    
    # Set state to appointment details
    await state.set_state(AdminStates.appointment_details)


async def appointment_delete(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle appointment deletion"""
    # Get data from state
    data = await state.get_data()
    appointment_id = data.get("appointment_id")
    date = data.get("date")
    
    # Update appointment status to canceled
    await crud.update_appointment_status(session, appointment_id, "canceled")
    
    # Get appointments for the date
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    appointments = await crud.get_appointments_by_date_range(session, start_of_day, end_of_day)
    
    if not appointments:
        await callback.message.edit_text(
            f"Немає записів на {date.strftime('%d.%m.%Y')}.\n\n"
            f"Оберіть іншу дату:",
            reply_markup=admin_date_selection_keyboard()
        )
        
        # Set state to appointment view by date
        await state.set_state(AdminStates.appointment_view_by_date)
        return
    
    # Show appointments
    await callback.message.edit_text(
        f"Запис скасовано!\n\nЗаписи на {date.strftime('%d.%m.%Y')}:",
        reply_markup=admin_appointments_keyboard(appointments)
    )
    
    # Set state to appointment management
    await state.set_state(AdminStates.appointment_management)


# Manual appointment creation handlers
async def manual_appointment_search_client(message: Message, state: FSMContext, session: AsyncSession):
    """Handle client search for manual appointment"""
    # Search for clients by name or phone
    clients = await crud.search_clients(session, message.text)
    
    if not clients:
        await message.answer(
            "Клієнтів не знайдено. Спробуйте інший пошуковий запит або створіть нового клієнта."
        )
        return
    
    # Show client search results
    await message.answer(
        "Знайдені клієнти:",
        reply_markup=admin_client_search_keyboard(clients)
    )
    
    # Set state to manual appointment select client
    await state.set_state(AdminStates.manual_appointment_select_client)


def register_admin_handlers(dp: Dispatcher):
    """Register admin handlers"""
    # Command handlers
    dp.message.register(cmd_admin, Command(commands=["admin"]))
    
    # State handlers
    dp.callback_query.register(admin_main_menu, AdminStates.main_menu, F.data.startswith("admin:"))
    
    # Workplace management
    dp.callback_query.register(workplace_management, AdminStates.workplace_management)
    dp.message.register(workplace_create, AdminStates.workplace_create)
    dp.callback_query.register(workplace_edit, AdminStates.workplace_edit)
    dp.message.register(workplace_edit_name, AdminStates.workplace_edit_name)
    
    # Work slot management
    dp.callback_query.register(workslot_select_master, AdminStates.workslot_create_select_master)
    dp.callback_query.register(workslot_select_workplace, AdminStates.workslot_create_select_workplace)
    dp.callback_query.register(workslot_select_date, AdminStates.workslot_create_select_date)
    dp.callback_query.register(workslot_select_start_time, AdminStates.workslot_create_select_start_time)
    dp.callback_query.register(workslot_select_end_time, AdminStates.workslot_create_select_end_time)
    
    # Appointment management
    dp.callback_query.register(appointment_view_by_date, AdminStates.appointment_view_by_date)
    dp.callback_query.register(appointment_management, AdminStates.appointment_management)
    dp.callback_query.register(appointment_delete, AdminStates.appointment_details, F.data.startswith("admin_delete:"))
    
    # Manual appointment creation
    dp.message.register(manual_appointment_search_client, AdminStates.manual_appointment_search_client)
