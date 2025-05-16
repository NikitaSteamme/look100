from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, ARRAY, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .base import Base


class AppointmentStatus(enum.Enum):
    active = "active"
    canceled = "canceled"
    completed = "completed"


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(100), nullable=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    appointments = relationship("Appointment", back_populates="client")


class Section(Base):
    __tablename__ = "section"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    procedures = relationship("Procedure", back_populates="section")
    translations = relationship("SectionTranslation", back_populates="section")


class SectionTranslation(Base):
    __tablename__ = "section_translation"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("section.id", ondelete="CASCADE"))
    lang = Column(String(5), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    section = relationship("Section", back_populates="translations")


class Procedure(Base):
    __tablename__ = "procedure"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("section.id", ondelete="CASCADE"))
    duration = Column(Integer, nullable=False)  # in minutes
    base_price = Column(Float, nullable=False)
    discount = Column(Float, default=0)  # in percentage

    section = relationship("Section", back_populates="procedures")
    translations = relationship("ProcedureTranslation", back_populates="procedure")
    masters = relationship("MasterProcedure", back_populates="procedure")


class ProcedureTranslation(Base):
    __tablename__ = "procedure_translation"

    id = Column(Integer, primary_key=True, index=True)
    procedure_id = Column(Integer, ForeignKey("procedure.id", ondelete="CASCADE"))
    lang = Column(String(5), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    procedure = relationship("Procedure", back_populates="translations")


class Master(Base):
    __tablename__ = "master"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    telegram_username = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)

    procedures = relationship("MasterProcedure", back_populates="master")
    work_slots = relationship("WorkSlot", back_populates="master")
    appointments = relationship("Appointment", back_populates="master")


class MasterProcedure(Base):
    __tablename__ = "master_procedure"

    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(Integer, ForeignKey("master.id", ondelete="CASCADE"))
    procedure_id = Column(Integer, ForeignKey("procedure.id", ondelete="CASCADE"))

    master = relationship("Master", back_populates="procedures")
    procedure = relationship("Procedure", back_populates="masters")


class Workplace(Base):
    __tablename__ = "workplace"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    work_slots = relationship("WorkSlot", back_populates="workplace")
    appointments = relationship("Appointment", back_populates="workplace")


class WorkSlot(Base):
    __tablename__ = "work_slot"

    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(Integer, ForeignKey("master.id", ondelete="CASCADE"))
    workplace_id = Column(Integer, ForeignKey("workplace.id", ondelete="CASCADE"))
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    master = relationship("Master", back_populates="work_slots")
    workplace = relationship("Workplace", back_populates="work_slots")


class Appointment(Base):
    __tablename__ = "appointment"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="CASCADE"))
    master_id = Column(Integer, ForeignKey("master.id", ondelete="CASCADE"))
    workplace_id = Column(Integer, ForeignKey("workplace.id", ondelete="CASCADE"))
    procedures = Column(ARRAY(Integer), nullable=False)  # Array of procedure IDs
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.active)
    google_event_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="appointments")
    master = relationship("Master", back_populates="appointments")
    workplace = relationship("Workplace", back_populates="appointments")


class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    logs = relationship("AdminLog", back_populates="admin")


class AdminLog(Base):
    __tablename__ = "admin_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"))
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    details = Column(Text, nullable=True)

    admin = relationship("Admin", back_populates="logs")
