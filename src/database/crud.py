"""
Оптимизированные CRUD-функции для работы с базой данных
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, update, delete, or_, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta

from .models import (
    Section, SectionTranslation, 
    Procedure, ProcedureTranslation,
    Master, MasterProcedure,
    Client, Appointment, Workplace,
    Admin, AdminLog, WorkSlot,
    AppointmentStatus
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Функции для работы с разделами
async def get_sections(db: AsyncSession, lang: str = "UKR") -> List[Dict[str, Any]]:
    """
    Получение всех разделов с переводами с использованием JOIN
    """
    try:
        # Используем JOIN для оптимизации запроса
        query = (
            select(Section, SectionTranslation)
            .outerjoin(SectionTranslation, Section.id == SectionTranslation.section_id)
        )
        
        result = await db.execute(query)
        sections_data = result.all()
        
        # Группируем результаты по разделам
        sections_dict = {}
        for section, translation in sections_data:
            if section.id not in sections_dict:
                sections_dict[section.id] = {
                    "id": section.id,
                    "translations": []
                }
            
            if translation:
                sections_dict[section.id]["translations"].append({
                    "lang": translation.lang,
                    "name": translation.name,
                    "description": translation.description if hasattr(translation, 'description') else ""
                })
        
        # Формируем итоговый список разделов
        sections = []
        for section_id, section_data in sections_dict.items():
            # Получаем перевод на нужном языке или первый доступный
            name = ""
            for trans in section_data["translations"]:
                if trans["lang"] == lang:
                    name = trans["name"]
                    break
            
            if not name and section_data["translations"]:
                name = section_data["translations"][0]["name"]
            
            section_data["name"] = name
            sections.append(section_data)
        
        return sections
    except SQLAlchemyError as e:
        logger.error(f"Error in get_sections: {e}")
        return []

async def get_section_by_id(db: AsyncSession, section_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение раздела по ID с переводами с использованием JOIN
    """
    try:
        # Используем JOIN для оптимизации запроса
        query = (
            select(Section, SectionTranslation)
            .outerjoin(SectionTranslation, Section.id == SectionTranslation.section_id)
            .where(Section.id == section_id)
        )
        
        result = await db.execute(query)
        section_data = result.all()
        
        if not section_data:
            return None
        
        # Формируем результат
        section = section_data[0][0]
        translations = []
        
        for _, translation in section_data:
            if translation:
                translations.append({
                    "lang": translation.lang,
                    "name": translation.name,
                    "description": translation.description if hasattr(translation, 'description') else ""
                })
        
        # Получаем перевод на украинском языке или первый доступный
        name = ""
        for trans in translations:
            if trans["lang"] == "UKR":
                name = trans["name"]
                break
        
        if not name and translations:
            name = translations[0]["name"]
        
        return {
            "id": section.id,
            "name": name,
            "translations": translations
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in get_section_by_id: {e}")
        return None

async def create_section(db: AsyncSession, section_data: Dict[str, Any], translations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Создание раздела с переводами
    """
    try:
        # Валидация данных
        if not section_data.get("name"):
            logger.error("Section name is required")
            return None
        
        if not translations:
            logger.error("At least one translation is required")
            return None
        
        # Создание раздела
        section = Section(**section_data)
        db.add(section)
        await db.flush()
        
        # Создание переводов
        for translation in translations:
            # Валидация данных перевода
            if not translation.get("lang") or not translation.get("name"):
                logger.warning(f"Invalid translation data: {translation}")
                continue
            
            translation["section_id"] = section.id
            section_translation = SectionTranslation(**translation)
            db.add(section_translation)
        
        await db.commit()
        await db.refresh(section)
        
        # Возвращаем созданный раздел
        return await get_section_by_id(db, section.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in create_section: {e}")
        await db.rollback()
        return None

async def update_section(db: AsyncSession, section_id: int, translations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Обновление раздела и его переводов
    """
    try:
        # Валидация данных
        if not translations:
            logger.error("At least one translation is required")
            return None
        
        # Получение раздела
        section_result = await db.execute(select(Section).where(Section.id == section_id))
        section = section_result.scalar_one_or_none()
        
        if not section:
            logger.error(f"Section with ID {section_id} not found")
            return None
        
        # Обновление имени раздела
        ukr_translation = next((t for t in translations if t.get("lang") == "UKR"), translations[0])
        section.name = ukr_translation.get("name", "")
        
        # Удаление старых переводов
        await db.execute(
            text(f"DELETE FROM section_translation WHERE section_id = {section_id}")
        )
        
        # Создание новых переводов
        for translation in translations:
            # Валидация данных перевода
            if not translation.get("lang") or not translation.get("name"):
                logger.warning(f"Invalid translation data: {translation}")
                continue
            
            translation["section_id"] = section_id
            section_translation = SectionTranslation(**translation)
            db.add(section_translation)
        
        await db.commit()
        
        # Возвращаем обновленный раздел
        return await get_section_by_id(db, section_id)
    except SQLAlchemyError as e:
        logger.error(f"Error in update_section: {e}")
        await db.rollback()
        return None

async def delete_section(db: AsyncSession, section_id: int) -> bool:
    """
    Удаление раздела и всех связанных с ним данных
    """
    try:
        # Получение раздела
        section_result = await db.execute(select(Section).where(Section.id == section_id))
        section = section_result.scalar_one_or_none()
        
        if not section:
            logger.error(f"Section with ID {section_id} not found")
            return False
        
        # Удаление связанных данных с использованием каскадного удаления
        await db.execute(
            text(f"DELETE FROM section WHERE id = {section_id}")
        )
        
        await db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_section: {e}")
        await db.rollback()
        return False

# Функции для работы с процедурами
async def get_procedures(db: AsyncSession, lang: str = "UKR") -> List[Dict[str, Any]]:
    """
    Получение всех процедур с переводами с использованием JOIN
    """
    try:
        # Используем JOIN для оптимизации запроса
        query = (
            select(
                Procedure, 
                ProcedureTranslation,
                Section,
                SectionTranslation
            )
            .outerjoin(ProcedureTranslation, Procedure.id == ProcedureTranslation.procedure_id)
            .outerjoin(Section, Procedure.section_id == Section.id)
            .outerjoin(SectionTranslation, and_(
                Section.id == SectionTranslation.section_id,
                SectionTranslation.lang == lang
            ))
        )
        
        result = await db.execute(query)
        procedures_data = result.all()
        
        # Группируем результаты по процедурам
        procedures_dict = {}
        for procedure, translation, section, section_translation in procedures_data:
            if procedure.id not in procedures_dict:
                procedures_dict[procedure.id] = {
                    "id": procedure.id,
                    "section_id": procedure.section_id,
                    "section_name": section_translation.name if section_translation else "",
                    "duration": procedure.duration,
                    "base_price": procedure.base_price,
                    "discount": procedure.discount,
                    "translations": []
                }
            
            if translation and translation.procedure_id == procedure.id:
                # Проверяем, не добавлен ли уже этот перевод
                translation_exists = False
                for existing_trans in procedures_dict[procedure.id]["translations"]:
                    if existing_trans["lang"] == translation.lang:
                        translation_exists = True
                        break
                
                if not translation_exists:
                    procedures_dict[procedure.id]["translations"].append({
                        "lang": translation.lang,
                        "name": translation.name,
                        "description": translation.description if hasattr(translation, 'description') else ""
                    })
        
        # Формируем итоговый список процедур
        procedures = []
        for procedure_id, procedure_data in procedures_dict.items():
            # Получаем перевод на нужном языке или первый доступный
            name = ""
            description = ""
            for trans in procedure_data["translations"]:
                if trans["lang"] == lang:
                    name = trans["name"]
                    description = trans["description"]
                    break
            
            if not name and procedure_data["translations"]:
                name = procedure_data["translations"][0]["name"]
                description = procedure_data["translations"][0]["description"]
            
            procedure_data["name"] = name
            procedure_data["description"] = description
            procedures.append(procedure_data)
        
        return procedures
    except SQLAlchemyError as e:
        logger.error(f"Error in get_procedures: {e}")
        return []

async def get_procedure_by_id(db: AsyncSession, procedure_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение процедуры по ID с переводами с использованием JOIN
    """
    try:
        # Используем JOIN для оптимизации запроса
        query = (
            select(
                Procedure, 
                ProcedureTranslation,
                Section,
                SectionTranslation
            )
            .outerjoin(ProcedureTranslation, Procedure.id == ProcedureTranslation.procedure_id)
            .outerjoin(Section, Procedure.section_id == Section.id)
            .outerjoin(SectionTranslation, Section.id == SectionTranslation.section_id)
            .where(Procedure.id == procedure_id)
        )
        
        result = await db.execute(query)
        procedure_data = result.all()
        
        if not procedure_data:
            return None
        
        # Формируем результат
        procedure = procedure_data[0][0]
        translations = []
        section_name = ""
        
        for _, translation, _, section_translation in procedure_data:
            if translation:
                # Проверяем, не добавлен ли уже этот перевод
                translation_exists = False
                for existing_trans in translations:
                    if existing_trans["lang"] == translation.lang:
                        translation_exists = True
                        break
                
                if not translation_exists:
                    translations.append({
                        "lang": translation.lang,
                        "name": translation.name,
                        "description": translation.description if hasattr(translation, 'description') else ""
                    })
            
            if section_translation and section_translation.lang == "UKR" and not section_name:
                section_name = section_translation.name
        
        # Получаем перевод на украинском языке или первый доступный
        name = ""
        description = ""
        for trans in translations:
            if trans["lang"] == "UKR":
                name = trans["name"]
                description = trans["description"]
                break
        
        if not name and translations:
            name = translations[0]["name"]
            description = translations[0]["description"]
        
        return {
            "id": procedure.id,
            "section_id": procedure.section_id,
            "section_name": section_name,
            "name": name,
            "description": description,
            "duration": procedure.duration,
            "base_price": procedure.base_price,
            "discount": procedure.discount,
            "translations": translations
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in get_procedure_by_id: {e}")
        return None

async def update_procedure(db: AsyncSession, procedure_id: int, procedure_data: Dict[str, Any], translations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Обновление процедуры и ее переводов
    """
    try:
        # Валидация данных
        if not translations:
            logger.error("At least one translation is required")
            return None
        
        # Получение процедуры
        procedure_result = await db.execute(
            select(Procedure).where(Procedure.id == procedure_id)
        )
        procedure = procedure_result.scalar_one_or_none()
        
        if not procedure:
            logger.error(f"Procedure with ID {procedure_id} not found")
            return None
        
        # Если указан section_id, проверяем существование раздела
        if "section_id" in procedure_data:
            section_result = await db.execute(
                select(Section).where(Section.id == procedure_data["section_id"])
            )
            section = section_result.scalar_one_or_none()
            
            if not section:
                logger.error(f"Section with ID {procedure_data['section_id']} not found")
                return None
        
        # Обновление данных процедуры
        for key, value in procedure_data.items():
            setattr(procedure, key, value)
        
        # Удаление старых переводов
        await db.execute(
            text(f"DELETE FROM procedure_translation WHERE procedure_id = {procedure_id}")
        )
        
        # Создание новых переводов
        for translation in translations:
            # Валидация данных перевода
            if not translation.get("lang") or not translation.get("name"):
                logger.warning(f"Invalid translation data: {translation}")
                continue
            
            translation["procedure_id"] = procedure_id
            procedure_translation = ProcedureTranslation(**translation)
            db.add(procedure_translation)
        
        await db.commit()
        
        # Возвращаем обновленную процедуру
        return await get_procedure_by_id(db, procedure_id)
    except SQLAlchemyError as e:
        logger.error(f"Error in update_procedure: {e}")
        await db.rollback()
        return None

async def delete_procedure(db: AsyncSession, procedure_id: int) -> bool:
    """
    Удаление процедуры и всех связанных с ней данных
    """
    try:
        # Получение процедуры
        procedure_result = await db.execute(
            select(Procedure).where(Procedure.id == procedure_id)
        )
        procedure = procedure_result.scalar_one_or_none()
        
        if not procedure:
            logger.error(f"Procedure with ID {procedure_id} not found")
            return False
        
        # Удаление связанных данных с использованием каскадного удаления
        await db.execute(
            text(f"DELETE FROM procedure WHERE id = {procedure_id}")
        )
        
        await db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_procedure: {e}")
        await db.rollback()
        return False

# Функции для работы с рабочими местами
async def get_workplaces(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Получение всех рабочих мест
    """
    try:
        query = select(Workplace)
        result = await db.execute(query)
        workplaces = result.scalars().all()
        
        return [
            {
                "id": workplace.id,
                "name": workplace.name
            }
            for workplace in workplaces
        ]
    except SQLAlchemyError as e:
        logger.error(f"Error in get_workplaces: {e}")
        return []

async def get_workplace_by_id(db: AsyncSession, workplace_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение рабочего места по ID
    """
    try:
        query = select(Workplace).where(Workplace.id == workplace_id)
        result = await db.execute(query)
        workplace = result.scalars().first()
        
        if not workplace:
            return None
        
        return {
            "id": workplace.id,
            "name": workplace.name
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in get_workplace_by_id: {e}")
        return None

async def create_workplace(db: AsyncSession, workplace_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создание нового рабочего места
    """
    try:
        workplace = Workplace(
            name=workplace_data["name"]
        )
        
        db.add(workplace)
        await db.commit()
        await db.refresh(workplace)
        
        return {
            "id": workplace.id,
            "name": workplace.name
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in create_workplace: {e}")
        await db.rollback()
        return None

async def update_workplace(db: AsyncSession, workplace_id: int, workplace_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обновление рабочего места
    """
    try:
        query = select(Workplace).where(Workplace.id == workplace_id)
        result = await db.execute(query)
        workplace = result.scalars().first()
        
        if not workplace:
            return None
        
        if "name" in workplace_data:
            workplace.name = workplace_data["name"]
        
        await db.commit()
        await db.refresh(workplace)
        
        return {
            "id": workplace.id,
            "name": workplace.name
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in update_workplace: {e}")
        await db.rollback()
        return None

async def create_procedure(db: AsyncSession, procedure_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создание новой процедуры с переводами
    """
    try:
        # Проверка обязательных полей
        required_fields = ["section_id", "duration", "base_price", "translations"]
        for field in required_fields:
            if field not in procedure_data:
                logger.error(f"Required field {field} is missing in procedure_data")
                return None
        
        # Проверка переводов
        translations = procedure_data.get("translations", [])
        if not translations:
            logger.error("At least one translation is required")
            return None
        
        # Проверка обязательных полей в переводах
        for i, translation_data in enumerate(translations):
            if "lang" not in translation_data or "name" not in translation_data:
                logger.error(f"Translation {i} is missing required fields (lang or name)")
                return None
        
        # Создаем процедуру
        procedure = Procedure(
            section_id=procedure_data["section_id"],
            duration=procedure_data["duration"],
            base_price=procedure_data["base_price"],
            discount=procedure_data.get("discount", 0)
        )
        
        db.add(procedure)
        await db.flush()  # Получаем ID процедуры
        
        # Добавляем переводы
        for translation_data in translations:
            translation = ProcedureTranslation(
                procedure_id=procedure.id,
                lang=translation_data["lang"],
                name=translation_data["name"],
                description=translation_data.get("description", "")
            )
            db.add(translation)
        
        await db.commit()
        await db.refresh(procedure)
        
        # Формируем ответ
        result = {
            "id": procedure.id,
            "section_id": procedure.section_id,
            "duration": procedure.duration,
            "base_price": procedure.base_price,
            "discount": procedure.discount,
            "translations": []
        }
        
        # Получаем переводы для ответа
        query = select(ProcedureTranslation).where(ProcedureTranslation.procedure_id == procedure.id)
        translations_result = await db.execute(query)
        translations = translations_result.scalars().all()
        
        # Получаем название раздела
        section_name = ""
        try:
            section_query = select(Section, SectionTranslation).outerjoin(
                SectionTranslation, 
                and_(Section.id == SectionTranslation.section_id, SectionTranslation.lang == "UKR")
            ).where(Section.id == procedure.section_id)
            section_result = await db.execute(section_query)
            section_data = section_result.first()
            if section_data and section_data[1]:
                section_name = section_data[1].name
        except Exception as e:
            logger.error(f"Error getting section name: {e}")
        
        result["section_name"] = section_name
        
        # Добавляем переводы в результат
        for translation in translations:
            result["translations"].append({
                "lang": translation.lang,
                "name": translation.name,
                "description": translation.description
            })
            
        # Добавляем поле name для совместимости с шаблоном
        # Используем украинский перевод или первый доступный
        name = ""
        description = ""
        for trans in result["translations"]:
            if trans["lang"] == "UKR":
                name = trans["name"]
                description = trans["description"]
                break
        
        if not name and result["translations"]:
            name = result["translations"][0]["name"]
            description = result["translations"][0]["description"]
        
        result["name"] = name
        result["description"] = description
        
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error in create_procedure: {e}")
        await db.rollback()
        return None

async def delete_workplace(db: AsyncSession, workplace_id: int) -> bool:
    """
    Удаление рабочего места
    """
    try:
        query = select(Workplace).where(Workplace.id == workplace_id)
        result = await db.execute(query)
        workplace = result.scalars().first()
        
        if not workplace:
            return False
        
        # Проверка на связанные записи
        appointments_query = select(func.count()).select_from(Appointment).where(Appointment.workplace_id == workplace_id)
        appointments_count = await db.scalar(appointments_query)
        
        if appointments_count > 0:
            # Если есть связанные записи, просто деактивируем рабочее место
            workplace.is_active = False
            await db.commit()
            return True
        
        # Если нет связанных записей, удаляем полностью
        await db.delete(workplace)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_workplace: {e}")
        await db.rollback()
        return False

# Функции для работы с рабочими слотами
async def get_work_slots(db: AsyncSession, master_id: Optional[int] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Получение всех рабочих слотов с фильтрацией
    """
    try:
        query = select(WorkSlot)
        
        # Применяем фильтры, если они указаны
        if master_id is not None:
            query = query.where(WorkSlot.master_id == master_id)
        
        if start_date is not None:
            query = query.where(WorkSlot.start_time >= start_date)
        
        if end_date is not None:
            query = query.where(WorkSlot.end_time <= end_date)
        
        # Сортируем по дате и времени начала
        query = query.order_by(WorkSlot.start_time)
        
        result = await db.execute(query)
        work_slots = result.scalars().all()
        
        # Формируем список результатов
        work_slots_list = []
        for slot in work_slots:
            work_slots_list.append({
                "id": slot.id,
                "master_id": slot.master_id,
                "workplace_id": slot.workplace_id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "date": slot.start_time.date()
            })
        
        return work_slots_list
    except SQLAlchemyError as e:
        logger.error(f"Error in get_work_slots: {e}")
        return []

async def get_work_slot_by_id(db: AsyncSession, work_slot_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение рабочего слота по ID
    """
    try:
        query = select(WorkSlot).where(WorkSlot.id == work_slot_id)
        result = await db.execute(query)
        work_slot = result.scalars().first()
        
        if not work_slot:
            return None
        
        return {
            "id": work_slot.id,
            "master_id": work_slot.master_id,
            "workplace_id": work_slot.workplace_id,
            "start_time": work_slot.start_time,
            "end_time": work_slot.end_time,
            "date": work_slot.start_time.date()
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in get_work_slot_by_id: {e}")
        return None

async def create_work_slot(db: AsyncSession, work_slot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создание нового рабочего слота
    """
    try:
        # Подробное логирование входных данных
        logger.info(f"Creating work slot with data: {work_slot_data}")
        
        # Проверка обязательных полей
        required_fields = ["master_id", "workplace_id", "start_time", "end_time"]
        for field in required_fields:
            if field not in work_slot_data:
                logger.error(f"Required field {field} is missing in work_slot_data")
                return None
        
        # Преобразуем строки в даты, если необходимо
        start_time = work_slot_data["start_time"]
        end_time = work_slot_data["end_time"]
        
        logger.info(f"Original start_time: {start_time}, type: {type(start_time)}")
        logger.info(f"Original end_time: {end_time}, type: {type(end_time)}")
        
        # Преобразуем строки в даты без часового пояса (offset-naive)
        if isinstance(start_time, str):
            # Удаляем информацию о часовом поясе
            start_time = start_time.replace('Z', '')
            if '+' in start_time:
                start_time = start_time.split('+')[0]
            if '-' in start_time and 'T' in start_time and start_time.rindex('-') > start_time.index('T'):
                start_time = start_time.split('-', start_time.rindex('-'))[0]
            
            start_time = datetime.fromisoformat(start_time)
            logger.info(f"Converted start_time to naive datetime: {start_time}")
        elif start_time.tzinfo is not None:
            # Если это объект datetime с часовым поясом, удаляем информацию о часовом поясе
            start_time = start_time.replace(tzinfo=None)
            logger.info(f"Removed timezone from start_time: {start_time}")
        
        if isinstance(end_time, str):
            # Удаляем информацию о часовом поясе
            end_time = end_time.replace('Z', '')
            if '+' in end_time:
                end_time = end_time.split('+')[0]
            if '-' in end_time and 'T' in end_time and end_time.rindex('-') > end_time.index('T'):
                end_time = end_time.split('-', end_time.rindex('-'))[0]
                
            end_time = datetime.fromisoformat(end_time)
            logger.info(f"Converted end_time to naive datetime: {end_time}")
        elif end_time.tzinfo is not None:
            # Если это объект datetime с часовым поясом, удаляем информацию о часовом поясе
            end_time = end_time.replace(tzinfo=None)
            logger.info(f"Removed timezone from end_time: {end_time}")
        
        # Проверяем существование мастера и рабочего места
        from sqlalchemy import select
        from .models import Master, Workplace
        
        master_id = work_slot_data["master_id"]
        workplace_id = work_slot_data["workplace_id"]
        
        # Проверка мастера
        master_query = select(Master).where(Master.id == master_id)
        master_result = await db.execute(master_query)
        master = master_result.scalars().first()
        if not master:
            logger.error(f"Master with ID {master_id} not found")
            return None
        logger.info(f"Found master: {master.name} (ID: {master.id})")
        
        # Проверка рабочего места
        workplace_query = select(Workplace).where(Workplace.id == workplace_id)
        workplace_result = await db.execute(workplace_query)
        workplace = workplace_result.scalars().first()
        if not workplace:
            logger.error(f"Workplace with ID {workplace_id} not found")
            return None
        logger.info(f"Found workplace: {workplace.name} (ID: {workplace.id})")
        
        # Создаем рабочий слот
        try:
            from .models import WorkSlot
            logger.info("Creating WorkSlot object...")
            work_slot = WorkSlot(
                master_id=master_id,
                workplace_id=workplace_id,
                date=start_time.date(),
                start_time=start_time,
                end_time=end_time
            )
            logger.info(f"WorkSlot object created: {work_slot}")
            
            logger.info("Adding WorkSlot to database session...")
            db.add(work_slot)
            logger.info("Committing changes...")
            await db.commit()
            logger.info("Changes committed successfully")
            logger.info("Refreshing WorkSlot object...")
            await db.refresh(work_slot)
            logger.info(f"WorkSlot refreshed, ID: {work_slot.id}")
        except Exception as e:
            logger.error(f"Error creating WorkSlot: {e}")
            await db.rollback()
            return None
        
        return {
            "id": work_slot.id,
            "master_id": work_slot.master_id,
            "workplace_id": work_slot.workplace_id,
            "start_time": work_slot.start_time,
            "end_time": work_slot.end_time,
            "date": work_slot.start_time.date()
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in create_work_slot: {e}")
        await db.rollback()
        return None

async def update_work_slot(db: AsyncSession, work_slot_id: int, work_slot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обновление рабочего слота
    """
    try:
        # Получаем рабочий слот
        query = select(WorkSlot).where(WorkSlot.id == work_slot_id)
        result = await db.execute(query)
        work_slot = result.scalars().first()
        
        if not work_slot:
            logger.error(f"Work slot with ID {work_slot_id} not found")
            return None
        
        # Обновляем поля
        if "master_id" in work_slot_data:
            work_slot.master_id = work_slot_data["master_id"]
        
        if "workplace_id" in work_slot_data:
            work_slot.workplace_id = work_slot_data["workplace_id"]
        
        if "start_time" in work_slot_data:
            start_time = work_slot_data["start_time"]
            logger.info(f"Original start_time: {start_time}, type: {type(start_time)}")
            
            # Преобразуем строки в даты без часового пояса (offset-naive)
            if isinstance(start_time, str):
                # Удаляем информацию о часовом поясе
                start_time = start_time.replace('Z', '')
                if '+' in start_time:
                    start_time = start_time.split('+')[0]
                if '-' in start_time and 'T' in start_time and start_time.rindex('-') > start_time.index('T'):
                    start_time = start_time.split('-', start_time.rindex('-'))[0]
                
                start_time = datetime.fromisoformat(start_time)
                logger.info(f"Converted start_time to naive datetime: {start_time}")
            elif start_time.tzinfo is not None:
                # Если это объект datetime с часовым поясом, удаляем информацию о часовом поясе
                start_time = start_time.replace(tzinfo=None)
                logger.info(f"Removed timezone from start_time: {start_time}")
            
            work_slot.start_time = start_time
            work_slot.date = start_time.date()
        
        if "end_time" in work_slot_data:
            end_time = work_slot_data["end_time"]
            logger.info(f"Original end_time: {end_time}, type: {type(end_time)}")
            
            # Преобразуем строки в даты без часового пояса (offset-naive)
            if isinstance(end_time, str):
                # Удаляем информацию о часовом поясе
                end_time = end_time.replace('Z', '')
                if '+' in end_time:
                    end_time = end_time.split('+')[0]
                if '-' in end_time and 'T' in end_time and end_time.rindex('-') > end_time.index('T'):
                    end_time = end_time.split('-', end_time.rindex('-'))[0]
                    
                end_time = datetime.fromisoformat(end_time)
                logger.info(f"Converted end_time to naive datetime: {end_time}")
            elif end_time.tzinfo is not None:
                # Если это объект datetime с часовым поясом, удаляем информацию о часовом поясе
                end_time = end_time.replace(tzinfo=None)
                logger.info(f"Removed timezone from end_time: {end_time}")
                
            work_slot.end_time = end_time
        
        await db.commit()
        await db.refresh(work_slot)
        
        return {
            "id": work_slot.id,
            "master_id": work_slot.master_id,
            "workplace_id": work_slot.workplace_id,
            "start_time": work_slot.start_time,
            "end_time": work_slot.end_time,
            "date": work_slot.start_time.date()
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in update_work_slot: {e}")
        await db.rollback()
        return None

async def delete_work_slot(db: AsyncSession, work_slot_id: int) -> bool:
    """
    Удаление рабочего слота
    """
    try:
        # Получаем рабочий слот
        query = select(WorkSlot).where(WorkSlot.id == work_slot_id)
        result = await db.execute(query)
        work_slot = result.scalars().first()
        
        if not work_slot:
            return False
        
        # Проверяем, есть ли связанные активные записи
        appointments_query = select(func.count()).select_from(Appointment).where(
            and_(
                Appointment.master_id == work_slot.master_id,
                Appointment.start_time >= work_slot.start_time,
                Appointment.end_time <= work_slot.end_time,
                # Только активные записи (не отмененные и не завершенные)
                Appointment.status.notin_(["canceled", "completed"])
            )
        )
        appointments_count = await db.scalar(appointments_query)
        
        if appointments_count > 0:
            logger.error(f"Cannot delete work slot with ID {work_slot_id} because it has associated active appointments")
            return False
        
        # Удаляем рабочий слот
        await db.delete(work_slot)
        await db.commit()
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_work_slot: {e}")
        await db.rollback()
        return False

# Функции для работы с администраторами
async def get_admin_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[Admin]:
    """
    Получение администратора по Telegram ID
    """
    try:
        query = select(Admin).where(Admin.telegram_id == telegram_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Error in get_admin_by_telegram_id: {e}")
        return None

async def get_admin_by_username(db: AsyncSession, username: str) -> Optional[Admin]:
    """
    Получение администратора по имени пользователя
    """
    try:
        query = select(Admin).where(Admin.username == username)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Error in get_admin_by_username: {e}")
        return None

async def log_admin_action(db: AsyncSession, admin_id: int, action: str, details: str) -> bool:
    """
    Логирование действий администратора
    """
    try:
        log_entry = AdminLog(
            admin_id=admin_id,
            action=action,
            details=details,
            timestamp=datetime.now()
        )
        db.add(log_entry)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in log_admin_action: {e}")
        await db.rollback()
        return False

# Функции для работы с мастерами
async def get_masters(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Получение всех мастеров
    """
    try:
        # Используем JOIN для оптимизации запроса
        query = select(Master)
        result = await db.execute(query)
        masters = result.scalars().all()
        
        masters_list = []
        for master in masters:
            # Получаем процедуры мастера
            procedures_query = select(MasterProcedure.procedure_id).where(MasterProcedure.master_id == master.id)
            procedures_result = await db.execute(procedures_query)
            procedures = [proc[0] for proc in procedures_result.all()]
            
            masters_list.append({
                "id": master.id,
                "name": master.name,
                "telegram_username": master.telegram_username,
                "phone": master.phone,
                "email": master.email,
                "procedures": procedures
            })
        
        return masters_list
    except SQLAlchemyError as e:
        logger.error(f"Error in get_masters: {e}")
        return []

async def get_master_by_id(db: AsyncSession, master_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение мастера по ID
    """
    try:
        query = select(Master).where(Master.id == master_id)
        result = await db.execute(query)
        master = result.scalars().first()
        
        if not master:
            return None
        
        # Получаем процедуры мастера
        procedures_query = select(MasterProcedure.procedure_id).where(MasterProcedure.master_id == master.id)
        procedures_result = await db.execute(procedures_query)
        procedures = [proc[0] for proc in procedures_result.all()]
        
        return {
            "id": master.id,
            "name": master.name,
            "telegram_username": master.telegram_username,
            "phone": master.phone,
            "email": master.email,
            "procedures": procedures
        }
    except SQLAlchemyError as e:
        logger.error(f"Error in get_master_by_id: {e}")
        return None

async def create_master(db: AsyncSession, master_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создание нового мастера
    """
    try:
        # Проверка обязательных полей
        if "name" not in master_data:
            logger.error("Required field 'name' is missing in master_data")
            return None
        
        # Создаем мастера
        master = Master(
            name=master_data["name"],
            telegram_username=master_data.get("telegram_username"),
            phone=master_data.get("phone"),
            email=master_data.get("email")
        )
        
        db.add(master)
        await db.flush()  # Получаем ID мастера
        
        # Добавляем процедуры
        procedures = master_data.get("procedures", [])
        for procedure_id in procedures:
            master_procedure = MasterProcedure(
                master_id=master.id,
                procedure_id=procedure_id
            )
            db.add(master_procedure)
        
        await db.commit()
        await db.refresh(master)
        
        # Формируем ответ
        return await get_master_by_id(db, master.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in create_master: {e}")
        await db.rollback()
        return None

async def update_master(db: AsyncSession, master_id: int, master_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обновление мастера
    """
    try:
        query = select(Master).where(Master.id == master_id)
        result = await db.execute(query)
        master = result.scalars().first()
        
        if not master:
            return None
        
        # Обновляем поля мастера
        if "name" in master_data:
            master.name = master_data["name"]
        if "telegram_username" in master_data:
            master.telegram_username = master_data["telegram_username"]
        if "phone" in master_data:
            master.phone = master_data["phone"]
        if "email" in master_data:
            master.email = master_data["email"]
        
        # Обновляем процедуры
        if "procedures" in master_data:
            # Удаляем старые связи
            delete_query = delete(MasterProcedure).where(MasterProcedure.master_id == master.id)
            await db.execute(delete_query)
            
            # Добавляем новые связи
            for procedure_id in master_data["procedures"]:
                master_procedure = MasterProcedure(
                    master_id=master.id,
                    procedure_id=procedure_id
                )
                db.add(master_procedure)
        
        await db.commit()
        await db.refresh(master)
        
        # Формируем ответ
        return await get_master_by_id(db, master.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in update_master: {e}")
        await db.rollback()
        return None

async def delete_master(db: AsyncSession, master_id: int) -> bool:
    """
    Удаление мастера
    """
    try:
        query = select(Master).where(Master.id == master_id)
        result = await db.execute(query)
        master = result.scalars().first()
        
        if not master:
            logger.error(f"Master with ID {master_id} not found")
            return False
        
        # Проверка на связанные активные записи
        current_time = datetime.now()
        appointments_query = select(func.count()).select_from(Appointment).where(
            and_(
                Appointment.master_id == master_id,
                Appointment.start_time >= current_time,
                Appointment.status.notin_(["canceled", "completed"])
            )
        )
        appointments_count = await db.scalar(appointments_query)
        
        if appointments_count > 0:
            # Если есть связанные активные записи в будущем, не удаляем мастера
            logger.error(f"Cannot delete master with ID {master_id} because it has associated active appointments in the future")
            return False
        
        # Проверка на рабочее время в будущем или сейчас
        work_slots_query = select(func.count()).select_from(WorkSlot).where(
            and_(
                WorkSlot.master_id == master_id,
                WorkSlot.end_time >= current_time
            )
        )
        work_slots_count = await db.scalar(work_slots_query)
        
        if work_slots_count > 0:
            # Если есть рабочее время в будущем или сейчас, не удаляем мастера
            logger.error(f"Cannot delete master with ID {master_id} because it has work slots in the future or now")
            return False
        
        # Удаляем связи с процедурами
        delete_procedures_query = delete(MasterProcedure).where(MasterProcedure.master_id == master_id)
        await db.execute(delete_procedures_query)
        
        # Удаляем мастера
        await db.delete(master)
        await db.commit()
        logger.info(f"Master with ID {master_id} successfully deleted")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_master: {e}")
        await db.rollback()
        return False

# Функции для работы с клиентами
async def get_clients(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Получение всех клиентов
    """
    try:
        query = select(Client).order_by(Client.id)
        result = await db.execute(query)
        clients = result.scalars().all()
        
        client_list = []
        for client in clients:
            client_dict = {
                "id": client.id,
                "name": client.name,
                "phone": client.phone,
                "email": client.email,
                "telegram_id": client.telegram_id,
                "lang": client.lang,
                "time_coeff": client.time_coeff,
                "is_first_visit": client.is_first_visit,
                "created_at": client.created_at,
                "updated_at": client.updated_at
            }
            client_list.append(client_dict)
        
        return client_list
    except SQLAlchemyError as e:
        logger.error(f"Error in get_clients: {e}")
        return []

async def get_client_by_id(db: AsyncSession, client_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение клиента по ID
    """
    try:
        query = select(Client).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalars().first()
        
        if not client:
            return None
        
        client_dict = {
            "id": client.id,
            "name": client.name,
            "phone": client.phone,
            "email": client.email,
            "telegram_id": client.telegram_id,
            "created_at": client.created_at,
            "updated_at": client.updated_at
        }
        
        return client_dict
    except SQLAlchemyError as e:
        logger.error(f"Error in get_client_by_id: {e}")
        return None

async def get_client_by_telegram_id(db: AsyncSession, telegram_id: str) -> Optional[Dict[str, Any]]:
    """
    Получение клиента по Telegram ID
    """
    try:
        query = select(Client).where(Client.telegram_id == str(telegram_id))
        result = await db.execute(query)
        client = result.scalars().first()
        
        if not client:
            logger.info(f"Client with telegram_id {telegram_id} not found")
            return None
        
        client_dict = {
            "id": client.id,
            "name": client.name,
            "phone": client.phone,
            "email": client.email,
            "telegram_id": client.telegram_id,
            "lang": client.lang,
            "time_coeff": client.time_coeff,
            "is_first_visit": client.is_first_visit,
            "created_at": client.created_at,
            "updated_at": client.updated_at
        }
        
        return client_dict
    except SQLAlchemyError as e:
        logger.error(f"Error in get_client_by_telegram_id: {e}")
        return None

async def create_client(db: AsyncSession, client_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создание нового клиента
    """
    try:
        # Проверка на существование клиента с таким же телефоном
        if client_data.get("phone") and client_data["phone"].strip():
            phone_query = select(Client).where(Client.phone == client_data["phone"])
            phone_result = await db.execute(phone_query)
            existing_client = phone_result.scalars().first()
            
            if existing_client:
                logger.warning(f"Client with phone {client_data['phone']} already exists")
                return None
        
        # Создание нового клиента
        new_client = Client(
            name=client_data.get("name", ""),
            phone=client_data.get("phone", "") or "",
            email=client_data.get("email", "") or "",
            telegram_id=client_data.get("telegram_id", "") or "",
            lang=client_data.get("lang", "ru"),
            time_coeff=client_data.get("time_coeff", 1.0),
            is_first_visit=client_data.get("is_first_visit", True)
        )
        
        db.add(new_client)
        await db.commit()
        await db.refresh(new_client)
        
        # Формируем ответ
        return await get_client_by_id(db, new_client.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in create_client: {e}")
        await db.rollback()
        return None

async def update_client(db: AsyncSession, client_id: int, client_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обновление клиента
    """
    try:
        query = select(Client).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalars().first()
        
        if not client:
            return None
        
        # Проверка на существование клиента с таким же телефоном (кроме текущего)
        if client_data.get("phone") and client_data["phone"] != client.phone:
            phone_query = select(Client).where(and_(Client.phone == client_data["phone"], Client.id != client_id))
            phone_result = await db.execute(phone_query)
            existing_client = phone_result.scalars().first()
            
            if existing_client:
                logger.warning(f"Another client with phone {client_data['phone']} already exists")
                return None
        
        # Обновление полей клиента
        if "name" in client_data:
            client.name = client_data["name"]
        if "phone" in client_data:
            client.phone = client_data["phone"]
        if "email" in client_data:
            client.email = client_data["email"]
        if "telegram_id" in client_data:
            client.telegram_id = client_data["telegram_id"]
        
        client.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(client)
        
        # Формируем ответ
        return await get_client_by_id(db, client.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in update_client: {e}")
        await db.rollback()
        return None

async def delete_client(db: AsyncSession, client_id: int) -> bool:
    """
    Удаление клиента
    """
    try:
        query = select(Client).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalars().first()
        
        if not client:
            return False
        
        # Проверка на связанные записи
        appointments_query = select(func.count()).select_from(Appointment).where(Appointment.client_id == client_id)
        appointments_count = await db.scalar(appointments_query)
        
        if appointments_count > 0:
            # Если есть связанные записи, не удаляем клиента
            return False
        
        # Удаляем клиента
        await db.delete(client)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_client: {e}")
        await db.rollback()
        return False

# Функции для работы с записями
async def get_appointments(db: AsyncSession, client_id: Optional[int] = None, master_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Получение списка записей с возможностью фильтрации
    """
    try:
        # Проверяем, есть ли записи в базе данных
        count_query = select(func.count()).select_from(Appointment)
        count_result = await db.execute(count_query)
        count = count_result.scalar()
        logger.info(f"Total appointments in database: {count}")
        
        # Получаем все записи без фильтров и связей
        simple_query = select(Appointment)
        simple_result = await db.execute(simple_query)
        simple_appointments = simple_result.scalars().all()
        logger.info(f"Simple query appointments count: {len(simple_appointments)}")
        for app in simple_appointments:
            logger.info(f"Simple appointment: id={app.id}, client_id={app.client_id}, master_id={app.master_id}, status={app.status}")
        
        # Основной запрос с опциями загрузки связей
        query = select(Appointment).options(
            joinedload(Appointment.client),
            joinedload(Appointment.master),
            joinedload(Appointment.workplace)
        )
        
        # Применяем фильтры, если они указаны
        if client_id is not None:
            query = query.where(Appointment.client_id == client_id)
        if master_id is not None:
            query = query.where(Appointment.master_id == master_id)
        
        # Сортируем по дате создания в обратном порядке (новые сверху)
        query = query.order_by(desc(Appointment.created_at))
        
        logger.info(f"Query: {query}")
        
        result = await db.execute(query)
        appointments = result.unique().scalars().all()
        logger.info(f"Query with joins appointments count: {len(appointments)}")
        for app in appointments:
            logger.info(f"Joined appointment: id={app.id}, client_id={app.client_id}, master_id={app.master_id}, status={app.status}")
            logger.info(f"Client: {app.client.name if app.client else None}, Master: {app.master.name if app.master else None}")
        
        
        # Получаем все процедуры для быстрого поиска
        procedures = await get_procedures(db)
        procedures_dict = {proc["id"]: proc for proc in procedures}
        
        appointments_list = []
        for appointment in appointments:
            # Собираем информацию о процедурах
            procedures_data = []
            if appointment.procedures:
                for proc_id in appointment.procedures:
                    if proc_id in procedures_dict:
                        procedures_data.append(procedures_dict[proc_id])
            
            # Создаем словарь с данными о записи
            appointment_dict = {
                "id": appointment.id,
                "client_id": appointment.client_id,
                "master_id": appointment.master_id,
                "workplace_id": appointment.workplace_id,
                "procedures": appointment.procedures,
                "procedures_data": procedures_data,
                "start_time": appointment.start_time,
                "end_time": appointment.end_time,
                "status": appointment.status.value,
                "google_event_id": appointment.google_event_id,
                "created_at": appointment.created_at,
                "updated_at": appointment.updated_at
            }
            
            # Добавляем информацию о клиенте, мастере и рабочем месте
            if appointment.client:
                appointment_dict["client"] = {
                    "id": appointment.client.id,
                    "name": appointment.client.name,
                    "phone": appointment.client.phone
                }
            
            if appointment.master:
                appointment_dict["master"] = {
                    "id": appointment.master.id,
                    "name": appointment.master.name
                }
            
            if appointment.workplace:
                appointment_dict["workplace"] = {
                    "id": appointment.workplace.id,
                    "name": appointment.workplace.name
                }
            
            appointments_list.append(appointment_dict)
        
        return appointments_list
    except Exception as e:
        logger.error(f"Error in get_appointments: {e}")
        return []

async def get_appointment_by_id(db: AsyncSession, appointment_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение записи по ID
    """
    try:
        query = select(Appointment).where(Appointment.id == appointment_id).options(
            joinedload(Appointment.client),
            joinedload(Appointment.master),
            joinedload(Appointment.workplace)
        )
        result = await db.execute(query)
        appointment = result.unique().scalars().first()
        
        if not appointment:
            logger.error(f"Appointment with ID {appointment_id} not found")
            return None
        
        # Получаем информацию о процедурах
        procedures = await get_procedures(db)
        procedures_dict = {proc["id"]: proc for proc in procedures}
        
        procedures_data = []
        if appointment.procedures:
            for proc_id in appointment.procedures:
                if proc_id in procedures_dict:
                    procedures_data.append(procedures_dict[proc_id])
        
        # Формируем словарь с данными о записи
        appointment_dict = {
            "id": appointment.id,
            "client_id": appointment.client_id,
            "master_id": appointment.master_id,
            "workplace_id": appointment.workplace_id,
            "procedures": appointment.procedures,
            "procedures_data": procedures_data,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "status": appointment.status.value,
            "google_event_id": appointment.google_event_id,
            "created_at": appointment.created_at,
            "updated_at": appointment.updated_at
        }
        
        # Добавляем информацию о клиенте, мастере и рабочем месте
        if appointment.client:
            appointment_dict["client"] = {
                "id": appointment.client.id,
                "name": appointment.client.name,
                "phone": appointment.client.phone
            }
        
        if appointment.master:
            appointment_dict["master"] = {
                "id": appointment.master.id,
                "name": appointment.master.name
            }
        
        if appointment.workplace:
            appointment_dict["workplace"] = {
                "id": appointment.workplace.id,
                "name": appointment.workplace.name
            }
        
        logger.info(f"Returning appointment data: {appointment_dict}")
        return appointment_dict
    except Exception as e:
        logger.error(f"Error in get_appointment_by_id: {e}")
        return None

async def create_appointment(db: AsyncSession, appointment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создание новой записи
    """
    try:
        # Проверяем наличие обязательных полей
        required_fields = ["client_id", "master_id", "workplace_id", "procedures", "start_time", "end_time"]
        for field in required_fields:
            if field not in appointment_data:
                logger.error(f"Missing required field: {field}")
                return None
        
        # Преобразуем даты в формат без часового пояса
        start_time = appointment_data["start_time"]
        end_time = appointment_data["end_time"]
        
        # Если даты с часовым поясом, преобразуем в формат без часового пояса
        if hasattr(start_time, 'tzinfo') and start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if hasattr(end_time, 'tzinfo') and end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
        
        # Создаем новую запись
        new_appointment = Appointment(
            client_id=appointment_data["client_id"],
            master_id=appointment_data["master_id"],
            workplace_id=appointment_data["workplace_id"],
            procedures=appointment_data["procedures"],
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.active,
            google_event_id=appointment_data.get("google_event_id")
        )
        
        db.add(new_appointment)
        await db.commit()
        await db.refresh(new_appointment)
        
        # Формируем ответ
        return await get_appointment_by_id(db, new_appointment.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in create_appointment: {e}")
        await db.rollback()
        return None

async def update_appointment(db: AsyncSession, appointment_id: int, appointment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обновление записи
    """
    try:
        # Получаем запись по ID
        result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalars().first()
        
        if not appointment:
            logger.error(f"Appointment with ID {appointment_id} not found")
            return None
        
        # Обновляем поля записи
        if "client_id" in appointment_data:
            appointment.client_id = appointment_data["client_id"]
        if "master_id" in appointment_data:
            appointment.master_id = appointment_data["master_id"]
        if "workplace_id" in appointment_data:
            appointment.workplace_id = appointment_data["workplace_id"]
        if "procedures" in appointment_data:
            appointment.procedures = appointment_data["procedures"]
        if "start_time" in appointment_data:
            start_time = appointment_data["start_time"]
            # Если дата с часовым поясом, преобразуем в формат без часового пояса
            if hasattr(start_time, 'tzinfo') and start_time.tzinfo is not None:
                start_time = start_time.replace(tzinfo=None)
            appointment.start_time = start_time
        if "end_time" in appointment_data:
            end_time = appointment_data["end_time"]
            # Если дата с часовым поясом, преобразуем в формат без часового пояса
            if hasattr(end_time, 'tzinfo') and end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)
            appointment.end_time = end_time
        if "status" in appointment_data:
            appointment.status = appointment_data["status"]
        if "google_event_id" in appointment_data:
            appointment.google_event_id = appointment_data["google_event_id"]
        
        appointment.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(appointment)
        
        # Формируем ответ
        return await get_appointment_by_id(db, appointment.id)
    except SQLAlchemyError as e:
        logger.error(f"Error in update_appointment: {e}")
        await db.rollback()
        return None

async def delete_appointment(db: AsyncSession, appointment_id: int) -> bool:
    """
    Удаление записи
    """
    try:
        query = select(Appointment).where(Appointment.id == appointment_id)
        result = await db.execute(query)
        appointment = result.scalars().first()
        
        if not appointment:
            return False
        
        # Удаляем запись
        await db.delete(appointment)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error in delete_appointment: {e}")
        await db.rollback()
        return False

# Функция для расчета продолжительности приема
async def calculate_appointment_duration(db: AsyncSession, procedure_ids: List[int], time_coeff: float = 1.0, is_first_visit: bool = False) -> int:
    """
    Расчет продолжительности приема на основе выбранных процедур
    
    Args:
        db: Сессия базы данных
        procedure_ids: Список ID выбранных процедур
        time_coeff: Коэффициент времени для клиента (опытный клиент может требовать меньше времени)
        is_first_visit: Первый ли визит клиента (первый визит может требовать больше времени)
        
    Returns:
        Продолжительность приема в минутах
    """
    try:
        # Базовая продолжительность для первого визита
        base_duration = 15 if is_first_visit else 0
        
        # Если нет выбранных процедур, возвращаем минимальную продолжительность
        if not procedure_ids:
            return max(30, base_duration)
        
        # Получаем информацию о выбранных процедурах
        query = select(Procedure).where(Procedure.id.in_(procedure_ids))
        result = await db.execute(query)
        procedures = result.scalars().all()
        
        # Рассчитываем общую продолжительность
        total_duration = base_duration
        for procedure in procedures:
            # Используем duration из процедуры, если он есть, иначе используем значение по умолчанию
            procedure_duration = getattr(procedure, 'duration', 30)
            total_duration += procedure_duration
        
        # Применяем коэффициент времени клиента
        adjusted_duration = int(total_duration * time_coeff)
        
        # Минимальная продолжительность - 30 минут
        return max(30, adjusted_duration)
    except SQLAlchemyError as e:
        logger.error(f"Error in calculate_appointment_duration: {e}")
        # В случае ошибки возвращаем значение по умолчанию
        return 60

# Функция для получения доступных дней для мастера
async def get_available_days(db: AsyncSession, master_id: int, start_date: datetime, days_count: int = 30) -> List[datetime]:
    """
    Получение доступных дней для записи к мастеру
    
    Args:
        db: Сессия базы данных
        master_id: ID мастера
        start_date: Начальная дата поиска
        days_count: Количество дней для поиска
        
    Returns:
        Список дат, в которые у мастера есть рабочее время
    """
    try:
        end_date = start_date + timedelta(days=days_count)
        
        # Получаем рабочие слоты мастера на указанный период
        query = (
            select(WorkSlot)
            .where(
                WorkSlot.master_id == master_id,
                WorkSlot.start_time >= start_date,
                WorkSlot.start_time < end_date
            )
        )
        result = await db.execute(query)
        work_slots = result.scalars().all()
        
        # Группируем рабочие слоты по дням
        available_days = set()
        for slot in work_slots:
            day = datetime(slot.start_time.year, slot.start_time.month, slot.start_time.day)
            available_days.add(day)
        
        return sorted(list(available_days))
    except SQLAlchemyError as e:
        logger.error(f"Error in get_available_days: {e}")
        return []

# Функция для получения доступных слотов
async def get_available_slots(db: AsyncSession, master_id: int, date: datetime, duration: int = 60) -> List[datetime]:
    """
    Получение доступных слотов для записи на основе мастера, даты и продолжительности процедуры
    
    Args:
        db: Сессия базы данных
        master_id: ID мастера
        date: Дата, на которую ищем слоты
        duration: Продолжительность процедуры в минутах
        
    Returns:
        Список доступных временных слотов (datetime)
    """
    try:
        # Функция для округления времени до ближайшей четверти часа в большую сторону
        def round_up_to_quarter_hour(dt):
            """Округляет время до ближайшей четверти часа в большую сторону"""
            minutes = dt.minute
            if minutes % 15 == 0:
                return dt
            return dt.replace(minute=((minutes // 15) + 1) * 15, second=0, microsecond=0)
        
        # Получаем рабочий день мастера
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        # Получаем рабочие слоты мастера на указанную дату
        query = (
            select(WorkSlot)
            .where(
                WorkSlot.master_id == master_id,
                WorkSlot.start_time >= start_of_day,
                WorkSlot.end_time <= end_of_day
            )
            .order_by(WorkSlot.start_time)
        )
        result = await db.execute(query)
        work_slots = result.scalars().all()
        
        if not work_slots:
            return []
        
        # Получаем существующие записи мастера на указанную дату, отсортированные по времени начала
        query = (
            select(Appointment)
            .where(
                Appointment.master_id == master_id,
                Appointment.start_time >= start_of_day,
                Appointment.start_time <= end_of_day,
                Appointment.status != "canceled"
            )
            .order_by(Appointment.start_time)
        )
        result = await db.execute(query)
        appointments = result.scalars().all()
        
        # Создаем доступные слоты
        available_slots = []
        
        for work_slot in work_slots:
            # Создаем временную шкалу для этого рабочего слота
            timeline = []
            
            # Добавляем существующие записи в временную шкалу
            slot_appointments = [
                a for a in appointments 
                if a.start_time >= work_slot.start_time and a.start_time < work_slot.end_time
            ]
            
            # Сортируем записи по времени начала
            slot_appointments.sort(key=lambda a: a.start_time)
            
            # Генерируем доступные слоты с учетом существующих записей
            current_time = work_slot.start_time
            
            # Обрабатываем каждую запись
            for appointment in slot_appointments:
                # Генерируем слоты до текущей записи
                while current_time < appointment.start_time and current_time + timedelta(minutes=duration) <= appointment.start_time:
                    # Проверяем, что слот удовлетворяет условиям
                    if (
                        # До конца рабочего времени не менее 1 часа
                        current_time + timedelta(hours=1) <= work_slot.end_time and
                        # Запись с учетом ее продолжительности не выходит за пределы рабочего времени
                        current_time + timedelta(minutes=duration) <= work_slot.end_time
                    ):
                        available_slots.append(current_time)
                    
                    # Переходим к следующему часу
                    current_time += timedelta(hours=1)
                
                # Получаем продолжительность записи
                appointment_duration = getattr(appointment, 'duration', 60)  # По умолчанию 60 минут
                
                # Вычисляем время окончания записи + перерыв
                appointment_end = appointment.start_time + timedelta(minutes=appointment_duration)
                appointment_end_with_break = appointment_end + timedelta(minutes=15)
                
                # Округляем до ближайшей четверти часа в большую сторону
                appointment_end_with_break = round_up_to_quarter_hour(appointment_end_with_break)
                
                # Устанавливаем текущее время на конец записи + перерыв
                current_time = appointment_end_with_break
            
            # Генерируем слоты после последней записи до конца рабочего времени
            while current_time + timedelta(minutes=duration) <= work_slot.end_time:
                # Проверяем, что слот удовлетворяет условиям
                if (
                    # До конца рабочего времени не менее 1 часа
                    current_time + timedelta(hours=1) <= work_slot.end_time and
                    # Запись с учетом ее продолжительности не выходит за пределы рабочего времени
                    current_time + timedelta(minutes=duration) <= work_slot.end_time
                ):
                    available_slots.append(current_time)
                
                # Переходим к следующему часу
                current_time += timedelta(hours=1)
        
        # Удаляем дубликаты и сортируем слоты
        available_slots = sorted(list(set(available_slots)))
        
        return available_slots
    except SQLAlchemyError as e:
        logger.error(f"Error in get_available_slots: {e}")
        return []
# Функция для добавления индексов в базу данных
async def add_database_indexes(db: AsyncSession) -> None:
    """
    Добавление индексов в базу данных для оптимизации запросов
    """
    try:
        # Индексы для таблицы section_translation
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_section_translation_section_id ON section_translation (section_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_section_translation_lang ON section_translation (lang)")
        )
        
        # Индексы для таблицы procedure_translation
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_procedure_translation_procedure_id ON procedure_translation (procedure_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_procedure_translation_lang ON procedure_translation (lang)")
        )
        
        # Индексы для таблицы procedure
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_procedure_section_id ON procedure (section_id)")
        )
        
        # Индексы для таблицы master_procedure
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_master_procedure_master_id ON master_procedure (master_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_master_procedure_procedure_id ON master_procedure (procedure_id)")
        )
        
        # Индексы для таблицы appointment
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointment_client_id ON appointment (client_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointment_master_id ON appointment (master_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointment_procedure_id ON appointment (procedure_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointment_workplace_id ON appointment (workplace_id)")
        )
        await db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointment_status ON appointment (status)")
        )
        
        await db.commit()
        logger.info("Database indexes added successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error in add_database_indexes: {e}")
        await db.rollback()
