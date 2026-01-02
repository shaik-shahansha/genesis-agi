"""Email integration - Send and receive emails via SMTP/IMAP.

Example:
    config = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'email': 'mind@example.com',
        'password': 'app-password',
        'enabled': True
    }

    email_int = EmailIntegration(config)
    await email_int.send(
        message="Hello!",
        to="user@example.com",
        subject="Greetings"
    )
"""

import aiosmtplib
import aioimaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import logging

from genesis.integrations.base import Integration, IntegrationType

logger = logging.getLogger(__name__)


class EmailIntegration(Integration):
    """Email integration using SMTP/IMAP."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config['smtp_host']
        self.smtp_port = config['smtp_port']
        self.imap_host = config['imap_host']
        self.imap_port = config['imap_port']
        self.email = config['email']
        self.password = config['password']
        self.check_interval = config.get('check_interval', 300)
        self.mark_as_read = config.get('mark_as_read', True)
        self.emails_sent = 0
        self.emails_received = 0

    async def send(
        self,
        message: str,
        to: str,
        subject: str = "Message from Genesis Mind",
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject
            if cc:
                msg['Cc'] = ', '.join(cc)

            part = MIMEText(message, 'html' if html else 'plain')
            msg.attach(part)

            # Use async SMTP client
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            async with aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port) as server:
                await server.starttls()
                await server.login(self.email, self.password)
                await server.send_message(msg, sender=self.email, recipients=recipients)

            self.emails_sent += 1
            logger.info(f"[Done] Email sent to {to}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False

    async def receive(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            # Use async IMAP client
            mail = aioimaplib.IMAP4_SSL(host=self.imap_host, port=self.imap_port)
            await mail.wait_hello_from_server()
            await mail.login(self.email, self.password)
            await mail.select('INBOX')

            status, messages = await mail.search('UNSEEN')
            if status != 'OK':
                await mail.logout()
                return []

            email_ids = messages[0].split()
            emails = []

            for email_id in email_ids[-limit:]:
                status, msg_data = await mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue

                # Parse the response - aioimaplib returns different format
                raw_email = msg_data[1]
                msg = email.message_from_bytes(raw_email)

                emails.append({
                    'id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                    'from': msg.get('From'),
                    'to': msg.get('To'),
                    'subject': msg.get('Subject'),
                    'date': msg.get('Date'),
                    'body': self._get_email_body(msg)
                })

                if self.mark_as_read:
                    await mail.store(email_id, '+FLAGS', '(\\Seen)')
                self.emails_received += 1

            await mail.close()
            await mail.logout()
            logger.info(f"📧 Received {len(emails)} new emails")
            return emails
        except Exception as e:
            logger.error(f"❌ Failed to receive emails: {e}")
            return []

    def _get_email_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
        return body

    def get_status(self) -> Dict[str, Any]:
        return {
            'type': IntegrationType.EMAIL,
            'enabled': self.enabled,
            'email': self.email,
            'smtp_host': self.smtp_host,
            'imap_host': self.imap_host,
            'emails_sent': self.emails_sent,
            'emails_received': self.emails_received
        }
