"""Email Newsletter Extractor — fetch newsletters via IMAP.

Connects to an IMAP mailbox, searches for unread emails from whitelisted
senders, extracts HTML/plain text content, and converts to Articles.

Environment variables:
    EMAIL_USERNAME: IMAP login username
    EMAIL_APP_PASSWORD: IMAP app-specific password
    EMAIL_IMAP_SERVER: IMAP server hostname (e.g. imap.gmail.com)
"""
from __future__ import annotations

import email
import email.policy
import hashlib
import logging
import os
import re
from datetime import datetime
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import List, Optional, Tuple

from pipeline.models import Article, ArticleSource

logger = logging.getLogger(__name__)


def _decode_header_value(value: str) -> str:
    """Decode RFC 2047 encoded header value."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _get_text_from_part(part) -> str:
    """Extract text content from a single MIME part."""
    content_type = part.get_content_type()
    charset = part.get_content_charset() or "utf-8"

    try:
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        text = payload.decode(charset, errors="replace")
    except Exception:
        return ""

    if content_type == "text/html":
        return _html_to_markdown(text)
    return text


def _html_to_markdown(html: str) -> str:
    """Convert HTML to simple Markdown-like text.

    Uses basic regex-based conversion to avoid external dependencies.
    For production use, consider installing 'markdownify' for better results.
    """
    # Remove style and script blocks
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Headers
    for i in range(1, 7):
        html = re.sub(
            rf'<h{i}[^>]*>(.*?)</h{i}>',
            lambda m: '#' * i + ' ' + m.group(1).strip(),
            html, flags=re.DOTALL | re.IGNORECASE
        )

    # Paragraphs and divs
    html = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', html, flags=re.DOTALL | re.IGNORECASE)

    # Links: <a href="url">text</a> → [text](url)
    html = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        r'[\2](\1)',
        html, flags=re.DOTALL | re.IGNORECASE
    )

    # Bold and italic
    html = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)

    # List items
    html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL | re.IGNORECASE)

    # Line breaks
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)

    # Remove remaining tags
    html = re.sub(r'<[^>]+>', '', html)

    # Clean up HTML entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), html)

    # Collapse excessive whitespace
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = re.sub(r' {2,}', ' ', html)

    return html.strip()


def _extract_body(msg) -> str:
    """Extract the best text body from an email message.

    Prefers plain text if available; falls back to HTML converted to text.
    """
    plain_parts = []
    html_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                plain_parts.append(_get_text_from_part(part))
            elif content_type == "text/html":
                html_parts.append(_get_text_from_part(part))
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(_get_text_from_part(msg))
        elif content_type == "text/html":
            html_parts.append(_get_text_from_part(msg))

    # Prefer plain text
    if plain_parts:
        return "\n".join(p for p in plain_parts if p.strip())
    if html_parts:
        return "\n".join(p for p in html_parts if p.strip())
    return ""


def _extract_sender(msg) -> Tuple[str, str]:
    """Extract sender name and email address.

    Returns (name, address).
    """
    from_header = msg.get("From", "")
    name, addr = parseaddr(from_header)
    name = _decode_header_value(name)
    return name, addr.lower()


def _extract_date(msg) -> Optional[datetime]:
    """Extract and parse the email Date header."""
    date_str = msg.get("Date", "")
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        return None


def _compute_message_id(msg) -> str:
    """Generate a URL-friendly unique ID from the email Message-ID."""
    mid = msg.get("Message-ID", "")
    if mid:
        # Use hash of Message-ID for privacy and URL-safety
        return hashlib.sha256(mid.encode()).hexdigest()[:16]
    # Fallback: hash subject + date + from
    raw = f"{msg.get('Subject', '')}{msg.get('Date', '')}{msg.get('From', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_sender_allowed(sender_addr: str, whitelist: List[str]) -> bool:
    """Check if sender address matches any whitelist entry.

    Supports partial matching: 'newsletter@example.com' matches 'example.com'.
    """
    if not whitelist:
        # If no whitelist configured, allow all
        return True
    for allowed in whitelist:
        allowed_lower = allowed.lower()
        if allowed_lower in sender_addr or sender_addr.endswith(allowed_lower):
            return True
        # Also match display name
        if "@" in allowed_lower and allowed_lower == sender_addr:
            return True
    return False


def _parse_email_to_article(msg, sender_whitelist: List[str] = None) -> Optional[Article]:
    """Convert an email.message.Message to an Article.

    Returns None if the email should be skipped.
    """
    if sender_whitelist is None:
        sender_whitelist = []

    sender_name, sender_addr = _extract_sender(msg)

    # Apply whitelist filter
    if sender_whitelist and not _is_sender_allowed(sender_addr, sender_whitelist):
        return None

    subject = _decode_header_value(msg.get("Subject", "Untitled Newsletter"))
    body = _extract_body(msg)
    published_at = _extract_date(msg)
    msg_id = _compute_message_id(msg)

    if not body.strip():
        logger.debug(f"Skipping email with empty body: {subject}")
        return None

    # Remove common newsletter footers (unsubscribe links, etc.)
    body = _clean_newsletter_footer(body)

    article = Article(
        url=f"email://{msg_id}",
        title=subject,
        source=ArticleSource.EMAIL,
        content_raw=body,
        author=sender_name or sender_addr,
        published_at=published_at,
        source_name=sender_name or sender_addr,
        tags=["newsletter"],
    )
    article.compute_hash()
    return article


def _clean_newsletter_footer(text: str) -> str:
    """Remove common newsletter footer patterns."""
    # Remove unsubscribe blocks
    text = re.sub(
        r'\n.*(?:unsubscribe|opt.?out|click here to unsubscribe).*\n.*',
        '', text, flags=re.IGNORECASE | re.DOTALL
    )
    # Remove "You received this email because..."
    text = re.sub(
        r'\n.*(?:you received this email|you\'re receiving this).*',
        '', text, flags=re.IGNORECASE | re.DOTALL
    )
    # Remove mailing address blocks (common in US newsletters)
    text = re.sub(
        r'\n\d+\s+\w+\s+(?:St|Street|Ave|Avenue|Blvd|Road|Rd).*?(?:\n\n|\Z)',
        '', text, flags=re.IGNORECASE | re.DOTALL
    )
    return text.strip()


def extract_emails(
    imap_server: str = "",
    imap_port: int = 993,
    username: str = "",
    app_password: str = "",
    sender_whitelist: Optional[List[str]] = None,
    max_emails: int = 10,
    mark_as_read: bool = True,
) -> List[Article]:
    """Main entry point: connect to IMAP, fetch newsletters, return Articles.

    Args:
        imap_server: IMAP server hostname.
        imap_port: IMAP port (default 993 for SSL).
        username: IMAP login username.
        app_password: IMAP app-specific password.
        sender_whitelist: List of allowed sender addresses/domains.
        max_emails: Maximum emails to process.
        mark_as_read: Whether to mark processed emails as read.

    Returns:
        List of Article objects from newsletter emails.
    """
    import imaplib

    # Resolve from env if not provided
    if not imap_server:
        imap_server = os.getenv("EMAIL_IMAP_SERVER", "")
    if not username:
        username = os.getenv("EMAIL_USERNAME", "")
    if not app_password:
        app_password = os.getenv("EMAIL_APP_PASSWORD", "")
    if sender_whitelist is None:
        sender_whitelist = []

    if not imap_server or not username or not app_password:
        logger.error("Email config incomplete — need IMAP server, username, and password")
        return []

    logger.info(f"Connecting to IMAP: {imap_server}:{imap_port}")

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    except Exception as e:
        logger.error(f"IMAP connection failed: {e}")
        return []

    try:
        mail.login(username, app_password)
        mail.select("INBOX", readonly=not mark_as_read)

        # Search for unseen emails
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            logger.warning("IMAP search returned no results")
            return []

        message_ids = data[0].split()
        if not message_ids:
            logger.info("No unread emails found")
            return []

        # Limit to max_emails
        message_ids = message_ids[-max_emails:]  # Most recent first
        logger.info(f"Found {len(message_ids)} unread emails to check")

        articles = []
        for mid in message_ids:
            try:
                status, msg_data = mail.fetch(mid, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email, policy=email.policy.default)

                article = _parse_email_to_article(msg, sender_whitelist)
                if article:
                    articles.append(article)

                # Mark as seen
                if mark_as_read:
                    mail.store(mid, '+FLAGS', '\\Seen')

            except Exception as e:
                logger.error(f"Error processing email {mid}: {e}")
                continue

        logger.info(f"Extracted {len(articles)} newsletter articles")
        return articles

    except Exception as e:
        logger.error(f"IMAP error: {e}")
        return []
    finally:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass
