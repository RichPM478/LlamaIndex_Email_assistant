import imaplib
import email
import os
from datetime import datetime
from email.header import decode_header
from app.config.settings import get_settings

def fetch_emails(settings, limit=200):
    imap = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    imap.login(settings.imap_user, settings.imap_password)
    imap.select(settings.imap_folder)

    # Search for all emails
    status, messages = imap.search(None, "ALL")
    if status != "OK":
        return []

    email_ids = messages[0].split()
    results = []

    for i, mail_id in enumerate(reversed(email_ids)):
        if i >= limit:
            break
        status, msg_data = imap.fetch(mail_id, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])

        from_ = decode_header(msg.get("From"))[0][0]
        if isinstance(from_, bytes):
            from_ = from_.decode()

        subject = decode_header(msg.get("Subject"))[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()

        # --- Filtering logic ---
        if settings.filter_from:
            if not any(f.lower() in from_.lower() for f in settings.filter_from):
                continue
        if settings.filter_subject:
            if not any(f.lower() in subject.lower() for f in settings.filter_subject):
                continue

        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in disp:
                    charset = part.get_content_charset()
                    body = part.get_payload(decode=True).decode(charset or "utf-8", errors="ignore")
                    break
        else:
            charset = msg.get_content_charset()
            body = msg.get_payload(decode=True).decode(charset or "utf-8", errors="ignore")

        results.append({
            "from": from_,
            "subject": subject,
            "body": body,
            "date": msg.get("Date")
        })

    imap.close()
    imap.logout()
    return results


def save_raw_emails(records):
    os.makedirs("data/raw", exist_ok=True)
    path = os.path.join("data/raw", f"emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return path
