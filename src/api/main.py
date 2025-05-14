from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

from src.database.base import get_db
from src.database import crud
from src.api import schemas

load_dotenv()

# Security settings
SECRET_KEY = os.getenv("API_SECRET_KEY", "your_secret_key_for_jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Beauty Salon API", description="API for Beauty Salon Management")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    admin = await crud.get_admin_by_telegram_id(db, int(form_data.username))
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
    return {"access_token": access_token, "token_type": "bearer"}


# Client endpoints
@app.post("/clients/", response_model=schemas.ClientResponse)
async def create_client(client: schemas.ClientCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    db_client = await crud.get_client_by_telegram_id(db, client.telegram_id)
    if db_client:
        raise HTTPException(status_code=400, detail="Client already registered")
    return await crud.create_client(db, client.dict())


@app.get("/clients/{telegram_id}", response_model=schemas.ClientResponse)
async def read_client(telegram_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    db_client = await crud.get_client_by_telegram_id(db, telegram_id)
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client


@app.put("/clients/{client_id}", response_model=schemas.ClientResponse)
async def update_client(client_id: int, client: schemas.ClientUpdate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    updated_client = await crud.update_client(db, client_id, client.dict(exclude_unset=True))
    if updated_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return updated_client


# Section endpoints
@app.post("/sections/", response_model=schemas.SectionResponse)
async def create_section(section: schemas.SectionCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    translations = [t.dict() for t in section.translations]
    return await crud.create_section(db, {}, translations)


@app.get("/sections/", response_model=List[schemas.SectionResponse])
async def read_sections(lang: schemas.LanguageEnum = schemas.LanguageEnum.UKR, db: AsyncSession = Depends(get_db)):
    return await crud.get_sections(db, lang.value)


# Procedure endpoints
@app.post("/procedures/", response_model=schemas.ProcedureResponse)
async def create_procedure(procedure: schemas.ProcedureCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    procedure_data = procedure.dict(exclude={"translations"})
    translations = [t.dict() for t in procedure.translations]
    return await crud.create_procedure(db, procedure_data, translations)


@app.get("/procedures/section/{section_id}", response_model=List[schemas.ProcedureResponse])
async def read_procedures_by_section(section_id: int, lang: schemas.LanguageEnum = schemas.LanguageEnum.UKR, db: AsyncSession = Depends(get_db)):
    return await crud.get_procedures_by_section(db, section_id, lang.value)


# Master endpoints
@app.post("/masters/", response_model=schemas.MasterResponse)
async def create_master(master: schemas.MasterCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    master_data = master.dict(exclude={"procedures"})
    db_master = await crud.create_master(db, master_data)
    
    # Assign procedures to master if provided
    if master.procedures:
        for procedure_id in master.procedures:
            await crud.assign_procedure_to_master(db, db_master.id, procedure_id)
    
    return db_master


@app.get("/masters/", response_model=List[schemas.MasterResponse])
async def read_masters(db: AsyncSession = Depends(get_db)):
    return await crud.get_masters(db)


@app.get("/masters/procedures/{procedure_ids}", response_model=List[schemas.MasterResponse])
async def read_masters_by_procedures(procedure_ids: str, db: AsyncSession = Depends(get_db)):
    procedure_id_list = [int(pid) for pid in procedure_ids.split(",")]
    return await crud.get_masters_by_procedures(db, procedure_id_list)


# Workplace endpoints
@app.post("/workplaces/", response_model=schemas.WorkplaceResponse)
async def create_workplace(workplace: schemas.WorkplaceCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    return await crud.create_workplace(db, workplace.dict())


@app.get("/workplaces/", response_model=List[schemas.WorkplaceResponse])
async def read_workplaces(db: AsyncSession = Depends(get_db)):
    return await crud.get_workplaces(db)


# WorkSlot endpoints
@app.post("/work-slots/", response_model=schemas.WorkSlotResponse)
async def create_work_slot(work_slot: schemas.WorkSlotCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    return await crud.create_work_slot(db, work_slot.dict())


@app.get("/work-slots/master/{master_id}", response_model=List[schemas.WorkSlotResponse])
async def read_master_work_slots(
    master_id: int, 
    start_date: str, 
    end_date: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return await crud.get_master_work_slots(db, master_id, start, end)


# Appointment endpoints
@app.post("/appointments/", response_model=schemas.AppointmentResponse)
async def create_appointment(appointment: schemas.AppointmentCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    return await crud.create_appointment(db, appointment.dict())


@app.get("/appointments/client/{client_id}", response_model=List[schemas.AppointmentResponse])
async def read_client_appointments(
    client_id: int, 
    status: Optional[schemas.AppointmentStatusEnum] = None, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    return await crud.get_client_appointments(db, client_id, status.value if status else None)


@app.get("/appointments/master/{master_id}", response_model=List[schemas.AppointmentResponse])
async def read_master_appointments(
    master_id: int, 
    start_date: str, 
    end_date: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return await crud.get_master_appointments(db, master_id, start, end)


@app.put("/appointments/{appointment_id}", response_model=schemas.AppointmentResponse)
async def update_appointment_status(
    appointment_id: int, 
    status_update: schemas.AppointmentUpdate, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    updated_appointment = await crud.update_appointment_status(db, appointment_id, status_update.status)
    if updated_appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return updated_appointment


# Slot generation endpoints
@app.get("/slots/available", response_model=schemas.AvailableSlotsResponse)
async def get_available_slots(
    master_id: int,
    date: str,
    procedures: str,
    client_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    procedure_ids = [int(pid) for pid in procedures.split(",")]
    appointment_date = datetime.fromisoformat(date)
    
    # Get client info if provided
    client_time_coeff = 1.0
    is_first_visit = True
    if client_id:
        client = await crud.get_client_by_id(db, client_id)
        if client:
            client_time_coeff = client.time_coeff
            is_first_visit = client.is_first_visit
    
    # Calculate appointment duration
    duration_minutes = await crud.calculate_appointment_duration(
        db, procedure_ids, client_time_coeff, is_first_visit
    )
    
    # Get available slots
    slots = await crud.get_available_slots(db, master_id, appointment_date, duration_minutes)
    
    return {"slots": slots}


# Admin endpoints
@app.post("/admins/", response_model=schemas.AdminResponse)
async def create_admin(
    admin: schemas.AdminCreate, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    # Only superadmins can create new admins
    if not current_admin.is_superadmin:
        raise HTTPException(status_code=403, detail="Not authorized to create admins")
    
    db_admin = await crud.get_admin_by_telegram_id(db, admin.telegram_id)
    if db_admin:
        raise HTTPException(status_code=400, detail="Admin already registered")
    
    admin_data = admin.dict(exclude={"password"})
    admin_data["password_hash"] = get_password_hash(admin.password)
    
    return await crud.create_admin(db, admin_data)


@app.get("/admin-logs/", response_model=List[schemas.AdminLogResponse])
async def read_admin_logs(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    # Only superadmins can view all logs
    if not current_admin.is_superadmin:
        raise HTTPException(status_code=403, detail="Not authorized to view all logs")
    
    return await crud.get_admin_logs(db, skip, limit)


@app.get("/admin-logs/admin/{admin_id}", response_model=List[schemas.AdminLogResponse])
async def read_admin_logs_by_admin(
    admin_id: int,
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    # Admins can only view their own logs unless they are superadmins
    if not current_admin.is_superadmin and current_admin.id != admin_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these logs")
    
    return await crud.get_admin_logs_by_admin(db, admin_id, skip, limit)


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Beauty Salon API is running"}
