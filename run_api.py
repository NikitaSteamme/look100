"""
Скрипт для запуска API Beauty Salon Bot
"""
import uvicorn
import logging
from src.api.main import app

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

if __name__ == "__main__":
    logger.info("Starting Beauty Salon API")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
