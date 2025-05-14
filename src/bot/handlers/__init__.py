from aiogram import Dispatcher

from .client import register_client_handlers
from .admin import register_admin_handlers


def register_all_handlers(dp: Dispatcher):
    """Register all handlers"""
    register_client_handlers(dp)
    register_admin_handlers(dp)
