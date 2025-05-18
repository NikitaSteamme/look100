"""
API Client for interacting with the Beauty Salon API.
Handles all HTTP requests, error handling, and response parsing.
"""
import aiohttp
import logging
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ApiError(Exception):
    """Custom exception for API errors"""
    def __init__(self, status: int, message: str, details: Optional[Dict] = None):
        self.status = status
        self.message = message
        self.details = details or {}
        super().__init__(f"API Error {status}: {message}")

class BeautySalonApiClient:
    """Client for interacting with the Beauty Salon API"""
    
    def __init__(self, base_url: str = None, api_key: str = None, timeout: int = 30):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the API (defaults to API_BASE_URL env var or http://localhost:8000)
            api_key: API key for authentication (defaults to API_KEY env var)
            timeout: Request timeout in seconds
        """
        # When running in Docker, use the service name 'api' instead of 'localhost'
        default_url = "http://api:8000" if os.getenv("DOCKER", "false").lower() == "true" else "http://localhost:8000"
        self.base_url = base_url or os.getenv("API_BASE_URL", default_url)
        self.api_key = api_key or os.getenv("API_KEY")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self, headers: Optional[Dict] = None) -> Dict:
        """Get default headers with optional overrides"""
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            default_headers["Authorization"] = f"Bearer {self.api_key}"
        
        if headers:
            default_headers.update(headers)
            
        return default_headers
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Union[Dict, List]] = None,
        headers: Optional[Dict] = None
    ) -> Any:
        """Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/api/sections')
            params: Query parameters
            json_data: JSON data for POST/PUT requests
            headers: Additional headers
            
        Returns:
            Parsed JSON response
            
        Raises:
            ApiError: If the API returns an error status code
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")
            
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers(headers)
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers
            ) as response:
                response_data = await response.text()
                
                try:
                    response_json = json.loads(response_data) if response_data else {}
                except json.JSONDecodeError:
                    response_json = {"detail": response_data}
                
                if not response.ok:
                    logger.error(
                        "API request failed: %s %s - %s",
                        response.status,
                        response.reason,
                        response_json
                    )
                    raise ApiError(
                        status=response.status,
                        message=response_json.get("detail", response.reason),
                        details=response_json
                    )
                
                return response_json
                
        except aiohttp.ClientError as e:
            logger.exception("API request failed")
            raise ApiError(500, f"Network error: {str(e)}")
    
    # API Endpoint Methods
    
    # Sections
    async def get_sections(self, lang: str = "ru") -> List[Dict]:
        """Get all sections"""
        return await self._make_request("GET", f"/api/v2/sections?lang={lang}")
    
    async def get_section(self, section_id: int, lang: str = "ru") -> Dict:
        """Get a section by ID"""
        return await self._make_request("GET", f"/api/v2/sections/{section_id}?lang={lang}")
    
    # Procedures
    async def get_procedures(self, section_id: Optional[int] = None, lang: str = "ru") -> List[Dict]:
        """Get procedures, optionally filtered by section"""
        endpoint = f"/api/v2/procedures?lang={lang}"
        if section_id is not None:
            endpoint += f"&section_id={section_id}"
        return await self._make_request("GET", endpoint)
    
    async def get_procedure(self, procedure_id: int, lang: str = "ru") -> Dict:
        """Get a procedure by ID"""
        return await self._make_request("GET", f"/api/v2/procedures/{procedure_id}?lang={lang}")
    
    # Appointments
    async def get_appointments(
        self,
        client_id: Optional[int] = None,
        master_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get appointments with optional filters"""
        params = {}
        if client_id is not None:
            params["client_id"] = client_id
        if master_id is not None:
            params["master_id"] = master_id
        if start_date is not None:
            params["start_date"] = start_date.isoformat()
        if end_date is not None:
            params["end_date"] = end_date.isoformat()
        if status is not None:
            params["status"] = status
            
        return await self._make_request("GET", "/api/appointments", params=params)
    
    async def create_appointment(self, appointment_data: Dict) -> Dict:
        """Create a new appointment"""
        return await self._make_request("POST", "/api/appointments", json_data=appointment_data)
    
    async def update_appointment(self, appointment_id: int, update_data: Dict) -> Dict:
        """Update an existing appointment"""
        return await self._make_request("PUT", f"/api/appointments/{appointment_id}", json_data=update_data)
    
    async def cancel_appointment(self, appointment_id: int) -> Dict:
        """Cancel an appointment"""
        return await self._make_request("POST", f"/api/appointments/{appointment_id}/cancel")
    
    # Masters
    async def get_masters(self, lang: str = "ru") -> List[Dict]:
        """Get all masters"""
        return await self._make_request("GET", f"/api/v2/masters?lang={lang}")
    
    async def get_masters_for_procedures(self, procedure_ids: List[int], lang: str = "ru") -> List[Dict]:
        """Get masters who can perform the specified procedures"""
        try:
            # Сначала получаем всех мастеров
            response = await self._make_request("GET", f"/api/v2/masters?lang={lang}")
            
            # Проверяем формат данных
            if isinstance(response, dict) and 'data' in response:
                masters = response['data']
            else:
                masters = response
                
            if not masters or not isinstance(masters, list):
                return []
                
            # Фильтруем мастеров, которые могут выполнять все выбранные процедуры
            filtered_masters = []
            for master in masters:
                # Проверяем, что мастер может выполнять все выбранные процедуры
                if isinstance(master, dict) and 'procedures' in master:
                    master_procedures = master['procedures']
                    if all(proc_id in master_procedures for proc_id in procedure_ids):
                        filtered_masters.append(master)
                        
            return filtered_masters
        except Exception as e:
            logging.error(f"Error in get_masters_for_procedures: {str(e)}")
            # В случае ошибки возвращаем всех мастеров
            return await self.get_masters(lang=lang)
    
    async def get_master(self, master_id: int, lang: str = "ru") -> Dict:
        """Get a master by ID"""
        return await self._make_request("GET", f"/api/v2/masters/{master_id}?lang={lang}")
    
    # Work Slots
    async def get_available_slots(
        self,
        master_id: int,
        date: datetime,
        duration: int
    ) -> List[Dict]:
        """Get available time slots for a master"""
        return await self._make_request(
            "GET",
            "/api/work-slots/available",
            params={
                "master_id": master_id,
                "date": date.strftime("%Y-%m-%d"),
                "duration": duration
            }
        )

# Global instance for convenience
# When running in Docker, use the service name 'api' instead of 'localhost'
import os
base_url = os.getenv('API_BASE_URL', 'http://api:8000' if os.getenv('DOCKER', 'false').lower() == 'true' else 'http://localhost:8000')
api_client = BeautySalonApiClient(base_url=base_url)
