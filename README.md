# Beauty Salon Telegram Bot

A comprehensive Telegram bot for managing appointments in a beauty salon with client and admin functionalities.

## Features

### For Clients
- Language selection (Ukrainian, English, Portuguese, Russian)
- Service section and procedure selection
- Booking by master or time preference
- Appointment management (view, cancel)
- Automated notifications

### For Admins
- Workplace management
- Work schedule management for masters
- Appointment management
- Manual appointment creation
- Client search

### Technical Features
- PostgreSQL database for data storage
- Google Calendar integration for appointment synchronization
- FastAPI web interface for CRUD operations
- Docker containerization for easy deployment

## Project Structure

```
beauty-salon-bot/
├── docker-compose.yml     # Docker configuration
├── Dockerfile             # Docker build instructions
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── src/                   # Source code
│   ├── api/               # FastAPI web interface
│   ├── bot/               # Telegram bot
│   ├── database/          # Database models and operations
│   └── utils/             # Utility functions
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL
- Docker and Docker Compose (optional)
- Telegram Bot Token (from BotFather)
- Google Calendar API credentials (optional)

### Environment Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your configuration:
   ```
   cp .env.example .env
   ```
3. Edit the `.env` file with your credentials:
   - Telegram Bot Token
   - Database credentials
   - Admin Telegram IDs
   - Google Calendar credentials (optional)

### Installation

#### Using Docker (recommended)

1. Build and start the containers:
   ```
   docker-compose up -d
   ```

2. The bot and API will be automatically started.

#### Manual Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Start the bot:
   ```
   python -m src.bot.main
   ```

4. Start the API (in a separate terminal):
   ```
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

## Database Schema

The database includes the following main entities:
- Clients
- Masters
- Procedures
- Workplaces
- Work slots
- Appointments
- Admins

## API Documentation

The API documentation is available at `/docs` when the API is running.

## Bot Commands

- `/start` - Start the bot and select language
- `/my_appointments` - View your active appointments
- `/admin` - Access admin panel (for admins only)

## Development

### Adding New Features

1. Create new models in `src/database/models.py`
2. Add CRUD operations in `src/database/crud.py`
3. Add API endpoints in `src/api/main.py`
4. Add bot handlers in `src/bot/handlers/`

### Adding New Languages

Add new translations in `src/utils/translations.py`.

## License

This project is licensed under the MIT License.
