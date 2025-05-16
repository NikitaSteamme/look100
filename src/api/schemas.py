from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class LanguageEnum(str, Enum):
    UKR = "UKR"
    ENG = "ENG"
    POR = "POR"
    RUS = "RUS"


class AppointmentStatusEnum(str, Enum):
    active = "active"
    canceled = "canceled"
    completed = "completed"


class ClientBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    telegram_id: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    telegram_id: Optional[str] = None


class ClientResponse(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TranslationBase(BaseModel):
    lang: LanguageEnum
    name: str


class SectionTranslationCreate(TranslationBase):
    pass


class SectionCreate(BaseModel):
    translations: List[SectionTranslationCreate]


class SectionResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class ProcedureTranslationBase(TranslationBase):
    description: Optional[str] = None


class ProcedureTranslationCreate(ProcedureTranslationBase):
    pass


class ProcedureBase(BaseModel):
    section_id: int
    duration: int
    base_price: float
    discount: float = 0


class ProcedureCreate(ProcedureBase):
    translations: List[ProcedureTranslationCreate]


class ProcedureResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    duration: int
    base_price: float
    discount: float

    class Config:
        orm_mode = True


class MasterBase(BaseModel):
    name: str
    telegram_username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class MasterCreate(MasterBase):
    procedures: Optional[List[int]] = None


class MasterResponse(MasterBase):
    id: int
    procedures: List[int] = []

    class Config:
        orm_mode = True


class WorkplaceBase(BaseModel):
    name: str


class WorkplaceCreate(WorkplaceBase):
    pass


class WorkplaceResponse(WorkplaceBase):
    id: int

    class Config:
        orm_mode = True


class WorkSlotBase(BaseModel):
    master_id: int
    workplace_id: int
    date: datetime
    start_time: datetime
    end_time: datetime


class WorkSlotCreate(WorkSlotBase):
    pass


class WorkSlotResponse(WorkSlotBase):
    id: int

    class Config:
        orm_mode = True


class AppointmentBase(BaseModel):
    client_id: int
    master_id: int
    workplace_id: int
    procedures: List[int]
    start_time: datetime
    end_time: datetime
    google_event_id: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    status: AppointmentStatusEnum


class AppointmentResponse(AppointmentBase):
    id: int
    status: AppointmentStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class AdminBase(BaseModel):
    telegram_id: int
    username: str


class AdminCreate(AdminBase):
    password: str


class AdminResponse(AdminBase):
    id: int
    is_superadmin: bool
    created_at: datetime

    class Config:
        orm_mode = True


class AdminLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    timestamp: datetime
    details: Optional[str] = None

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class SlotResponse(BaseModel):
    time: datetime


class AvailableSlotsResponse(BaseModel):
    slots: List[datetime]
