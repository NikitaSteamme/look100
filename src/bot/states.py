from aiogram.fsm.state import State, StatesGroup


class ClientStates(StatesGroup):
    """States for client flow"""
    language_selection = State()
    registration_name = State()
    registration_phone = State()
    section_selection = State()
    procedure_selection = State()
    master_or_time_selection = State()
    master_selection = State()
    time_selection = State()
    appointment_confirmation = State()
    my_appointments = State()
    appointment_details = State()
    cancel_appointment = State()


class AdminStates(StatesGroup):
    """States for admin flow"""
    main_menu = State()
    
    # Workplace management
    workplace_management = State()
    workplace_create = State()
    workplace_edit = State()
    workplace_edit_name = State()
    workplace_delete = State()
    
    # Work slot management
    workslot_management = State()
    workslot_create_select_master = State()
    workslot_create_select_workplace = State()
    workslot_create_select_date = State()
    workslot_create_select_start_time = State()
    workslot_create_select_end_time = State()
    workslot_create_select_time = State()
    workslot_delete = State()
    
    # Appointment management
    appointment_management = State()
    appointment_view_by_date = State()
    appointment_delete = State()
    appointment_details = State()
    
    # Manual appointment creation
    manual_appointment_search_client = State()
    manual_appointment_select_client = State()
    manual_appointment_select_section = State()
    manual_appointment_select_procedures = State()
    manual_appointment_select_master = State()
    manual_appointment_select_time = State()
    manual_appointment_confirm = State()
