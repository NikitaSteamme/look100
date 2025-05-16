from aiogram import Dispatcher, BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any, Awaitable, Callable, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import AsyncSessionLocal
from src.database import crud


class DatabaseMiddleware(BaseMiddleware):
    """Middleware for injecting database session into handler data"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Middleware for loading user data from database"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Check if we have user info in the event
        if hasattr(event, "from_user") and event.from_user:
            telegram_id = event.from_user.id
            session = data.get("session")
            
            if session:
                # Try to get client from database
                client = await crud.get_client_by_telegram_id(session, telegram_id)
                data["client"] = client
                
                # Check if user is admin
                admin = await crud.get_admin_by_telegram_id(session, telegram_id)
                data["admin"] = admin
        
        return await handler(event, data)


def register_all_middlewares(dp: Dispatcher):
    """Register all middlewares"""
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(UserMiddleware())
