"""
Оптимизированные эндпоинты API для работы с Beauty Salon Bot
"""
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import json
import logging
from dotenv import load_dotenv

from src.database.base import get_db
from src.database import crud
from src.api import schemas
from src.api.response_models import APIResponse, SectionResponseModel, ProcedureResponseModel
from src.database.models import Master, Workplace, WorkSlot, Appointment, AppointmentStatus

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

load_dotenv()

# Security settings
SECRET_KEY = os.getenv("API_SECRET_KEY", "your_secret_key_for_jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="Beauty Salon API", 
    description="API для управления салоном красоты",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")
templates = Jinja2Templates(directory="src/api/templates")

# Обработка ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Обработчик HTTP-исключений
    """
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error_response(
            message=exc.detail,
            errors=[{"code": exc.status_code, "detail": exc.detail}]
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Обработчик общих исключений
    """
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(exc)}]
        ).dict()
    )

# Security functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_admin(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        telegram_id: str = payload.get("sub")
        if telegram_id is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=telegram_id)
    except JWTError:
        raise credentials_exception
    admin = await crud.get_admin_by_telegram_id(db, int(token_data.username))
    if admin is None:
        raise credentials_exception
    return admin

# Authentication endpoints
@app.post("/token", response_model=APIResponse[schemas.Token])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Получение токена доступа
    """
    try:
        # Пробуем получить администратора по Telegram ID
        try:
            admin_id = int(form_data.username)
            admin = await crud.get_admin_by_telegram_id(db, admin_id)
        except ValueError:
            # Если имя пользователя не является числом, ищем по имени пользователя
            admin = await crud.get_admin_by_username(db, form_data.username)
            logger.info(f"Attempting to login with username: {form_data.username}")
        
        if admin:
            logger.info(f"Found admin: {admin.username} (ID: {admin.id})")
        else:
            logger.error(f"Admin not found for: {form_data.username}")
        
        if not admin or not verify_password(form_data.password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(admin.telegram_id)}, expires_delta=access_token_expires
        )
        
        await crud.log_admin_action(db, admin.id, "login", "Admin logged in via API")
        
        token_data = {"access_token": access_token, "token_type": "bearer"}
        return APIResponse.success_response(
            data=token_data,
            message="Authentication successful"
        )
    except Exception as e:
        logger.error(f"Error in login_for_access_token: {e}")
        raise

# Section endpoints
@app.get("/api/v2/sections", response_model=APIResponse[List[SectionResponseModel]])
async def read_sections(
    lang: schemas.LanguageEnum = Query(schemas.LanguageEnum.UKR, description="Язык для получения данных"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение всех разделов
    """
    try:
        sections = await crud.get_sections(db, lang.value)
        return APIResponse.success_response(
            data=sections,
            message=f"Retrieved {len(sections)} sections"
        )
    except Exception as e:
        logger.error(f"Error in read_sections: {e}")
        raise

@app.get("/api/v2/sections/{section_id}", response_model=APIResponse[SectionResponseModel])
async def read_section(
    section_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получение раздела по ID
    """
    try:
        section = await crud.get_section_by_id(db, section_id)
        if section is None:
            raise HTTPException(status_code=404, detail=f"Section with ID {section_id} not found")
        
        return APIResponse.success_response(
            data=section,
            message=f"Retrieved section with ID {section_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in read_section: {e}")
        raise

@app.post("/api/v2/sections", response_model=APIResponse[SectionResponseModel])
async def create_section(
    section: schemas.SectionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Создание нового раздела
    """
    try:
        # Валидация данных
        if not section.translations:
            raise HTTPException(status_code=400, detail="At least one translation is required")
        
        # Используем имя из первого перевода (обычно UKR) в качестве имени раздела
        ukr_translation = next((t for t in section.translations if t.lang == "UKR"), section.translations[0])
        section_data = {"name": ukr_translation.name}
        translations = [t.dict() for t in section.translations]
        
        section = await crud.create_section(db, {"name": section.translations[0].name}, section.translations)
        if section is None:
            raise HTTPException(status_code=500, detail="Failed to create section")
        
        return APIResponse.success_response(
            data=section,
            message=f"Section created successfully with ID {section['id']}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_section: {e}")
        raise

@app.put("/api/v2/sections/{section_id}", response_model=APIResponse[SectionResponseModel])
async def update_section(
    section_id: int,
    section: schemas.SectionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Обновление раздела
    """
    try:
        # Валидация данных
        if not section.translations:
            raise HTTPException(status_code=400, detail="At least one translation is required")
        
        translations = [t.dict() for t in section.translations]
        section = await crud.update_section(db, section_id, section.translations)
        
        if section is None:
            raise HTTPException(status_code=404, detail=f"Section with ID {section_id} not found")
        
        return APIResponse.success_response(
            data=section,
            message=f"Section with ID {section_id} updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_section: {e}")
        raise

@app.delete("/api/v2/sections/{section_id}", response_model=APIResponse[bool])
async def delete_section(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Удаление раздела
    """
    try:
        success = await crud.delete_section(db, section_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Section with ID {section_id} not found")
        
        return APIResponse.success_response(
            data=True,
            message=f"Section with ID {section_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_section: {e}")
        raise

# Procedure endpoints
@app.get("/api/v2/procedures", response_model=APIResponse[List[ProcedureResponseModel]])
async def read_procedures(
    lang: schemas.LanguageEnum = Query(schemas.LanguageEnum.UKR, description="Язык для получения данных"),
    section_id: Optional[int] = Query(None, description="ID раздела для фильтрации"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение всех процедур
    """
    try:
        procedures = await crud.get_procedures(db, lang.value)
        
        # Фильтрация по разделу, если указан section_id
        if section_id is not None:
            procedures = [p for p in procedures if p["section_id"] == section_id]
        
        return APIResponse.success_response(
            data=procedures,
            message=f"Retrieved {len(procedures)} procedures"
        )
    except Exception as e:
        logger.error(f"Error in read_procedures: {e}")
        raise

@app.get("/api/v2/procedures/{procedure_id}", response_model=APIResponse[ProcedureResponseModel])
async def read_procedure(
    procedure_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получение процедуры по ID
    """
    try:
        procedure = await crud.get_procedure_by_id(db, procedure_id)
        
        if procedure is None:
            raise HTTPException(status_code=404, detail=f"Procedure with ID {procedure_id} not found")
        
        return APIResponse.success_response(
            data=procedure,
            message=f"Retrieved procedure with ID {procedure_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in read_procedure: {e}")
        raise

@app.post("/api/v2/procedures", response_model=APIResponse[ProcedureResponseModel])
async def create_procedure(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Создание новой процедуры
    """
    try:
        # Получаем данные из запроса напрямую
        procedure_data = await request.json()
        logger.info(f"Received procedure data: {procedure_data}")
        
        # Проверяем наличие обязательных полей
        required_fields = ["section_id", "duration", "base_price", "translations"]
        for field in required_fields:
            if field not in procedure_data:
                logger.error(f"Missing required field: {field}")
                return APIResponse.error_response(
                    message=f"Missing required field: {field}",
                    errors=[{"code": 400, "detail": f"Missing required field: {field}"}]
                )
        
        # Проверяем наличие переводов
        if not procedure_data.get("translations"):
            logger.error("At least one translation is required")
            return APIResponse.error_response(
                message="At least one translation is required",
                errors=[{"code": 400, "detail": "At least one translation is required"}]
            )
        
        # Проверяем каждый перевод
        for i, translation in enumerate(procedure_data["translations"]):
            if "lang" not in translation or "name" not in translation:
                logger.error(f"Translation {i} is missing required fields (lang or name)")
                return APIResponse.error_response(
                    message=f"Translation {i} is missing required fields (lang or name)",
                    errors=[{"code": 400, "detail": f"Translation {i} is missing required fields (lang or name)"}]
                )
        
        procedure = await crud.create_procedure(db, procedure_data)
        
        if procedure is None:
            logger.error("Failed to create procedure")
            return APIResponse.error_response(
                message="Failed to create procedure",
                errors=[{"code": 500, "detail": "Failed to create procedure"}]
            )
        
        return APIResponse.success_response(
            data=procedure,
            message=f"Procedure created successfully with ID {procedure['id']}"
        )
    except HTTPException as e:
        logger.error(f"HTTP Exception in create_procedure: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in create_procedure: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.put("/api/v2/procedures/{procedure_id}", response_model=APIResponse[ProcedureResponseModel])
async def update_procedure(
    procedure_id: int,
    procedure: schemas.ProcedureCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Обновление процедуры
    """
    try:
        # Валидация данных
        if not procedure.translations:
            raise HTTPException(status_code=400, detail="At least one translation is required")
        
        procedure_data = procedure.dict(exclude={"translations"})
        translations = [t.dict() for t in procedure.translations]
        
        procedure = await crud.update_procedure(db, procedure_id, procedure_data, procedure.translations)
        
        if procedure is None:
            raise HTTPException(status_code=404, detail=f"Procedure with ID {procedure_id} not found")
        
        return APIResponse.success_response(
            data=procedure,
            message=f"Procedure with ID {procedure_id} updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_procedure: {e}")
        raise

@app.delete("/api/v2/procedures/{procedure_id}", response_model=APIResponse[bool])
async def delete_procedure(
    procedure_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Удаление процедуры
    """
    try:
        success = await crud.delete_procedure(db, procedure_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Procedure with ID {procedure_id} not found")
        
        return APIResponse.success_response(
            data=True,
            message=f"Procedure with ID {procedure_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_procedure: {e}")
        raise

# Admin pages
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_index(request: Request):
    """
    Главная страница админки
    """
    return RedirectResponse(url="/admin/sections")

@app.get("/admin/masters", response_class=HTMLResponse)
async def admin_masters(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления мастерами
    """
    try:
        # Получаем список мастеров
        masters = await crud.get_masters(db)
        
        # Получаем список процедур для выбора
        procedures = await crud.get_procedures(db)
        
        return templates.TemplateResponse("masters.html", {
            "request": request,
            "masters": masters,
            "procedures": procedures,
            "active_page": "masters"
        })
    except Exception as e:
        logger.error(f"Error in admin_masters: {e}")
        raise

@app.get("/admin/clients", response_class=HTMLResponse)
async def admin_clients(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления клиентами
    """
    try:
        # Получаем список клиентов
        clients = await crud.get_clients(db)
        
        return templates.TemplateResponse("clients.html", {
            "request": request,
            "active_page": "clients",
            "clients": clients
        })
    except Exception as e:
        logger.error(f"Error in admin_clients: {e}")
        raise

@app.get("/admin/appointments", response_class=HTMLResponse)
async def admin_appointments(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления записями
    """
    try:
        # Получаем список записей
        appointments = await crud.get_appointments(db)
        logger.info(f"Appointments count: {len(appointments)}")
        logger.info(f"Appointments data: {appointments}")
        
        # Получаем списки клиентов, мастеров, рабочих мест и процедур
        clients = await crud.get_clients(db)
        masters = await crud.get_masters(db)
        workplaces = await crud.get_workplaces(db)
        procedures = await crud.get_procedures(db)
        
        logger.info(f"Clients count: {len(clients)}")
        logger.info(f"Masters count: {len(masters)}")
        logger.info(f"Workplaces count: {len(workplaces)}")
        logger.info(f"Procedures count: {len(procedures)}")
        
        # Преобразуем даты в строки для отображения в шаблоне
        for appointment in appointments:
            if "start_time" in appointment and appointment["start_time"]:
                appointment["start_time_str"] = appointment["start_time"].strftime("%Y-%m-%d %H:%M")
            if "end_time" in appointment and appointment["end_time"]:
                appointment["end_time_str"] = appointment["end_time"].strftime("%Y-%m-%d %H:%M")
        
        return templates.TemplateResponse(
            "appointments.html",
            {
                "request": request,
                "appointments": appointments,
                "clients": clients,
                "masters": masters,
                "workplaces": workplaces,
                "procedures": procedures
            }
        )
    except Exception as e:
        logger.error(f"Error in admin_appointments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке страницы управления записями"
        )

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница настроек
    """
    try:
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "active_page": "settings"
        })
    except Exception as e:
        logger.error(f"Error in admin_settings: {e}")
        raise

@app.get("/admin/work_slots", response_class=HTMLResponse)
async def admin_work_slots(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления рабочими слотами
    """
    try:
        # Создаем упрощенную версию функции
        # Получаем список мастеров и рабочих мест напрямую из базы данных
        
        # Получаем список мастеров
        masters_query = select(Master)
        masters_result = await db.execute(masters_query)
        masters_records = masters_result.scalars().all()
        
        # Преобразуем в формат для шаблона
        masters = []
        for master in masters_records:
            masters.append({
                "id": master.id,
                "name": master.name,
                "telegram_username": master.telegram_username,
                "phone": master.phone,
                "email": master.email,
                "procedures": []
            })
        
        # Получаем список рабочих мест
        workplaces_query = select(Workplace)
        workplaces_result = await db.execute(workplaces_query)
        workplaces_records = workplaces_result.scalars().all()
        
        # Преобразуем в формат для шаблона
        workplaces = []
        for workplace in workplaces_records:
            workplaces.append({
                "id": workplace.id,
                "name": workplace.name
            })
        
        # Получаем параметры фильтрации из запроса
        master_id = request.query_params.get('master_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        # Устанавливаем даты для фильтра
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str).replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str).replace(hour=23, minute=59, second=59)
            except ValueError:
                end_date = (start_date + timedelta(days=7)).replace(hour=23, minute=59, second=59)
        else:
            end_date = (start_date + timedelta(days=7)).replace(hour=23, minute=59, second=59)
        
        # Преобразуем master_id в int, если он есть
        filter_master_id = None
        if master_id and master_id.isdigit():
            filter_master_id = int(master_id)
        
        # Получаем рабочие слоты с применением фильтров
        logger.info(f"Getting work slots with filters: master_id={filter_master_id}, start_date={start_date}, end_date={end_date}")
        work_slots = await crud.get_work_slots(db, master_id=filter_master_id, start_date=start_date, end_date=end_date)
        logger.info(f"Retrieved {len(work_slots)} work slots")
        
        # Логируем полученные данные для отладки
        for slot in work_slots:
            logger.info(f"Work slot: {slot}")
        
        # Проверяем наличие мастеров и рабочих мест
        logger.info(f"Masters count: {len(masters)}")
        logger.info(f"Workplaces count: {len(workplaces)}")
        
        # Проверяем данные мастеров
        for master in masters:
            logger.info(f"Master: {master}")
        
        # Проверяем данные рабочих мест
        for workplace in workplaces:
            logger.info(f"Workplace: {workplace}")
        
        # Теперь возвращаем шаблон с данными
        return templates.TemplateResponse("work_slots.html", {
            "request": request,
            "active_page": "work_slots",
            "masters": masters,
            "workplaces": workplaces,
            "work_slots": work_slots,
            "filter": {
                "master_id": filter_master_id,
                "start_date": start_date.date().isoformat() if start_date else None,
                "end_date": end_date.date().isoformat() if end_date else None
            }
        })
    except Exception as e:
        logger.error(f"Error in admin_work_slots: {e}")
        # В случае ошибки возвращаем пустой шаблон
        return templates.TemplateResponse("work_slots.html", {
            "request": request,
            "active_page": "work_slots",
            "masters": [],
            "workplaces": [],
            "work_slots": [],
            "filter": {
                "master_id": None,
                "start_date": datetime.now().date().isoformat(),
                "end_date": (datetime.now() + timedelta(days=7)).date().isoformat()
            }
        })

@app.get("/admin/workplaces", response_class=HTMLResponse)
async def admin_workplaces(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления рабочими местами
    """
    try:
        workplaces = await crud.get_workplaces(db)
        
        return templates.TemplateResponse("workplaces.html", {
            "request": request,
            "active_page": "workplaces",
            "workplaces": workplaces
        })
    except Exception as e:
        logger.error(f"Error in admin_workplaces: {e}")
        raise

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    """
    Страница входа в админку
    """
    return templates.TemplateResponse("login.html", {
        "request": request
    })

@app.get("/admin/sections", response_class=HTMLResponse)
async def admin_sections(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления разделами
    """
    try:
        sections = await crud.get_sections(db)
        
        return templates.TemplateResponse("sections.html", {
            "request": request,
            "active_page": "sections",
            "sections": sections
        })
    except Exception as e:
        logger.error(f"Error in admin_sections: {e}")
        raise

@app.get("/admin/procedures", response_class=HTMLResponse)
async def admin_procedures(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Страница управления процедурами
    """
    try:
        logger.info("Starting admin_procedures function")
        
        # Получаем данные о процедурах и разделах
        logger.info("Fetching procedures and sections")
        procedures = await crud.get_procedures(db)
        logger.info(f"Raw procedures: {type(procedures)}, count: {len(procedures) if procedures else 0}")
        if procedures and len(procedures) > 0:
            logger.info(f"First procedure type: {type(procedures[0])}")
            if isinstance(procedures[0], dict):
                logger.info(f"First procedure keys: {procedures[0].keys()}")
        
        sections = await crud.get_sections(db)
        logger.info(f"Raw sections: {type(sections)}, count: {len(sections) if sections else 0}")
        if sections and len(sections) > 0:
            logger.info(f"First section type: {type(sections[0])}")
            if isinstance(sections[0], dict):
                logger.info(f"First section keys: {sections[0].keys()}")
        
        # Проверяем, что procedures и sections являются списками
        if procedures is None:
            logger.warning("Procedures is None, setting to empty list")
            procedures = []
        if sections is None:
            logger.warning("Sections is None, setting to empty list")
            sections = []
        
        # Преобразуем список разделов для совместимости с шаблоном
        # В шаблоне ожидается, что section.translations - это словарь с ключами по языкам
        logger.info("Converting sections data format for template compatibility")
        
        formatted_sections = []
        for section in sections:
            try:
                # Создаем новый словарь для раздела
                formatted_section = {
                    "id": section.get("id", 0) if isinstance(section, dict) else 0,
                    "name": section.get("name", "") if isinstance(section, dict) else "",
                    "translations": {}
                }
                
                # Преобразуем список переводов в словарь с ключами по языкам
                if isinstance(section, dict) and "translations" in section and isinstance(section["translations"], list):
                    for translation in section["translations"]:
                        if isinstance(translation, dict) and "lang" in translation:
                            lang = translation["lang"]
                            formatted_section["translations"][lang] = {
                                "name": translation.get("name", ""),
                                "description": translation.get("description", "")
                            }
                
                formatted_sections.append(formatted_section)
                logger.info(f"Converted section: {formatted_section}")
            except Exception as e:
                logger.error(f"Error converting section: {e}")
                # Добавляем пустой раздел в случае ошибки
                formatted_sections.append({
                    "id": 0,
                    "name": "Error Section",
                    "translations": {"UKR": {"name": "Error Section", "description": ""}}
                })
        
        logger.info(f"Formatted sections: {len(formatted_sections)}")
        logger.info(f"Procedures: {len(procedures)}")
        
        return templates.TemplateResponse("procedures.html", {
            "request": request,
            "active_page": "procedures",
            "procedures": procedures,
            "sections": formatted_sections
        })
    except Exception as e:
        logger.error(f"Error in admin_procedures: {e}")
        # Возвращаем пустые списки вместо ошибки
        return templates.TemplateResponse("procedures.html", {
            "request": request,
            "active_page": "procedures",
            "procedures": [],
            "sections": []
        })

# Эндпоинты для рабочих мест
@app.get("/api/v2/workplaces", response_model=APIResponse[List[schemas.WorkplaceResponse]])
async def read_workplaces(db: AsyncSession = Depends(get_db)):
    """
    Получение всех рабочих мест
    """
    try:
        workplaces = await crud.get_workplaces(db)
        return APIResponse.success_response(
            data=workplaces,
            message=f"Retrieved {len(workplaces)} workplaces"
        )
    except Exception as e:
        logger.error(f"Error in read_workplaces: {e}")
        raise

@app.get("/api/v2/workplaces/{workplace_id}", response_model=APIResponse[schemas.WorkplaceResponse])
async def read_workplace(
    workplace_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получение рабочего места по ID
    """
    try:
        workplace = await crud.get_workplace_by_id(db, workplace_id)
        if workplace is None:
            raise HTTPException(status_code=404, detail=f"Workplace with ID {workplace_id} not found")
        
        return APIResponse.success_response(
            data=workplace,
            message=f"Retrieved workplace with ID {workplace_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in read_workplace: {e}")
        raise

@app.post("/api/v2/workplaces", response_model=APIResponse[schemas.WorkplaceResponse])
async def create_workplace(
    workplace: schemas.WorkplaceCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Создание нового рабочего места
    """
    try:
        workplace_data = workplace.dict()
        new_workplace = await crud.create_workplace(db, workplace_data)
        
        if new_workplace is None:
            raise HTTPException(status_code=500, detail="Failed to create workplace")
        
        await crud.log_admin_action(db, current_admin.id, "create_workplace", f"Created workplace: {new_workplace['name']}")
        
        return APIResponse.success_response(
            data=new_workplace,
            message="Workplace created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_workplace: {e}")
        raise

@app.put("/api/v2/workplaces/{workplace_id}", response_model=APIResponse[schemas.WorkplaceResponse])
async def update_workplace(
    workplace_id: int,
    workplace: schemas.WorkplaceCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Обновление рабочего места
    """
    try:
        workplace_data = workplace.dict()
        updated_workplace = await crud.update_workplace(db, workplace_id, workplace_data)
        
        if updated_workplace is None:
            raise HTTPException(status_code=404, detail=f"Workplace with ID {workplace_id} not found")
        
        await crud.log_admin_action(db, current_admin.id, "update_workplace", f"Updated workplace: {updated_workplace['name']}")
        
        return APIResponse.success_response(
            data=updated_workplace,
            message="Workplace updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_workplace: {e}")
        raise

@app.delete("/api/v2/workplaces/{workplace_id}", response_model=APIResponse[Dict[str, Any]])
async def delete_workplace(
    workplace_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Удаление рабочего места
    """
    try:
        # Получаем информацию о рабочем месте для лога
        workplace = await crud.get_workplace_by_id(db, workplace_id)
        if workplace is None:
            raise HTTPException(status_code=404, detail=f"Workplace with ID {workplace_id} not found")
        
        success = await crud.delete_workplace(db, workplace_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete workplace")
        
        await crud.log_admin_action(db, current_admin.id, "delete_workplace", f"Deleted workplace: {workplace['name']}")
        
        return APIResponse.success_response(
            data={"id": workplace_id},
            message="Workplace deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_workplace: {e}")
        raise

# Эндпоинты для рабочих слотов
@app.get("/api/v2/work_slots", response_model=APIResponse[List[Dict[str, Any]]])
async def read_work_slots(
    master_id: Optional[int] = Query(None, description="ID мастера для фильтрации"),
    start_date: Optional[datetime] = Query(None, description="Дата начала периода"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания периода"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Получение всех рабочих слотов с фильтрацией
    """
    try:
        # Импортируем модель WorkSlot внутри функции
        from src.database.models import WorkSlot
        work_slots = await crud.get_work_slots(db, master_id, start_date, end_date)
        return APIResponse.success_response(
            data=work_slots,
            message=f"Successfully retrieved {len(work_slots)} work slots"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.get("/api/v2/work_slots/{work_slot_id}", response_model=APIResponse[Dict[str, Any]])
async def read_work_slot(
    work_slot_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Получение рабочего слота по ID
    """
    try:
        # Импортируем модель WorkSlot внутри функции
        from src.database.models import WorkSlot
        work_slot = await crud.get_work_slot_by_id(db, work_slot_id)
        if not work_slot:
            return APIResponse.error_response(
                message=f"Work slot with ID {work_slot_id} not found",
                errors=[{"code": 404, "detail": f"Work slot with ID {work_slot_id} not found"}]
            )
        
        return APIResponse.success_response(
            data=work_slot,
            message=f"Successfully retrieved work slot with ID {work_slot_id}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.post("/api/v2/work_slots", response_model=APIResponse[Dict[str, Any]])
async def create_work_slot(
    work_slot: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Создание нового рабочего слота
    """
    try:
        # Импортируем модель WorkSlot внутри функции
        from src.database.models import WorkSlot
        # Проверяем наличие обязательных полей
        required_fields = ["master_id", "workplace_id", "start_time", "end_time"]
        for field in required_fields:
            if field not in work_slot:
                return APIResponse.error_response(
                    message=f"Missing required field: {field}",
                    errors=[{"code": 400, "detail": f"Missing required field: {field}"}]
                )
        
        # Создаем рабочий слот
        created_work_slot = await crud.create_work_slot(db, work_slot)
        if not created_work_slot:
            return APIResponse.error_response(
                message="Failed to create work slot",
                errors=[{"code": 500, "detail": "Failed to create work slot"}]
            )
        
        return APIResponse.success_response(
            data=created_work_slot,
            message=f"Work slot created successfully with ID {created_work_slot['id']}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.put("/api/v2/work_slots/{work_slot_id}", response_model=APIResponse[Dict[str, Any]])
async def update_work_slot(
    work_slot_id: int,
    work_slot: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Обновление рабочего слота
    """
    try:
        # Импортируем модель WorkSlot внутри функции
        from src.database.models import WorkSlot
        # Проверяем, существует ли рабочий слот
        existing_work_slot = await crud.get_work_slot_by_id(db, work_slot_id)
        if not existing_work_slot:
            return APIResponse.error_response(
                message=f"Work slot with ID {work_slot_id} not found",
                errors=[{"code": 404, "detail": f"Work slot with ID {work_slot_id} not found"}]
            )
        
        # Обновляем рабочий слот
        updated_work_slot = await crud.update_work_slot(db, work_slot_id, work_slot)
        if not updated_work_slot:
            return APIResponse.error_response(
                message="Failed to update work slot",
                errors=[{"code": 500, "detail": "Failed to update work slot"}]
            )
        
        return APIResponse.success_response(
            data=updated_work_slot,
            message=f"Work slot with ID {work_slot_id} updated successfully"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.delete("/api/v2/work_slots/{work_slot_id}", response_model=APIResponse[Dict[str, Any]])
async def delete_work_slot(
    work_slot_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Удаление рабочего слота
    """
    try:
        # Импортируем модель WorkSlot внутри функции
        from src.database.models import WorkSlot
        # Проверяем, существует ли рабочий слот
        existing_work_slot = await crud.get_work_slot_by_id(db, work_slot_id)
        if not existing_work_slot:
            return APIResponse.error_response(
                message=f"Work slot with ID {work_slot_id} not found",
                errors=[{"code": 404, "detail": f"Work slot with ID {work_slot_id} not found"}]
            )
        
        # Удаляем рабочий слот
        success = await crud.delete_work_slot(db, work_slot_id)
        if not success:
            return APIResponse.error_response(
                message="Failed to delete work slot",
                errors=[{"code": 500, "detail": "Failed to delete work slot. It may have associated appointments."}]
            )
        
        return APIResponse.success_response(
            data={"id": work_slot_id},
            message=f"Work slot with ID {work_slot_id} deleted successfully"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

# Эндпоинты для мастеров
@app.get("/api/v2/masters", response_model=APIResponse[List[schemas.MasterResponse]])
async def read_masters(db: AsyncSession = Depends(get_db)):
    """
    Получение всех мастеров
    """
    try:
        masters = await crud.get_masters(db)
        return APIResponse.success_response(
            data=masters,
            message="Masters retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in read_masters: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.get("/api/v2/masters/{master_id}", response_model=APIResponse[Dict[str, Any]])
async def read_master(master_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение мастера по ID
    """
    try:
        master = await crud.get_master_by_id(db, master_id)
        if not master:
            return APIResponse.error_response(
                message=f"Master with ID {master_id} not found",
                errors=[{"code": 404, "detail": "Master not found"}]
            )
        
        return APIResponse.success_response(
            data=master,
            message=f"Master with ID {master_id} retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in read_master: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.get("/api/masters/{master_id}", response_model=APIResponse[Dict[str, Any]])
async def read_master_v1(master_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """
    Получение мастера по ID (старая версия API)
    """
    try:
        master = await crud.get_master_by_id(db, master_id)
        if not master:
            return APIResponse.error_response(
                message=f"Master with ID {master_id} not found",
                errors=[{"code": 404, "detail": "Master not found"}]
            )
        
        return APIResponse.success_response(
            data=master,
            message=f"Master with ID {master_id} retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in read_master_v1: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.post("/api/masters", response_model=APIResponse[Dict[str, Any]])
async def create_master(master: schemas.MasterCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """
    Создание нового мастера
    """
    try:
        master_data = master.dict()
        result = await crud.create_master(db, master_data)
        
        if result is None:
            return APIResponse.error_response(
                message="Failed to create master",
                errors=[{"code": 500, "detail": "Failed to create master"}]
            )
        
        return APIResponse.success_response(
            data=result,
            message="Master created successfully"
        )
    except Exception as e:
        logger.error(f"Error in create_master: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.put("/api/masters/{master_id}", response_model=APIResponse[Dict[str, Any]])
async def update_master(master_id: int, master: schemas.MasterCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """
    Обновление мастера
    """
    try:
        master_data = master.dict()
        result = await crud.update_master(db, master_id, master_data)
        
        if result is None:
            return APIResponse.error_response(
                message=f"Master with ID {master_id} not found",
                errors=[{"code": 404, "detail": "Master not found"}]
            )
        
        return APIResponse.success_response(
            data=result,
            message=f"Master with ID {master_id} updated successfully"
        )
    except Exception as e:
        logger.error(f"Error in update_master: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

@app.delete("/api/masters/{master_id}", response_model=APIResponse[Dict[str, Any]])
async def delete_master(master_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """
    Удаление мастера
    """
    try:
        result = await crud.delete_master(db, master_id)
        
        if not result:
            return APIResponse.error_response(
                message=f"Master with ID {master_id} not found or cannot be deleted",
                errors=[{"code": 404, "detail": "Master not found or cannot be deleted"}]
            )
        
        return APIResponse.success_response(
            data={"id": master_id},
            message=f"Master with ID {master_id} deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error in delete_master: {e}")
        return APIResponse.error_response(
            message="Internal server error",
            errors=[{"code": 500, "detail": str(e)}]
        )

# Эндпоинты для клиентов
@app.get("/api/clients", response_model=APIResponse)
async def read_clients(db: AsyncSession = Depends(get_db)):
    """
    Получение всех клиентов
    """
    try:
        clients = await crud.get_clients(db)
        return APIResponse(
            status="success",
            message="Список клиентов получен успешно",
            data=clients
        )
    except Exception as e:
        logger.error(f"Error in read_clients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка клиентов"
        )

@app.get("/api/clients/{client_id}", response_model=APIResponse)
async def read_client(client_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение клиента по ID
    """
    try:
        client = await crud.get_client_by_id(db, client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Клиент с ID {client_id} не найден"
            )
        
        return APIResponse(
            status="success",
            message="Клиент получен успешно",
            data=client
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in read_client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении клиента"
        )

@app.post("/api/clients", response_model=APIResponse)
async def create_client(
    client: schemas.ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание нового клиента
    """
    try:
        client_data = client.dict()
        new_client = await crud.create_client(db, client_data)
        
        if not new_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при создании клиента. Возможно, клиент с таким телефоном уже существует."
            )
        
        # Логирование действия отключено для упрощения
        
        return APIResponse(
            status="success",
            message="Клиент успешно создан",
            data=new_client
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании клиента"
        )

@app.put("/api/clients/{client_id}", response_model=APIResponse)
async def update_client(
    client_id: int,
    client: schemas.ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление клиента
    """
    try:
        client_data = client.dict()
        updated_client = await crud.update_client(db, client_id, client_data)
        
        if not updated_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Клиент с ID {client_id} не найден или не может быть обновлен"
            )
        
        # Логирование действия отключено для упрощения
        
        return APIResponse(
            status="success",
            message="Клиент успешно обновлен",
            data=updated_client
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении клиента"
        )

@app.delete("/api/clients/{client_id}", response_model=APIResponse)
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление клиента
    """
    try:
        # Получаем информацию о клиенте перед удалением
        client = await crud.get_client_by_id(db, client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Клиент с ID {client_id} не найден"
            )
        
        # Пытаемся удалить клиента
        result = await crud.delete_client(db, client_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить клиента, так как у него есть связанные записи"
            )
        
        # Логирование действия отключено для упрощения
        
        return APIResponse(
            status="success",
            message="Клиент успешно удален",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении клиента"
        )

# Эндпоинты для записей
@app.get("/api/v2/appointments", response_model=APIResponse)
async def read_appointments_v2(
    client_id: Optional[int] = Query(None, description="ID клиента для фильтрации"),
    master_id: Optional[int] = Query(None, description="ID мастера для фильтрации"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение всех записей с фильтрацией (v2)
    """
    return await read_appointments(client_id, master_id, db)

@app.get("/api/appointments", response_model=APIResponse)
async def read_appointments(
    client_id: Optional[int] = Query(None, description="ID клиента для фильтрации"),
    master_id: Optional[int] = Query(None, description="ID мастера для фильтрации"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение всех записей с фильтрацией
    """
    try:
        appointments = await crud.get_appointments(db, client_id, master_id)
        return APIResponse(
            status="success",
            message="Список записей получен успешно",
            data=appointments
        )
    except Exception as e:
        logger.error(f"Error in read_appointments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка записей"
        )

@app.get("/api/v2/appointments/{appointment_id}", response_model=APIResponse)
async def read_appointment_v2(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение записи по ID (v2)
    """
    return await read_appointment(appointment_id, db)

@app.get("/api/appointments/{appointment_id}", response_model=APIResponse)
async def read_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение записи по ID
    """
    try:
        logger.info(f"Getting appointment with ID: {appointment_id}")
        appointment = await crud.get_appointment_by_id(db, appointment_id)
        logger.info(f"Appointment data: {appointment}")
        
        if not appointment:
            logger.error(f"Appointment with ID {appointment_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Запись с ID {appointment_id} не найдена"
            )
        
        response = APIResponse(
            status="success",
            message="Запись получена успешно",
            data=appointment
        )
        logger.info(f"Response data: {response.dict()}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in read_appointment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении записи"
        )

@app.post("/api/v2/appointments", response_model=APIResponse)
async def create_appointment_v2(appointment_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Создание новой записи (v2)
    """
    return await create_appointment(appointment_data, db)

@app.post("/api/appointments", response_model=APIResponse)
async def create_appointment(appointment_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Создание новой записи
    """
    try:
        # Преобразуем строковые даты в объекты datetime
        if "start_time" in appointment_data and isinstance(appointment_data["start_time"], str):
            appointment_data["start_time"] = datetime.fromisoformat(appointment_data["start_time"].replace('Z', '+00:00'))
        if "end_time" in appointment_data and isinstance(appointment_data["end_time"], str):
            appointment_data["end_time"] = datetime.fromisoformat(appointment_data["end_time"].replace('Z', '+00:00'))
        
        # Преобразуем строковые ID в целые числа
        if "client_id" in appointment_data and isinstance(appointment_data["client_id"], str):
            appointment_data["client_id"] = int(appointment_data["client_id"])
        if "master_id" in appointment_data and isinstance(appointment_data["master_id"], str):
            appointment_data["master_id"] = int(appointment_data["master_id"])
        if "workplace_id" in appointment_data and isinstance(appointment_data["workplace_id"], str):
            appointment_data["workplace_id"] = int(appointment_data["workplace_id"])
        
        # Преобразуем строковые ID процедур в целые числа
        if "procedures" in appointment_data:
            if isinstance(appointment_data["procedures"], str):
                appointment_data["procedures"] = [int(p) for p in appointment_data["procedures"].split(',')]
            elif isinstance(appointment_data["procedures"], list):
                appointment_data["procedures"] = [int(p) if isinstance(p, str) else p for p in appointment_data["procedures"]]
        
        new_appointment = await crud.create_appointment(db, appointment_data)
        
        if not new_appointment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при создании записи. Проверьте правильность введенных данных."
            )
        
        return APIResponse(
            status="success",
            message="Запись успешно создана",
            data=new_appointment
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_appointment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании записи"
        )

@app.put("/api/v2/appointments/{appointment_id}", response_model=APIResponse)
async def update_appointment_v2(appointment_id: int, appointment_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Обновление записи (v2)
    """
    return await update_appointment(appointment_id, appointment_data, db)

@app.put("/api/appointments/{appointment_id}", response_model=APIResponse)
async def update_appointment(appointment_id: int, appointment_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Обновление записи
    """
    try:
        # Преобразуем строковые даты в объекты datetime
        if "start_time" in appointment_data and isinstance(appointment_data["start_time"], str):
            appointment_data["start_time"] = datetime.fromisoformat(appointment_data["start_time"].replace('Z', '+00:00'))
        if "end_time" in appointment_data and isinstance(appointment_data["end_time"], str):
            appointment_data["end_time"] = datetime.fromisoformat(appointment_data["end_time"].replace('Z', '+00:00'))
        
        # Преобразуем строковые ID в целые числа
        if "client_id" in appointment_data and isinstance(appointment_data["client_id"], str):
            appointment_data["client_id"] = int(appointment_data["client_id"])
        if "master_id" in appointment_data and isinstance(appointment_data["master_id"], str):
            appointment_data["master_id"] = int(appointment_data["master_id"])
        if "workplace_id" in appointment_data and isinstance(appointment_data["workplace_id"], str):
            appointment_data["workplace_id"] = int(appointment_data["workplace_id"])
        
        # Преобразуем строковые ID процедур в целые числа
        if "procedures" in appointment_data:
            if isinstance(appointment_data["procedures"], str):
                appointment_data["procedures"] = [int(p) for p in appointment_data["procedures"].split(',')]
            elif isinstance(appointment_data["procedures"], list):
                appointment_data["procedures"] = [int(p) if isinstance(p, str) else p for p in appointment_data["procedures"]]
        
        updated_appointment = await crud.update_appointment(db, appointment_id, appointment_data)
        
        if not updated_appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Запись с ID {appointment_id} не найдена или не может быть обновлена"
            )
        
        return APIResponse(
            status="success",
            message="Запись успешно обновлена",
            data=updated_appointment
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_appointment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении записи"
        )

@app.delete("/api/v2/appointments/{appointment_id}", response_model=APIResponse)
async def delete_appointment_v2(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаление записи (v2)
    """
    return await delete_appointment(appointment_id, db)

@app.get("/api/appointment_edit/{appointment_id}", response_model=APIResponse)
async def get_appointment_for_edit(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение данных о записи для редактирования
    """
    try:
        logger.info(f"Getting appointment for edit with ID: {appointment_id}")
        # Получаем запись из базы данных
        query = select(Appointment).where(Appointment.id == appointment_id)
        result = await db.execute(query)
        appointment = result.scalars().first()
        
        if not appointment:
            logger.error(f"Appointment with ID {appointment_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Запись с ID {appointment_id} не найдена"
            )
        
        # Формируем упрощенный объект для редактирования
        edit_data = {
            "id": appointment.id,
            "client_id": appointment.client_id,
            "master_id": appointment.master_id,
            "workplace_id": appointment.workplace_id,
            "procedures": appointment.procedures,
            "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
            "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
            "status": appointment.status.value
        }
        
        logger.info(f"Edit data: {edit_data}")
        
        return APIResponse(
            status="success",
            message="Данные для редактирования получены успешно",
            data=edit_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_appointment_for_edit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении данных для редактирования"
        )

@app.delete("/api/appointments/{appointment_id}", response_model=APIResponse)
async def delete_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаление записи
    """
    try:
        # Проверяем наличие записи
        appointment = await crud.get_appointment_by_id(db, appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Запись с ID {appointment_id} не найдена"
            )
        
        # Удаляем запись
        result = await crud.delete_appointment(db, appointment_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить запись"
            )
        
        return APIResponse(
            status="success",
            message="Запись успешно удалена",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_appointment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении записи"
        )

# Инициализация индексов при запуске приложения
@app.on_event("startup")
async def startup_event():
    """
    Действия при запуске приложения
    """
    try:
        async with AsyncSession() as session:
            await crud.add_database_indexes(session)
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
