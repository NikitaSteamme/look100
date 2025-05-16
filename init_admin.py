import asyncio
import os
from passlib.context import CryptContext
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import AsyncSessionLocal
from src.database import models, crud

# Загрузка переменных окружения
load_dotenv()

# Настройки безопасности
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Получение данных администратора из .env
ADMIN_IDS = os.getenv("ADMIN_IDS", "123456789").split(",")
ADMIN_PASSWORD = os.getenv("API_ADMIN_PASSWORD", "admin_password")

# Функция для хеширования пароля
def get_password_hash(password):
    return pwd_context.hash(password)

async def init_admin():
    """Инициализация администратора в базе данных"""
    async with AsyncSessionLocal() as session:
        # Проверка наличия администратора
        for admin_id in ADMIN_IDS:
            admin_id = int(admin_id.strip())
            admin = await crud.get_admin_by_telegram_id(session, admin_id)
            
            if not admin:
                print(f"Создание администратора с Telegram ID: {admin_id}")
                # Создание нового администратора
                admin_obj = models.Admin(
                    telegram_id=admin_id,
                    username=f"admin_{admin_id}",
                    password_hash=get_password_hash(ADMIN_PASSWORD),
                    is_superadmin=True
                )
                session.add(admin_obj)
                await session.commit()
                print(f"Администратор создан успешно!")
            else:
                print(f"Администратор с Telegram ID {admin_id} уже существует.")
                # Обновление пароля
                admin.password_hash = get_password_hash(ADMIN_PASSWORD)
                await session.commit()
                print(f"Пароль администратора обновлен.")

if __name__ == "__main__":
    asyncio.run(init_admin())
