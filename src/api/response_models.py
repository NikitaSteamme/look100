"""
Модели ответов API для унификации формата данных
"""
from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar('T')

class APIResponse(GenericModel, Generic[T]):
    """
    Базовый класс для всех ответов API
    """
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def success_response(cls, data: T, message: Optional[str] = None) -> 'APIResponse[T]':
        """
        Создает успешный ответ API
        """
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_response(cls, message: str, errors: Optional[List[Dict[str, Any]]] = None) -> 'APIResponse[T]':
        """
        Создает ответ API с ошибкой
        """
        return cls(success=False, message=message, errors=errors)

class TranslationModel(BaseModel):
    """
    Модель для представления перевода
    """
    lang: str
    name: str
    description: Optional[str] = None

class SectionResponseModel(BaseModel):
    """
    Модель для представления раздела
    """
    id: int
    name: str
    translations: List[TranslationModel]

class ProcedureResponseModel(BaseModel):
    """
    Модель для представления процедуры
    """
    id: int
    section_id: int
    section_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    duration: int
    base_price: float
    discount: float = 0
    translations: List[TranslationModel]
