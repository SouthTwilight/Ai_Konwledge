"""Tests for Email Newsletter Extractor."""
from __future__ import annotations

import email
import email.policy
from datetime import datetime
from unittest.mock import patch, MagicMock, call

import pytest

from pipeline.models import ArticleSource


# --- Fixtures ---

def _make_email_message(
    subject: str = "Test Newsletter",
    from_addr: str = "newsletter@example.com",
    body_plain: str = "Hello, this is a test newsletter.",
    body_html: str = "<p>Hello, this is a test newsletter.</p>",
    date: str = "Sat, 10 May 2026 08:00:00 +0000",
    message_id: str = "<msg123@example.com>",
):
    """Build a raw email bytes for testing."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["Date"] = date
    msg["Message-ID"] = message_id

    if body_plain:
        msg.attach(MIMEText(body_plain, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    return msg.as_bytes()


def _make_plain_email(
    subject: str = "Plain Newsletter",
    from_addr: str = "news@test.com",
    body: str = "Plain text content here.",
):
    """Build a plain text email."""
    from email.mime.text import MIMEText
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["Date"] = "Fri, 09 May 2026 10:00:00 +0000"
    msg["Message-ID"] = "<plain123@test.com>"
    return msg.as_bytes()


# --- Tests: _decode_header_value ---

def test_decode_header_plain():
    from pipeline.extractors.email_extractor import _decode_header_value
    assert _decode_header_value("Hello World") == "Hello World"


def test_decode_header_encoded():
    from pipeline.extractors.email_extractor import _decode_header_value
    # UTF-8 encoded subject
    result = _decode_header_value("=?utf-8?B?5rWL6K+V5paH5pys?=")
    assert len(result) > 0  # Should decode to Chinese characters


def test_decode_header_empty():
    from pipeline.extractors.email_extractor import _decode_header_value
    assert _decode_header_value("") == ""


# --- Tests: _html_to_markdown ---

def test_html_to_markdown_links():
    from pipeline.extractors.email_extractor import _html_to_markdown
    html = '<a href="https://example.com">Click here</a>'
    result = _html_to_markdown(html)
    assert "[Click here](https://example.com)" in result


def test_html_to_markdown_bold():
    from pipeline.extractors.email_extractor import _html_to_markdown
    html = "<p>This is <b>bold</b> text.</p>"
    result = _html_to_markdown(html)
    assert "**bold**" in result


def test_html_to_markdown_removes_style():
    from pipeline.extractors.email_extractor import _html_to_markdown
    html = "<style>body{color:red}</style><p>Hello</p>"
    result = _html_to_markdown(html)
    assert "color" not in result
    assert "Hello" in result


def test_html_to_markdown_headers():
    from pipeline.extractors.email_extractor import _html_to_markdown
    html = "<h2>Section Title</h2>"
    result = _html_to_markdown(html)
    assert "## Section Title" in result


def test_html_to_markdown_entities():
    from pipeline.extractors.email_extractor import _html_to_markdown
    html = "<p>Hello&nbsp;&amp;&nbsp;World</p>"
    result = _html_to_markdown(html)
    assert "Hello & World" in result


# --- Tests: _extract_body ---

def test_extract_body_multipart():
    from pipeline.extractors.email_extractor import _extract_body
    raw = _make_email_message(body_plain="Plain text", body_html="<p>HTML text</p>")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    body = _extract_body(msg)
    assert "Plain text" in body


def test_extract_body_html_only():
    from pipeline.extractors.email_extractor import _extract_body
    raw = _make_email_message(body_plain="", body_html="<p>HTML only</p>")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    body = _extract_body(msg)
    assert "HTML only" in body


def test_extract_body_plain_only():
    from pipeline.extractors.email_extractor import _extract_body
    raw = _make_plain_email(body="Just plain text")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    body = _extract_body(msg)
    assert "Just plain text" in body


# --- Tests: _is_sender_allowed ---

def test_sender_allowed_exact_match():
    from pipeline.extractors.email_extractor import _is_sender_allowed
    assert _is_sender_allowed("newsletter@example.com", ["newsletter@example.com"])


def test_sender_allowed_domain_match():
    from pipeline.extractors.email_extractor import _is_sender_allowed
    assert _is_sender_allowed("anything@example.com", ["example.com"])


def test_sender_not_allowed():
    from pipeline.extractors.email_extractor import _is_sender_allowed
    assert not _is_sender_allowed("spam@evil.com", ["example.com"])


def test_sender_allowed_empty_whitelist():
    from pipeline.extractors.email_extractor import _is_sender_allowed
    # Empty whitelist = allow all
    assert _is_sender_allowed("anyone@anywhere.com", [])


# --- Tests: _parse_email_to_article ---

def test_parse_email_to_article_basic():
    from pipeline.extractors.email_extractor import _parse_email_to_article
    raw = _make_email_message(
        subject="Weekly Tech Digest",
        from_addr="digest@technews.com",
    )
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    article = _parse_email_to_article(msg, sender_whitelist=["technews.com"])

    assert article is not None
    assert article.source == ArticleSource.EMAIL
    assert article.title == "Weekly Tech Digest"
    assert article.source_name == "digest@technews.com"
    assert article.tags == ["newsletter"]
    assert article.content_hash != ""
    assert article.url.startswith("email://")


def test_parse_email_filters_by_whitelist():
    from pipeline.extractors.email_extractor import _parse_email_to_article
    raw = _make_email_message(from_addr="promo@random.com")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    article = _parse_email_to_article(msg, sender_whitelist=["allowed.com"])
    assert article is None


def test_parse_email_skips_empty_body():
    from pipeline.extractors.email_extractor import _parse_email_to_article
    raw = _make_email_message(body_plain="", body_html="")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    article = _parse_email_to_article(msg)
    assert article is None


def test_parse_email_extracts_date():
    from pipeline.extractors.email_extractor import _parse_email_to_article
    raw = _make_email_message(date="Sat, 10 May 2026 08:00:00 +0000")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    article = _parse_email_to_article(msg)
    assert article is not None
    assert article.published_at is not None


# --- Tests: _clean_newsletter_footer ---

def test_clean_footer_unsubscribe():
    from pipeline.extractors.email_extractor import _clean_newsletter_footer
    text = "Main content here.\n\nTo unsubscribe click here.\nhttps://unsubscribe.link"
    result = _clean_newsletter_footer(text)
    assert "unsubscribe" not in result.lower()
    assert "Main content" in result


def test_clean_footer_received_because():
    from pipeline.extractors.email_extractor import _clean_newsletter_footer
    text = "Main content.\n\nYou received this email because you subscribed."
    result = _clean_newsletter_footer(text)
    assert "received this email" not in result.lower()


# --- Tests: extract_emails (integration with mocked IMAP) ---

def test_extract_emails_no_config():
    from pipeline.extractors.email_extractor import extract_emails
    articles = extract_emails(imap_server="", username="", app_password="")
    assert articles == []


def test_extract_emails_with_mock_imap():
    from pipeline.extractors.email_extractor import extract_emails

    mock_mail = MagicMock()
    mock_mail.search.return_value = ("OK", [b"1 2 3"])
    mock_mail.fetch.side_effect = [
        ("OK", [(b"1 (RFC822 {123}", _make_email_message(
            subject="Newsletter #1",
            from_addr="news@example.com",
            body_plain="Content 1",
        )), b")"]),
        ("OK", [(b"2 (RFC822 {123}", _make_plain_email(
            subject="Newsletter #2",
            from_addr="news@example.com",
            body="Content 2",
        )), b")"]),
        ("OK", [(b"3 (RFC822 {123}", _make_email_message(
            subject="Spam",
            from_addr="spam@evil.com",
            body_plain="Buy stuff!",
        )), b")"]),
    ]

    with patch("imaplib.IMAP4_SSL", return_value=mock_mail):
        articles = extract_emails(
            imap_server="imap.example.com",
            username="user@example.com",
            app_password="password",
            sender_whitelist=["example.com"],
            max_emails=5,
        )

        # Only whitelisted senders
        assert len(articles) == 2
        assert all(a.source == ArticleSource.EMAIL for a in articles)
        assert articles[0].title == "Newsletter #1"
        assert articles[1].title == "Newsletter #2"


def test_extract_emails_empty_inbox():
    from pipeline.extractors.email_extractor import extract_emails

    mock_mail = MagicMock()
    mock_mail.search.return_value = ("OK", [b""])

    with patch("imaplib.IMAP4_SSL", return_value=mock_mail):
        articles = extract_emails(
            imap_server="imap.example.com",
            username="user@example.com",
            app_password="password",
        )
        assert articles == []


def test_extract_emails_connection_failure():
    from pipeline.extractors.email_extractor import extract_emails

    with patch("imaplib.IMAP4_SSL", side_effect=Exception("Connection refused")):
        articles = extract_emails(
            imap_server="imap.example.com",
            username="user@example.com",
            app_password="password",
        )
        assert articles == []
