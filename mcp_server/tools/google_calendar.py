"""
Google Calendar tool for MCP server.

Provides comprehensive Google Calendar integration with OAuth2 authentication.
Supports event management, conflict detection, smart scheduling, and meeting preparation.
"""

import os
import json
import pickle
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import asyncio
from pathlib import Path
import logging
from . import BaseTool

logger = logging.getLogger(__name__)

# OAuth2 scopes for Google Calendar
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

class GoogleCalendarTool(BaseTool):
    """Google Calendar integration tool with OAuth2 authentication."""
    
    def __init__(self):
        super().__init__("google_calendar")
        self.credentials_path = Path("credentials/google_credentials.json")
        self.token_path = Path("credentials/google_token.pickle")
        self.service = None
        
        # Ensure credentials directory exists
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB collections for calendar intelligence
        self._init_chroma_collections()
        
    def _init_chroma_collections(self):
        """Initialize ChromaDB collections for calendar intelligence."""
        try:
            from memory.chroma_manager import chroma_manager
            
            if chroma_manager.enabled:
                # Create calendar events collection
                try:
                    self.calendar_events = chroma_manager.client.get_collection("calendar_events")
                except ValueError:
                    self.calendar_events = chroma_manager.client.create_collection("calendar_events")
                
                # Create calendar intelligence collection for patterns and insights
                try:
                    self.calendar_intelligence = chroma_manager.client.get_collection("calendar_intelligence")
                except ValueError:
                    self.calendar_intelligence = chroma_manager.client.create_collection("calendar_intelligence")
                
                logger.info("ChromaDB calendar collections initialized")
            else:
                self.calendar_events = None
                self.calendar_intelligence = None
                logger.warning("ChromaDB not available - calendar intelligence disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize calendar ChromaDB collections: {e}")
            self.calendar_events = None
            self.calendar_intelligence = None
    
    async def _authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API using OAuth2.
        
        Returns:
            True if authentication successful, False otherwise
        """
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.error(f"Failed to load token: {e}")
                creds = None
        
        # If no valid credentials, get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    logger.error(f"Google credentials file not found at {self.credentials_path}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"OAuth2 flow failed: {e}")
                    return False
            
            # Save credentials for next run
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logger.error(f"Failed to save token: {e}")
        
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar authentication successful")
            return True
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            return False
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute Google Calendar action.
        
        Args:
            action: Action to perform
            parameters: Action parameters
            
        Returns:
            Calendar operation result
        """
        # Authenticate first
        if not await self._authenticate():
            return {"error": "Google Calendar authentication failed"}
        
        try:
            if action == "list_events":
                return await self._list_events(parameters)
            elif action == "create_event":
                return await self._create_event(parameters)
            elif action == "update_event":
                return await self._update_event(parameters)
            elif action == "delete_event":
                return await self._delete_event(parameters)
            elif action == "get_conflicts":
                return await self._get_conflicts(parameters)
            elif action == "find_free_time":
                return await self._find_free_time(parameters)
            elif action == "prepare_meeting":
                return await self._prepare_meeting(parameters)
            elif action == "get_calendar_insights":
                return await self._get_calendar_insights(parameters)
            else:
                return {"error": f"Unknown calendar action: {action}"}
                
        except Exception as e:
            logger.error(f"Calendar action {action} failed: {e}")
            return {"error": f"Calendar operation failed: {str(e)}"}
    
    async def _list_events(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List calendar events with optional filtering."""
        calendar_id = parameters.get('calendar_id', 'primary')
        max_results = parameters.get('max_results', 20)
        time_min = parameters.get('time_min')
        time_max = parameters.get('time_max')
        
        # Default to next 7 days if no time range specified
        if not time_min:
            time_min = datetime.now(timezone.utc).isoformat()
        if not time_max:
            future_date = datetime.now(timezone.utc) + timedelta(days=7)
            time_max = future_date.isoformat()
        
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events and store in ChromaDB for intelligence
            processed_events = []
            for event in events:
                processed_event = self._process_event_data(event)
                processed_events.append(processed_event)
                
                # Store in ChromaDB for future intelligence
                await self._store_event_in_chroma(processed_event)
            
            return {
                "events": processed_events,
                "total_count": len(processed_events),
                "time_range": {"start": time_min, "end": time_max}
            }
            
        except HttpError as e:
            return {"error": f"Google Calendar API error: {e}"}
    
    async def _create_event(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar event."""
        calendar_id = parameters.get('calendar_id', 'primary')
        
        # Required parameters
        summary = parameters.get('summary')
        start_time = parameters.get('start_time')
        end_time = parameters.get('end_time')
        
        if not all([summary, start_time, end_time]):
            return {"error": "Missing required parameters: summary, start_time, end_time"}
        
        # Optional parameters
        description = parameters.get('description', '')
        location = parameters.get('location', '')
        attendees = parameters.get('attendees', [])
        
        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
        
        try:
            # Check for conflicts first
            conflicts = await self._check_time_conflicts(start_time, end_time, calendar_id)
            if conflicts.get('has_conflicts'):
                return {
                    "error": "Time conflict detected",
                    "conflicts": conflicts['conflicts'],
                    "suggested_times": await self._suggest_alternative_times(start_time, end_time)
                }
            
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            processed_event = self._process_event_data(event)
            
            # Store in ChromaDB
            await self._store_event_in_chroma(processed_event)
            
            # Generate meeting preparation if it's a meeting with attendees
            if attendees:
                prep_info = await self._generate_meeting_prep(processed_event)
                processed_event['meeting_preparation'] = prep_info
            
            return {
                "success": True,
                "event": processed_event,
                "event_url": event.get('htmlLink')
            }
            
        except HttpError as e:
            return {"error": f"Failed to create event: {e}"}
    
    async def _update_event(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing calendar event."""
        calendar_id = parameters.get('calendar_id', 'primary')
        event_id = parameters.get('event_id')
        
        if not event_id:
            return {"error": "Missing required parameter: event_id"}
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields that are provided
            for field in ['summary', 'description', 'location']:
                if field in parameters:
                    event[field] = parameters[field]
            
            if 'start_time' in parameters:
                event['start'] = {
                    'dateTime': parameters['start_time'],
                    'timeZone': 'UTC'
                }
            
            if 'end_time' in parameters:
                event['end'] = {
                    'dateTime': parameters['end_time'],
                    'timeZone': 'UTC'
                }
            
            if 'attendees' in parameters:
                event['attendees'] = [{'email': email} for email in parameters['attendees']]
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            processed_event = self._process_event_data(updated_event)
            
            # Update in ChromaDB
            await self._store_event_in_chroma(processed_event)
            
            return {
                "success": True,
                "event": processed_event
            }
            
        except HttpError as e:
            return {"error": f"Failed to update event: {e}"}
    
    async def _delete_event(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a calendar event."""
        calendar_id = parameters.get('calendar_id', 'primary')
        event_id = parameters.get('event_id')
        
        if not event_id:
            return {"error": "Missing required parameter: event_id"}
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return {
                "success": True,
                "message": f"Event {event_id} deleted successfully"
            }
            
        except HttpError as e:
            return {"error": f"Failed to delete event: {e}"}
    
    async def _get_conflicts(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Check for scheduling conflicts in a time range."""
        start_time = parameters.get('start_time')
        end_time = parameters.get('end_time')
        calendar_id = parameters.get('calendar_id', 'primary')
        
        if not all([start_time, end_time]):
            return {"error": "Missing required parameters: start_time, end_time"}
        
        return await self._check_time_conflicts(start_time, end_time, calendar_id)
    
    async def _find_free_time(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Find free time slots for scheduling."""
        duration_minutes = parameters.get('duration_minutes', 60)
        start_search = parameters.get('start_search')
        end_search = parameters.get('end_search')
        calendar_id = parameters.get('calendar_id', 'primary')
        
        # Default search range: next 7 days, business hours only
        if not start_search:
            start_search = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0).isoformat()
        if not end_search:
            end_date = datetime.now(timezone.utc) + timedelta(days=7)
            end_search = end_date.replace(hour=17, minute=0, second=0).isoformat()
        
        try:
            # Get existing events in the time range
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_search,
                timeMax=end_search,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Find free slots
            free_slots = self._calculate_free_slots(
                events, start_search, end_search, duration_minutes
            )
            
            return {
                "free_slots": free_slots,
                "duration_minutes": duration_minutes,
                "search_range": {"start": start_search, "end": end_search}
            }
            
        except HttpError as e:
            return {"error": f"Failed to find free time: {e}"}
    
    async def _prepare_meeting(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate meeting preparation information."""
        event_id = parameters.get('event_id')
        calendar_id = parameters.get('calendar_id', 'primary')
        
        if not event_id:
            return {"error": "Missing required parameter: event_id"}
        
        try:
            # Get event details
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            processed_event = self._process_event_data(event)
            prep_info = await self._generate_meeting_prep(processed_event)
            
            return {
                "event": processed_event,
                "preparation": prep_info
            }
            
        except HttpError as e:
            return {"error": f"Failed to prepare meeting: {e}"}
    
    async def _get_calendar_insights(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get calendar insights and patterns."""
        days_back = parameters.get('days_back', 30)
        
        if not self.calendar_intelligence:
            return {"error": "Calendar intelligence not available - ChromaDB disabled"}
        
        try:
            # Search for calendar patterns and insights
            insights_query = f"calendar patterns meetings schedule last {days_back} days"
            
            results = self.calendar_intelligence.query(
                query_texts=[insights_query],
                n_results=10
            )
            
            # Generate insights summary
            insights = {
                "meeting_frequency": "Analysis not available",
                "busiest_days": [],
                "common_meeting_types": [],
                "time_patterns": {},
                "recommendations": []
            }
            
            if results['documents'][0]:
                # Process stored insights
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    # Add insight processing logic here
            
            return {"insights": insights}
            
        except Exception as e:
            return {"error": f"Failed to generate insights: {e}"}
    
    def _process_event_data(self, event: Dict) -> Dict[str, Any]:
        """Process and normalize event data."""
        start = event.get('start', {})
        end = event.get('end', {})
        
        return {
            "id": event.get('id'),
            "summary": event.get('summary', 'No title'),
            "description": event.get('description', ''),
            "location": event.get('location', ''),
            "start_time": start.get('dateTime') or start.get('date'),
            "end_time": end.get('dateTime') or end.get('date'),
            "attendees": [
                attendee.get('email') for attendee in event.get('attendees', [])
                if attendee.get('email')
            ],
            "creator": event.get('creator', {}).get('email'),
            "status": event.get('status'),
            "html_link": event.get('htmlLink'),
            "created": event.get('created'),
            "updated": event.get('updated')
        }
    
    async def _store_event_in_chroma(self, event: Dict[str, Any]):
        """Store event data in ChromaDB for intelligence."""
        if not self.calendar_events:
            return
        
        try:
            event_text = f"{event['summary']} - {event['description']} at {event['location']}"
            
            metadata = {
                "event_id": event['id'],
                "type": "calendar_event",
                "start_time": event['start_time'],
                "end_time": event['end_time'],
                "attendee_count": len(event.get('attendees', [])),
                "has_location": bool(event.get('location')),
                "timestamp": datetime.now().isoformat()
            }
            
            self.calendar_events.add(
                documents=[event_text],
                metadatas=[metadata],
                ids=[f"event_{event['id']}"]
            )
            
        except Exception as e:
            logger.error(f"Failed to store event in ChromaDB: {e}")
    
    async def _check_time_conflicts(self, start_time: str, end_time: str, calendar_id: str) -> Dict[str, Any]:
        """Check for scheduling conflicts in given time range."""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True
            ).execute()
            
            conflicts = []
            for event in events_result.get('items', []):
                event_start = event.get('start', {}).get('dateTime')
                event_end = event.get('end', {}).get('dateTime')
                
                if event_start and event_end:
                    conflicts.append({
                        "summary": event.get('summary'),
                        "start": event_start,
                        "end": event_end
                    })
            
            return {
                "has_conflicts": len(conflicts) > 0,
                "conflicts": conflicts,
                "conflict_count": len(conflicts)
            }
            
        except HttpError as e:
            return {"error": f"Failed to check conflicts: {e}"}
    
    async def _suggest_alternative_times(self, original_start: str, original_end: str) -> List[Dict]:
        """Suggest alternative meeting times."""
        # Simple implementation: suggest 1 hour before and after
        try:
            original_dt = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
            duration = datetime.fromisoformat(original_end.replace('Z', '+00:00')) - original_dt
            
            suggestions = []
            
            # Suggest 1 hour earlier
            earlier_start = original_dt - timedelta(hours=1)
            earlier_end = earlier_start + duration
            suggestions.append({
                "start": earlier_start.isoformat(),
                "end": earlier_end.isoformat(),
                "suggestion": "1 hour earlier"
            })
            
            # Suggest 1 hour later
            later_start = original_dt + timedelta(hours=1)
            later_end = later_start + duration
            suggestions.append({
                "start": later_start.isoformat(),
                "end": later_end.isoformat(),
                "suggestion": "1 hour later"
            })
            
            return suggestions
            
        except Exception:
            return []
    
    def _calculate_free_slots(self, events: List[Dict], start_search: str, end_search: str, duration_minutes: int) -> List[Dict]:
        """Calculate free time slots between events."""
        busy_times = []
        
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            
            start_time = start.get('dateTime')
            end_time = end.get('dateTime')
            
            if start_time and end_time:
                busy_times.append({
                    'start': datetime.fromisoformat(start_time.replace('Z', '+00:00')),
                    'end': datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                })
        
        # Sort busy times
        busy_times.sort(key=lambda x: x['start'])
        
        # Find free slots
        free_slots = []
        search_start = datetime.fromisoformat(start_search.replace('Z', '+00:00'))
        search_end = datetime.fromisoformat(end_search.replace('Z', '+00:00'))
        
        current_time = search_start
        duration_delta = timedelta(minutes=duration_minutes)
        
        for busy in busy_times:
            if current_time + duration_delta <= busy['start']:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': (current_time + duration_delta).isoformat(),
                    'duration_minutes': duration_minutes
                })
            current_time = max(current_time, busy['end'])
        
        # Check for slot after last event
        if current_time + duration_delta <= search_end:
            free_slots.append({
                'start': current_time.isoformat(),
                'end': (current_time + duration_delta).isoformat(),
                'duration_minutes': duration_minutes
            })
        
        return free_slots[:10]  # Limit to 10 suggestions
    
    async def _generate_meeting_prep(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Generate meeting preparation information."""
        prep_info = {
            "agenda_items": [],
            "attendee_info": [],
            "relevant_context": [],
            "action_items": [],
            "documents_needed": []
        }
        
        try:
            # Search for related conversations and emails if available
            if self.calendar_intelligence:
                search_query = f"{event['summary']} meeting preparation context"
                
                results = self.calendar_intelligence.query(
                    query_texts=[search_query],
                    n_results=5
                )
                
                if results['documents'][0]:
                    for doc in results['documents'][0]:
                        prep_info['relevant_context'].append(doc)
            
            # Basic preparation suggestions
            prep_info['agenda_items'] = [
                "Review meeting objectives",
                "Prepare status updates",
                "Review previous action items"
            ]
            
            if event.get('attendees'):
                prep_info['attendee_info'] = [
                    f"Attendee: {attendee}" for attendee in event['attendees'][:5]
                ]
            
            return prep_info
            
        except Exception as e:
            logger.error(f"Failed to generate meeting prep: {e}")
            return prep_info
    
    def health_check(self) -> bool:
        """Check if Google Calendar tool is healthy."""
        return self.credentials_path.exists()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Google Calendar tool capabilities."""
        return {
            "name": self.name,
            "enabled": self.enabled and self.health_check(),
            "actions": [
                {
                    "name": "list_events",
                    "description": "List calendar events with optional filtering",
                    "parameters": ["calendar_id", "max_results", "time_min", "time_max"]
                },
                {
                    "name": "create_event",
                    "description": "Create a new calendar event",
                    "parameters": ["summary", "start_time", "end_time", "description", "location", "attendees"]
                },
                {
                    "name": "update_event", 
                    "description": "Update an existing calendar event",
                    "parameters": ["event_id", "summary", "start_time", "end_time", "description", "location", "attendees"]
                },
                {
                    "name": "delete_event",
                    "description": "Delete a calendar event",
                    "parameters": ["event_id", "calendar_id"]
                },
                {
                    "name": "get_conflicts",
                    "description": "Check for scheduling conflicts in a time range",
                    "parameters": ["start_time", "end_time", "calendar_id"]
                },
                {
                    "name": "find_free_time",
                    "description": "Find free time slots for scheduling",
                    "parameters": ["duration_minutes", "start_search", "end_search", "calendar_id"]
                },
                {
                    "name": "prepare_meeting",
                    "description": "Generate meeting preparation information",
                    "parameters": ["event_id", "calendar_id"]
                },
                {
                    "name": "get_calendar_insights",
                    "description": "Get calendar insights and patterns",
                    "parameters": ["days_back"]
                }
            ]
        }