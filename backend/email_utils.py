"""
email_utils.py - Gmail API integration for sending and receiving emails.
SSL certificates configured in main.py.
"""
import os
import base64
import logging
import asyncio
from typing import List, Optional

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth
    GOOGLE_API_CLIENT_AVAILABLE = True
except ImportError:
    GOOGLE_API_CLIENT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GMAIL_IMPERSONATE_USER = os.environ.get("GMAIL_IMPERSONATE_USER", "user@example.com")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", GMAIL_IMPERSONATE_USER)
EMAIL_RECIPIENTS = os.environ.get("EMAIL_RECIPIENTS", "").split(",")


def is_email_configured() -> bool:
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.warning("Email configuration incomplete: Google API libraries not installed")
        return False
    return True


def get_gmail_service(scopes: List[str]):
    """
    Initialize Gmail API service using Application Default Credentials.
    SSL certificates configured in main.py via certifi.
    """
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path:
        creds_path = os.path.expanduser(creds_path)
        if not os.path.exists(creds_path):
            logger.debug(f"Removing non-existent GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
            os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
    
    # Use Application Default Credentials
    creds, _ = google.auth.default(scopes=scopes)
    
    # If using service account, delegate to impersonate user
    if hasattr(creds, 'with_subject'):
        delegated_creds = creds.with_subject(GMAIL_IMPERSONATE_USER)
        return build('gmail', 'v1', credentials=delegated_creds, cache_discovery=False)
    else:
        return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def get_gmail_send_service():
    """Gmail service with full scope for sending emails."""
    return get_gmail_service(['https://www.googleapis.com/auth/gmail.modify'])


def get_gmail_read_service():
    """Gmail service with full scope for reading emails."""
    return get_gmail_service(['https://www.googleapis.com/auth/gmail.modify'])


async def send_email_with_attachments(
    subject: str,
    body: str,
    to_email: str,
    attachments: Optional[List[str]] = None
) -> bool:
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.error("Google API client libraries not installed.")
        return False

    if not is_email_configured():
        return False

    try:
        service = get_gmail_send_service()
    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {e}")
        return False

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    message = MIMEMultipart()
    message['To'] = to_email
    message['From'] = EMAIL_SENDER
    message['Subject'] = subject

    message.attach(MIMEText(body, 'html'))

    try:
        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(file_path)}",
                    )
                    message.attach(part)
                    logger.info(f"Attached file: {os.path.basename(file_path)}")
                except FileNotFoundError:
                    logger.error(f"Attachment file not found: {file_path}. Skipping.")
                except Exception as e:
                    logger.error(f"Error attaching file {file_path}: {e}")

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        logger.info(f"Sending email via Gmail API to {to_email}...")
        sent_message = await asyncio.to_thread(lambda: service.users().messages().send(userId="me", body=create_message).execute())
        logger.info(f"Email sent successfully! Message ID: {sent_message['id']}")
        return True

    except HttpError as error:
        logger.error(f"An error occurred sending email via Gmail API: {error}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error while sending email: {e}")
        return False


async def fetch_unread_replies(domains: List[str]) -> List[dict]:
    """
    Fetches unread emails from a list of supplier domains.
    Returns a list of dicts with 'id', 'from', 'subject', 'body', 'date'.
    """
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.error("Google API client libraries not installed.")
        return []

    try:
        service = get_gmail_read_service()
    except Exception as e:
        logger.error(f"Failed to initialize Gmail read service: {e}")
        return []

    query = "is:unread (" + " OR ".join([f"from:{domain}" for domain in domains]) + ")"
    logger.info(f"Querying Gmail: {query}")
    
    try:
        results = await asyncio.to_thread(lambda: service.users().messages().list(userId='me', q=query, maxResults=50).execute())
        messages = results.get('messages', [])
        
        extracted_emails = []
        
        for message in messages:
            try:
                msg = await asyncio.to_thread(lambda mid=message['id']: service.users().messages().get(userId='me', id=mid, format='full').execute())
                headers = msg['payload']['headers']
                
                email_data = {
                    'id': msg['id'],
                    'from': next((h['value'] for h in headers if h['name'] == 'From'), ''),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                    'body': _get_message_body(msg)
                }
                extracted_emails.append(email_data)
                logger.info(f"Extracted email from {email_data['from']}: {email_data['subject']}")
                
            except Exception as e:
                logger.error(f"Error extracting email {message['id']}: {e}")
                continue
        
        return extracted_emails
        
    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error fetching unread replies: {e}")
        return []


def _get_message_body(message: dict) -> str:
    """Extracts the plain text or HTML body from a Gmail message."""
    try:
        if 'parts' in message['payload']:
            # Multipart message
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in message['payload']:
            # Simple message
            if 'data' in message['payload']['body']:
                return base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        return ""
    except Exception as e:
        logger.error(f"Error extracting message body: {e}")
        return ""


async def send_reminder_email(supplier_email: str, supplier_name: str, chemical_query: str) -> bool:
    """Sends a reminder email to a supplier who hasn't responded."""
    subject = f"Reminder: Request for Quote - {chemical_query}"
    
    body = f"""
    <p>Dear {supplier_name},</p>
    
    <p>I hope this email finds you well.</p>
    
    <p>I wanted to follow up on my previous request for a quote regarding:</p>
    <p><strong>{chemical_query}</strong></p>
    
    <p>I would greatly appreciate if you could provide us with a quote at your earliest convenience. 
    If you have any questions or need clarification, please don't hesitate to reach out.</p>
    
    <p>Thank you for your attention to this matter.</p>
    
    <p>Best regards,<br>
    Amit<br>
    Procurement Team</p>
    """
    
    return await send_email_with_attachments(subject, body, supplier_email)


async def mark_message_as_read(message_id: str) -> bool:
    """Marks a Gmail message as read."""
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.error("Google API client libraries not installed.")
        return False
    
    try:
        service = get_gmail_read_service()
        await asyncio.to_thread(lambda: service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute())
        logger.info(f"Marked message {message_id} as read")
        return True
    except Exception as e:
        logger.error(f"Error marking message as read: {e}")
        return False
