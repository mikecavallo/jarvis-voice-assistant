"""
Gmail tool for MCP server.

Provides comprehensive Gmail integration with OAuth2 authentication.
Supports email management, content analysis, action item extraction, and smart reply generation.
"""

import os
import json
import pickle
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re
import uuid
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

# OAuth2 scopes for Gmail
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

class GmailTool(BaseTool):
    """Gmail integration tool with OAuth2 authentication and AI features."""
    
    def __init__(self):
        super().__init__("gmail")
        self.credentials_path = Path("credentials/gmail_credentials.json")
        self.token_path = Path("credentials/gmail_token.pickle")
        self.service = None
        
        # Ensure credentials directory exists
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB collections for email intelligence
        self._init_chroma_collections()
        
    def _init_chroma_collections(self):
        """Initialize ChromaDB collections for email intelligence."""
        try:
            from memory.chroma_manager import chroma_manager
            
            if chroma_manager.enabled:
                # Create email intelligence collection
                try:
                    self.gmail_intelligence = chroma_manager.client.get_collection("gmail_intelligence")
                except ValueError:
                    self.gmail_intelligence = chroma_manager.client.create_collection("gmail_intelligence")
                
                # Create email threads collection
                try:
                    self.email_threads = chroma_manager.client.get_collection("email_threads")
                except ValueError:
                    self.email_threads = chroma_manager.client.create_collection("email_threads")
                
                logger.info("ChromaDB email collections initialized")
            else:
                self.gmail_intelligence = None
                self.email_threads = None
                logger.warning("ChromaDB not available - email intelligence disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize email ChromaDB collections: {e}")
            self.gmail_intelligence = None
            self.email_threads = None
    
    async def _authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.
        
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
                logger.error(f"Failed to load Gmail token: {e}")
                creds = None
        
        # If no valid credentials, get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh Gmail token: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    logger.error(f"Gmail credentials file not found at {self.credentials_path}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Gmail OAuth2 flow failed: {e}")
                    return False
            
            # Save credentials for next run
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logger.error(f"Failed to save Gmail token: {e}")
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail authentication successful")
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute Gmail action.
        
        Args:
            action: Action to perform
            parameters: Action parameters
            
        Returns:
            Email operation result
        """
        # Authenticate first
        if not await self._authenticate():
            return {"error": "Gmail authentication failed"}
        
        try:
            if action == "list_emails":
                return await self._list_emails(parameters)
            elif action == "read_email":
                return await self._read_email(parameters)
            elif action == "send_email":
                return await self._send_email(parameters)
            elif action == "draft_email":
                return await self._draft_email(parameters)
            elif action == "search_emails":
                return await self._search_emails(parameters)
            elif action == "get_thread":
                return await self._get_thread(parameters)
            elif action == "analyze_email":
                return await self._analyze_email(parameters)
            elif action == "extract_action_items":
                return await self._extract_action_items(parameters)
            elif action == "generate_reply":
                return await self._generate_reply(parameters)
            elif action == "categorize_emails":
                return await self._categorize_emails(parameters)
            elif action == "get_email_insights":
                return await self._get_email_insights(parameters)
            else:
                return {"error": f"Unknown Gmail action: {action}"}
                
        except Exception as e:
            logger.error(f"Gmail action {action} failed: {e}")
            return {"error": f"Gmail operation failed: {str(e)}"}
    
    async def _list_emails(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List emails with optional filtering."""
        query = parameters.get('query', '')
        max_results = parameters.get('max_results', 20)
        label_ids = parameters.get('label_ids', [])
        
        try:
            # Build the search parameters
            search_params = {
                'userId': 'me',
                'maxResults': max_results
            }
            
            if query:
                search_params['q'] = query
            if label_ids:
                search_params['labelIds'] = label_ids
            
            # Get message list
            messages_result = self.service.users().messages().list(**search_params).execute()
            messages = messages_result.get('messages', [])
            
            # Get detailed information for each message
            email_list = []
            for message in messages[:max_results]:
                email_data = await self._get_email_details(message['id'])
                if email_data:
                    email_list.append(email_data)
                    
                    # Store in ChromaDB for intelligence
                    await self._store_email_in_chroma(email_data)
            
            return {
                "emails": email_list,
                "total_count": len(email_list),
                "query": query,
                "has_more": len(messages) > max_results
            }
            
        except HttpError as e:
            return {"error": f"Gmail API error: {e}"}
    
    async def _read_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific email by ID."""
        message_id = parameters.get('message_id')
        
        if not message_id:
            return {"error": "Missing required parameter: message_id"}
        
        try:
            email_data = await self._get_email_details(message_id)
            if not email_data:
                return {"error": "Email not found"}
            
            # Mark as read if requested
            if parameters.get('mark_read', False):
                self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            
            # Store in ChromaDB
            await self._store_email_in_chroma(email_data)
            
            # Analyze content for insights
            analysis = await self._analyze_email_content(email_data)
            email_data['analysis'] = analysis
            
            return {"email": email_data}
            
        except HttpError as e:
            return {"error": f"Failed to read email: {e}"}
    
    async def _send_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email."""
        to = parameters.get('to')
        subject = parameters.get('subject')
        body = parameters.get('body')
        
        if not all([to, subject, body]):
            return {"error": "Missing required parameters: to, subject, body"}
        
        cc = parameters.get('cc', [])
        bcc = parameters.get('bcc', [])
        attachments = parameters.get('attachments', [])
        
        try:
            # Create message
            message = MIMEMultipart()
            message['to'] = ', '.join(to) if isinstance(to, list) else to
            message['subject'] = subject
            
            if cc:
                message['cc'] = ', '.join(cc) if isinstance(cc, list) else cc
            if bcc:
                message['bcc'] = ', '.join(bcc) if isinstance(bcc, list) else bcc
            
            # Add body
            message.attach(MIMEText(body, 'html' if '<' in body else 'plain'))
            
            # Add attachments if any
            for attachment in attachments:
                if 'path' in attachment:
                    self._add_attachment(message, attachment['path'], attachment.get('name'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send email
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            # Store sent email info in ChromaDB
            sent_email_data = {
                'id': sent_message['id'],
                'to': to,
                'subject': subject,
                'body': body,
                'timestamp': datetime.now().isoformat(),
                'type': 'sent'
            }
            await self._store_email_in_chroma(sent_email_data)
            
            return {
                "success": True,
                "message_id": sent_message['id'],
                "sent_to": to,
                "subject": subject
            }
            
        except HttpError as e:
            return {"error": f"Failed to send email: {e}"}
    
    async def _draft_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create an email draft."""
        to = parameters.get('to')
        subject = parameters.get('subject')
        body = parameters.get('body')
        
        if not all([to, subject, body]):
            return {"error": "Missing required parameters: to, subject, body"}
        
        try:
            # Create draft message
            message = MIMEText(body, 'html' if '<' in body else 'plain')
            message['to'] = ', '.join(to) if isinstance(to, list) else to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {
                "success": True,
                "draft_id": draft['id'],
                "message_id": draft['message']['id']
            }
            
        except HttpError as e:
            return {"error": f"Failed to create draft: {e}"}
    
    async def _search_emails(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search emails using Gmail search syntax."""
        query = parameters.get('query', '')
        max_results = parameters.get('max_results', 20)
        
        if not query:
            return {"error": "Missing required parameter: query"}
        
        # Use the list_emails function with search query
        return await self._list_emails({
            'query': query,
            'max_results': max_results
        })
    
    async def _get_thread(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get email thread by thread ID."""
        thread_id = parameters.get('thread_id')
        
        if not thread_id:
            return {"error": "Missing required parameter: thread_id"}
        
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            # Process thread messages
            processed_messages = []
            for message in thread.get('messages', []):
                email_data = await self._get_email_details(message['id'])
                if email_data:
                    processed_messages.append(email_data)
            
            thread_data = {
                'thread_id': thread_id,
                'message_count': len(processed_messages),
                'messages': processed_messages,
                'snippet': thread.get('snippet', ''),
                'history_id': thread.get('historyId')
            }
            
            # Store thread in ChromaDB
            await self._store_thread_in_chroma(thread_data)
            
            return {"thread": thread_data}
            
        except HttpError as e:
            return {"error": f"Failed to get thread: {e}"}
    
    async def _analyze_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze email content for insights."""
        message_id = parameters.get('message_id')
        
        if not message_id:
            return {"error": "Missing required parameter: message_id"}
        
        try:
            email_data = await self._get_email_details(message_id)
            if not email_data:
                return {"error": "Email not found"}
            
            analysis = await self._analyze_email_content(email_data)
            
            return {
                "email_id": message_id,
                "analysis": analysis
            }
            
        except Exception as e:
            return {"error": f"Failed to analyze email: {e}"}
    
    async def _extract_action_items(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract action items from emails."""
        message_id = parameters.get('message_id')
        thread_id = parameters.get('thread_id')
        
        if not message_id and not thread_id:
            return {"error": "Missing required parameter: message_id or thread_id"}
        
        try:
            emails_to_process = []
            
            if message_id:
                email_data = await self._get_email_details(message_id)
                if email_data:
                    emails_to_process.append(email_data)
            
            if thread_id:
                thread_result = await self._get_thread({'thread_id': thread_id})
                if thread_result.get('thread'):
                    emails_to_process.extend(thread_result['thread']['messages'])
            
            # Extract action items from all emails
            all_action_items = []
            for email in emails_to_process:
                action_items = self._extract_action_items_from_text(email.get('body', ''))
                all_action_items.extend(action_items)
            
            return {
                "action_items": all_action_items,
                "email_count": len(emails_to_process)
            }
            
        except Exception as e:
            return {"error": f"Failed to extract action items: {e}"}
    
    async def _generate_reply(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smart reply suggestions for an email."""
        message_id = parameters.get('message_id')
        tone = parameters.get('tone', 'professional')
        
        if not message_id:
            return {"error": "Missing required parameter: message_id"}
        
        try:
            email_data = await self._get_email_details(message_id)
            if not email_data:
                return {"error": "Email not found"}
            
            # Generate reply suggestions
            reply_suggestions = await self._generate_reply_suggestions(email_data, tone)
            
            return {
                "original_email": {
                    "id": message_id,
                    "subject": email_data.get('subject'),
                    "from": email_data.get('from')
                },
                "reply_suggestions": reply_suggestions
            }
            
        except Exception as e:
            return {"error": f"Failed to generate reply: {e}"}
    
    async def _categorize_emails(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize emails automatically."""
        max_emails = parameters.get('max_emails', 50)
        
        try:
            # Get recent emails
            emails_result = await self._list_emails({'max_results': max_emails})
            emails = emails_result.get('emails', [])
            
            categories = {
                'urgent': [],
                'meetings': [],
                'projects': [],
                'personal': [],
                'newsletters': [],
                'spam_likely': [],
                'other': []
            }
            
            # Categorize each email
            for email in emails:
                category = self._categorize_email_content(email)
                categories[category].append({
                    'id': email['id'],
                    'subject': email['subject'],
                    'from': email['from'],
                    'timestamp': email['timestamp']
                })
            
            # Store categorization results in ChromaDB
            await self._store_categorization_in_chroma(categories)
            
            return {
                "categories": categories,
                "total_emails": len(emails),
                "categorization_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Failed to categorize emails: {e}"}
    
    async def _get_email_insights(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get email insights and statistics."""
        days_back = parameters.get('days_back', 7)
        
        if not self.gmail_intelligence:
            return {"error": "Email intelligence not available - ChromaDB disabled"}
        
        try:
            # Search for email patterns and insights
            insights_query = f"email patterns analysis last {days_back} days"
            
            results = self.gmail_intelligence.query(
                query_texts=[insights_query],
                n_results=20
            )
            
            # Generate insights summary
            insights = {
                "email_volume": {"sent": 0, "received": 0},
                "top_senders": [],
                "common_subjects": [],
                "response_time_avg": "Not calculated",
                "busy_times": [],
                "action_items_pending": 0,
                "recommendations": []
            }
            
            # Basic recommendations
            insights["recommendations"] = [
                "Set up email filters for newsletters",
                "Schedule dedicated time for email processing",
                "Use templates for common responses"
            ]
            
            return {"insights": insights, "period_days": days_back}
            
        except Exception as e:
            return {"error": f"Failed to generate insights: {e}"}
    
    async def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific email."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            for header in message['payload'].get('headers', []):
                headers[header['name'].lower()] = header['value']
            
            # Extract body
            body = self._extract_email_body(message['payload'])
            
            # Process email data
            email_data = {
                'id': message['id'],
                'thread_id': message['threadId'],
                'label_ids': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'history_id': message.get('historyId'),
                'internal_date': message.get('internalDate'),
                'timestamp': datetime.fromtimestamp(
                    int(message.get('internalDate', 0)) / 1000,
                    tz=timezone.utc
                ).isoformat() if message.get('internalDate') else None,
                'subject': headers.get('subject', 'No Subject'),
                'from': headers.get('from', 'Unknown'),
                'to': headers.get('to', 'Unknown'),
                'cc': headers.get('cc', ''),
                'bcc': headers.get('bcc', ''),
                'reply_to': headers.get('reply-to', ''),
                'body': body,
                'attachments': self._extract_attachments(message['payload']),
                'is_unread': 'UNREAD' in message.get('labelIds', []),
                'is_important': 'IMPORTANT' in message.get('labelIds', []),
                'is_starred': 'STARRED' in message.get('labelIds', [])
            }
            
            return email_data
            
        except Exception as e:
            logger.error(f"Failed to get email details for {message_id}: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        # Simple HTML to text conversion
                        body = re.sub(r'<[^>]+>', '', html_body)
        else:
            if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body.strip()
    
    def _extract_attachments(self, payload: Dict) -> List[Dict]:
        """Extract attachment information from email payload."""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if 'filename' in part and part['filename']:
                    attachments.append({
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    })
        
        return attachments
    
    def _add_attachment(self, message: MIMEMultipart, file_path: str, filename: Optional[str] = None):
        """Add attachment to email message."""
        try:
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename or os.path.basename(file_path)}'
            )
            
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
    
    async def _store_email_in_chroma(self, email_data: Dict[str, Any]):
        """Store email data in ChromaDB for intelligence."""
        if not self.gmail_intelligence:
            return
        
        try:
            email_text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
            
            metadata = {
                "email_id": email_data['id'],
                "thread_id": email_data.get('thread_id'),
                "type": "email",
                "from": email_data.get('from', ''),
                "subject": email_data.get('subject', ''),
                "timestamp": email_data.get('timestamp'),
                "is_unread": email_data.get('is_unread', False),
                "has_attachments": len(email_data.get('attachments', [])) > 0,
                "stored_at": datetime.now().isoformat()
            }
            
            doc_id = f"email_{email_data['id']}"
            
            self.gmail_intelligence.add(
                documents=[email_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
        except Exception as e:
            logger.error(f"Failed to store email in ChromaDB: {e}")
    
    async def _store_thread_in_chroma(self, thread_data: Dict[str, Any]):
        """Store email thread data in ChromaDB."""
        if not self.email_threads:
            return
        
        try:
            thread_text = " ".join([
                f"{msg.get('subject', '')} {msg.get('body', '')}"
                for msg in thread_data.get('messages', [])
            ])
            
            metadata = {
                "thread_id": thread_data['thread_id'],
                "type": "email_thread",
                "message_count": thread_data.get('message_count', 0),
                "snippet": thread_data.get('snippet', ''),
                "stored_at": datetime.now().isoformat()
            }
            
            doc_id = f"thread_{thread_data['thread_id']}"
            
            self.email_threads.add(
                documents=[thread_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
        except Exception as e:
            logger.error(f"Failed to store thread in ChromaDB: {e}")
    
    async def _analyze_email_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze email content for insights."""
        body = email_data.get('body', '')
        subject = email_data.get('subject', '')
        
        analysis = {
            'sentiment': 'neutral',
            'urgency': 'normal',
            'category': 'other',
            'key_topics': [],
            'action_items': [],
            'meeting_requests': [],
            'deadlines': []
        }
        
        # Simple keyword-based analysis
        urgent_keywords = ['urgent', 'asap', 'immediately', 'critical', 'emergency']
        meeting_keywords = ['meeting', 'call', 'zoom', 'teams', 'conference']
        
        text_lower = (subject + ' ' + body).lower()
        
        # Urgency detection
        if any(keyword in text_lower for keyword in urgent_keywords):
            analysis['urgency'] = 'high'
        
        # Meeting detection
        if any(keyword in text_lower for keyword in meeting_keywords):
            analysis['category'] = 'meeting'
            analysis['meeting_requests'] = self._extract_meeting_requests(body)
        
        # Extract action items
        analysis['action_items'] = self._extract_action_items_from_text(body)
        
        # Extract deadlines
        analysis['deadlines'] = self._extract_deadlines(body)
        
        return analysis
    
    def _extract_action_items_from_text(self, text: str) -> List[str]:
        """Extract action items from email text."""
        action_patterns = [
            r'please\s+(.{1,100})',
            r'can\s+you\s+(.{1,100})',
            r'need\s+to\s+(.{1,100})',
            r'action\s+item[:\s]+(.{1,100})',
            r'todo[:\s]+(.{1,100})',
            r'task[:\s]+(.{1,100})'
        ]
        
        action_items = []
        text_lower = text.lower()
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if match.strip() and len(match.strip()) > 5:
                    action_items.append(match.strip()[:100])  # Limit length
        
        return list(set(action_items))[:5]  # Remove duplicates and limit
    
    def _extract_meeting_requests(self, text: str) -> List[Dict[str, Any]]:
        """Extract meeting requests from email text."""
        meeting_patterns = [
            r'meeting\s+(.{1,100})',
            r'call\s+(.{1,100})',
            r'zoom\s+(.{1,100})',
            r'schedule\s+(.{1,100})'
        ]
        
        meetings = []
        for pattern in meeting_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.strip():
                    meetings.append({
                        'description': match.strip()[:100],
                        'extracted_from': 'email_content'
                    })
        
        return meetings[:3]  # Limit to 3
    
    def _extract_deadlines(self, text: str) -> List[str]:
        """Extract deadline information from email text."""
        deadline_patterns = [
            r'deadline[:\s]+(.{1,50})',
            r'due\s+(.{1,50})',
            r'by\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'before\s+(.{1,50})'
        ]
        
        deadlines = []
        for pattern in deadline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.strip():
                    deadlines.append(match.strip()[:50])
        
        return list(set(deadlines))[:3]  # Remove duplicates and limit
    
    def _categorize_email_content(self, email_data: Dict[str, Any]) -> str:
        """Categorize email based on content."""
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        from_addr = email_data.get('from', '').lower()
        
        text = subject + ' ' + body + ' ' + from_addr
        
        # Simple rule-based categorization
        if any(word in text for word in ['urgent', 'asap', 'critical', 'emergency']):
            return 'urgent'
        elif any(word in text for word in ['meeting', 'call', 'zoom', 'teams']):
            return 'meetings'
        elif any(word in text for word in ['project', 'task', 'milestone', 'deadline']):
            return 'projects'
        elif any(word in text for word in ['newsletter', 'unsubscribe', 'promotional']):
            return 'newsletters'
        elif 'noreply' in from_addr or 'automated' in text:
            return 'newsletters'
        elif any(word in text for word in ['personal', 'family', 'friend']):
            return 'personal'
        else:
            return 'other'
    
    async def _generate_reply_suggestions(self, email_data: Dict[str, Any], tone: str) -> List[Dict[str, Any]]:
        """Generate smart reply suggestions."""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        # Simple template-based reply suggestions
        suggestions = []
        
        if 'meeting' in body.lower():
            suggestions.append({
                'type': 'accept_meeting',
                'subject': f"Re: {subject}",
                'body': "Thank you for the meeting invitation. I'll be there."
            })
            suggestions.append({
                'type': 'decline_meeting',
                'subject': f"Re: {subject}",
                'body': "Thank you for the invitation. Unfortunately, I won't be able to attend."
            })
        
        if '?' in body:
            suggestions.append({
                'type': 'acknowledge',
                'subject': f"Re: {subject}",
                'body': "Thank you for your email. I'll review this and get back to you soon."
            })
        
        # Default acknowledgment
        suggestions.append({
            'type': 'acknowledge',
            'subject': f"Re: {subject}",
            'body': "Thank you for your email. I've received it and will respond accordingly."
        })
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    async def _store_categorization_in_chroma(self, categories: Dict[str, List]):
        """Store email categorization results in ChromaDB."""
        if not self.gmail_intelligence:
            return
        
        try:
            categorization_text = json.dumps(categories)
            
            metadata = {
                "type": "email_categorization",
                "timestamp": datetime.now().isoformat(),
                "total_emails": sum(len(emails) for emails in categories.values()),
                "categories": list(categories.keys())
            }
            
            doc_id = f"categorization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.gmail_intelligence.add(
                documents=[categorization_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
        except Exception as e:
            logger.error(f"Failed to store categorization in ChromaDB: {e}")
    
    def health_check(self) -> bool:
        """Check if Gmail tool is healthy."""
        return self.credentials_path.exists()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Gmail tool capabilities."""
        return {
            "name": self.name,
            "enabled": self.enabled and self.health_check(),
            "actions": [
                {
                    "name": "list_emails",
                    "description": "List emails with optional filtering",
                    "parameters": ["query", "max_results", "label_ids"]
                },
                {
                    "name": "read_email",
                    "description": "Read a specific email by ID",
                    "parameters": ["message_id", "mark_read"]
                },
                {
                    "name": "send_email",
                    "description": "Send an email",
                    "parameters": ["to", "subject", "body", "cc", "bcc", "attachments"]
                },
                {
                    "name": "draft_email",
                    "description": "Create an email draft",
                    "parameters": ["to", "subject", "body"]
                },
                {
                    "name": "search_emails",
                    "description": "Search emails using Gmail search syntax",
                    "parameters": ["query", "max_results"]
                },
                {
                    "name": "get_thread",
                    "description": "Get email thread by thread ID",
                    "parameters": ["thread_id"]
                },
                {
                    "name": "analyze_email",
                    "description": "Analyze email content for insights",
                    "parameters": ["message_id"]
                },
                {
                    "name": "extract_action_items",
                    "description": "Extract action items from emails",
                    "parameters": ["message_id", "thread_id"]
                },
                {
                    "name": "generate_reply",
                    "description": "Generate smart reply suggestions",
                    "parameters": ["message_id", "tone"]
                },
                {
                    "name": "categorize_emails",
                    "description": "Categorize emails automatically",
                    "parameters": ["max_emails"]
                },
                {
                    "name": "get_email_insights",
                    "description": "Get email insights and statistics",
                    "parameters": ["days_back"]
                }
            ]
        }