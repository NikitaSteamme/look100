import os
import datetime
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_credentials():
    """Get valid user credentials from storage.

    Returns:
        Credentials, the obtained credential.
    """
    creds = None
    token_path = os.getenv("GOOGLE_CALENDAR_TOKEN", "token.json")
    credentials_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json")
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_info(
            json.load(open(token_path)), SCOPES
        )
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def get_calendar_service():
    """Get a Google Calendar service instance.

    Returns:
        A Google Calendar service instance.
    """
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)
    return service


async def create_calendar_event(
    summary: str,
    description: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    attendees: Optional[list] = None
) -> Dict[str, Any]:
    """Create a new calendar event.

    Args:
        summary: Event title
        description: Event description
        start_time: Start time of the event
        end_time: End time of the event
        attendees: List of attendee email addresses

    Returns:
        Created event details
    """
    service = get_calendar_service()
    
    # Format time for Google Calendar API
    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()
    
    # Prepare event data
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time_str,
            'timeZone': os.getenv("TIMEZONE", "Europe/Kiev"),
        },
        'end': {
            'dateTime': end_time_str,
            'timeZone': os.getenv("TIMEZONE", "Europe/Kiev"),
        },
    }
    
    # Add attendees if provided
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    # Create the event
    event = service.events().insert(calendarId='primary', body=event).execute()
    
    return event


async def update_calendar_event(
    event_id: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    attendees: Optional[list] = None
) -> Dict[str, Any]:
    """Update an existing calendar event.

    Args:
        event_id: ID of the event to update
        summary: New event title (optional)
        description: New event description (optional)
        start_time: New start time (optional)
        end_time: New end time (optional)
        attendees: New list of attendee email addresses (optional)

    Returns:
        Updated event details
    """
    service = get_calendar_service()
    
    # Get the existing event
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    
    # Update fields if provided
    if summary:
        event['summary'] = summary
    
    if description:
        event['description'] = description
    
    if start_time:
        start_time_str = start_time.isoformat()
        event['start'] = {
            'dateTime': start_time_str,
            'timeZone': os.getenv("TIMEZONE", "Europe/Kiev"),
        }
    
    if end_time:
        end_time_str = end_time.isoformat()
        event['end'] = {
            'dateTime': end_time_str,
            'timeZone': os.getenv("TIMEZONE", "Europe/Kiev"),
        }
    
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    # Update the event
    updated_event = service.events().update(
        calendarId='primary', eventId=event_id, body=event
    ).execute()
    
    return updated_event


async def delete_calendar_event(event_id: str) -> bool:
    """Delete a calendar event.

    Args:
        event_id: ID of the event to delete

    Returns:
        True if successful, False otherwise
    """
    service = get_calendar_service()
    
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False


async def get_calendar_event(event_id: str) -> Optional[Dict[str, Any]]:
    """Get a calendar event by ID.

    Args:
        event_id: ID of the event to get

    Returns:
        Event details or None if not found
    """
    service = get_calendar_service()
    
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        return event
    except Exception as e:
        print(f"Error getting event: {e}")
        return None
