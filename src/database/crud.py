from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union

from .models import (
    Client, Section, SectionTranslation, Procedure, ProcedureTranslation,
    Master, MasterProcedure, Workplace, WorkSlot, Appointment, Admin, AdminLog,
    AppointmentStatus
)


# Client CRUD operations
async def create_client(db: AsyncSession, client_data: Dict[str, Any]) -> Client:
    client = Client(**client_data)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def get_client_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[Client]:
    result = await db.execute(select(Client).where(Client.telegram_id == telegram_id))
    return result.scalars().first()


async def update_client(db: AsyncSession, client_id: int, client_data: Dict[str, Any]) -> Optional[Client]:
    await db.execute(
        update(Client).where(Client.id == client_id).values(**client_data)
    )
    await db.commit()
    result = await db.execute(select(Client).where(Client.id == client_id))
    return result.scalars().first()


# Section CRUD operations
async def create_section(db: AsyncSession, section_data: Dict[str, Any], translations: List[Dict[str, Any]]) -> Section:
    section = Section(**section_data)
    db.add(section)
    await db.flush()
    
    for translation in translations:
        translation["section_id"] = section.id
        section_translation = SectionTranslation(**translation)
        db.add(section_translation)
    
    await db.commit()
    await db.refresh(section)
    return section


async def get_sections(db: AsyncSession, lang: str = "UKR") -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Section, SectionTranslation)
        .join(SectionTranslation, Section.id == SectionTranslation.section_id)
        .where(SectionTranslation.lang == lang)
    )
    
    sections = []
    for section, translation in result.all():
        section_dict = {
            "id": section.id,
            "name": translation.name
        }
        sections.append(section_dict)
    
    return sections


# Procedure CRUD operations
async def create_procedure(db: AsyncSession, procedure_data: Dict[str, Any], translations: List[Dict[str, Any]]) -> Procedure:
    procedure = Procedure(**procedure_data)
    db.add(procedure)
    await db.flush()
    
    for translation in translations:
        translation["procedure_id"] = procedure.id
        procedure_translation = ProcedureTranslation(**translation)
        db.add(procedure_translation)
    
    await db.commit()
    await db.refresh(procedure)
    return procedure


async def get_procedures_by_section(db: AsyncSession, section_id: int, lang: str = "UKR") -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Procedure, ProcedureTranslation)
        .join(ProcedureTranslation, Procedure.id == ProcedureTranslation.procedure_id)
        .where(and_(Procedure.section_id == section_id, ProcedureTranslation.lang == lang))
    )
    
    procedures = []
    for procedure, translation in result.all():
        procedure_dict = {
            "id": procedure.id,
            "name": translation.name,
            "description": translation.description,
            "duration": procedure.duration,
            "base_price": procedure.base_price,
            "discount": procedure.discount
        }
        procedures.append(procedure_dict)
    
    return procedures


# Master CRUD operations
async def create_master(db: AsyncSession, master_data: Dict[str, Any]) -> Master:
    master = Master(**master_data)
    db.add(master)
    await db.commit()
    await db.refresh(master)
    return master


async def get_masters(db: AsyncSession) -> List[Master]:
    result = await db.execute(select(Master))
    return result.scalars().all()


async def assign_procedure_to_master(db: AsyncSession, master_id: int, procedure_id: int) -> MasterProcedure:
    master_procedure = MasterProcedure(master_id=master_id, procedure_id=procedure_id)
    db.add(master_procedure)
    await db.commit()
    await db.refresh(master_procedure)
    return master_procedure


async def get_masters_by_procedures(db: AsyncSession, procedure_ids: List[int]) -> List[Master]:
    result = await db.execute(
        select(Master)
        .join(MasterProcedure, Master.id == MasterProcedure.master_id)
        .where(MasterProcedure.procedure_id.in_(procedure_ids))
        .group_by(Master.id)
        .having(func.count(MasterProcedure.procedure_id) == len(procedure_ids))
    )
    return result.scalars().all()


# Workplace CRUD operations
async def create_workplace(db: AsyncSession, workplace_data: Dict[str, Any]) -> Workplace:
    workplace = Workplace(**workplace_data)
    db.add(workplace)
    await db.commit()
    await db.refresh(workplace)
    return workplace


async def get_workplaces(db: AsyncSession) -> List[Workplace]:
    result = await db.execute(select(Workplace))
    return result.scalars().all()


# WorkSlot CRUD operations
async def create_work_slot(db: AsyncSession, work_slot_data: Dict[str, Any]) -> WorkSlot:
    work_slot = WorkSlot(**work_slot_data)
    db.add(work_slot)
    await db.commit()
    await db.refresh(work_slot)
    return work_slot


async def get_master_work_slots(db: AsyncSession, master_id: int, start_date: datetime, end_date: datetime) -> List[WorkSlot]:
    result = await db.execute(
        select(WorkSlot)
        .where(
            and_(
                WorkSlot.master_id == master_id,
                WorkSlot.start_time >= start_date,
                WorkSlot.end_time <= end_date
            )
        )
    )
    return result.scalars().all()


# Appointment CRUD operations
async def create_appointment(db: AsyncSession, appointment_data: Dict[str, Any]) -> Appointment:
    appointment = Appointment(**appointment_data)
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


async def get_client_appointments(db: AsyncSession, client_id: int, status: Optional[AppointmentStatus] = None) -> List[Appointment]:
    query = select(Appointment).where(Appointment.client_id == client_id)
    
    if status:
        query = query.where(Appointment.status == status)
    
    result = await db.execute(query.order_by(Appointment.start_time))
    return result.scalars().all()


async def get_master_appointments(db: AsyncSession, master_id: int, start_date: datetime, end_date: datetime) -> List[Appointment]:
    result = await db.execute(
        select(Appointment)
        .where(
            and_(
                Appointment.master_id == master_id,
                Appointment.start_time >= start_date,
                Appointment.end_time <= end_date,
                Appointment.status == AppointmentStatus.active
            )
        )
    )
    return result.scalars().all()


async def update_appointment_status(db: AsyncSession, appointment_id: int, status: AppointmentStatus) -> Optional[Appointment]:
    await db.execute(
        update(Appointment)
        .where(Appointment.id == appointment_id)
        .values(status=status)
    )
    await db.commit()
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    return result.scalars().first()


# Admin CRUD operations
async def create_admin(db: AsyncSession, admin_data: Dict[str, Any]) -> Admin:
    admin = Admin(**admin_data)
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def get_admin_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[Admin]:
    result = await db.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    return result.scalars().first()


async def log_admin_action(db: AsyncSession, admin_id: int, action: str, details: Optional[str] = None) -> AdminLog:
    log = AdminLog(admin_id=admin_id, action=action, details=details)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# Slot generation and availability
async def calculate_appointment_duration(
    db: AsyncSession, 
    procedure_ids: List[int], 
    client_time_coeff: float = 1.0, 
    is_first_visit: bool = False
) -> int:
    """Calculate the total duration of an appointment in minutes"""
    result = await db.execute(
        select(func.sum(Procedure.duration))
        .where(Procedure.id.in_(procedure_ids))
    )
    base_duration = result.scalar() or 0
    
    # Apply client's time coefficient
    total_duration = base_duration * client_time_coeff
    
    # Add consultation time for first visit
    if is_first_visit:
        total_duration += 15
    
    # Add break time
    total_duration += 15
    
    # Round up to nearest 15 minutes
    return int((total_duration + 14) // 15 * 15)


async def get_available_slots(
    db: AsyncSession,
    master_id: int,
    date: datetime,
    duration_minutes: int
) -> List[datetime]:
    """
    Generate available time slots for a specific master on a specific date
    based on their work schedule and existing appointments
    """
    # Get master's work slots for the day
    start_of_day = datetime.combine(date.date(), datetime.min.time())
    end_of_day = datetime.combine(date.date(), datetime.max.time())
    
    work_slots = await get_master_work_slots(db, master_id, start_of_day, end_of_day)
    if not work_slots:
        return []
    
    # Get master's appointments for the day
    appointments = await get_master_appointments(db, master_id, start_of_day, end_of_day)
    
    available_slots = []
    
    for work_slot in work_slots:
        current_time = work_slot.start_time
        
        # Generate slots with 1-hour intervals initially
        while current_time + timedelta(minutes=duration_minutes) <= work_slot.end_time:
            # Check if the slot overlaps with any existing appointment
            is_available = True
            for appointment in appointments:
                if (current_time < appointment.end_time and 
                    current_time + timedelta(minutes=duration_minutes) > appointment.start_time):
                    is_available = False
                    # Jump to the end of this appointment
                    current_time = appointment.end_time + timedelta(minutes=15)
                    # Round to nearest 15 minutes
                    minutes = current_time.minute
                    current_time = current_time.replace(
                        minute=(minutes // 15) * 15,
                        second=0,
                        microsecond=0
                    )
                    break
            
            if is_available:
                # Only add slot if there's at least 1 hour left in the work day
                if work_slot.end_time - current_time >= timedelta(hours=1):
                    available_slots.append(current_time)
                
                # Move to next slot (1 hour later)
                current_time += timedelta(hours=1)
            
    # Return only the 5 closest slots
    return available_slots[:5]
