import imaplib
import email
import os
from datetime import datetime
from email.header import decode_header
from app.config.settings import get_settings

def safe_decode_header(header_value):
    """Safely decode email header, handling None and malformed values"""
    if header_value is None:
        return ""
    
    try:
        decoded_parts = decode_header(header_value)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or 'utf-8', errors='ignore'))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(str(part))
        return ' '.join(result)
    except Exception as e:
        # If all else fails, return string representation
        return str(header_value) if header_value else ""

def fetch_emails(settings, limit=200):
    """Fetch emails from IMAP server with robust error handling"""
    try:
        imap = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_folder)
    except Exception as e:
        print(f"Failed to connect to IMAP server: {e}")
        return []

    # Search for all emails
    status, messages = imap.search(None, "ALL")
    if status != "OK":
        print("Failed to search emails")
        return []

    email_ids = messages[0].split()
    results = []
    errors = 0

    print(f"Found {len(email_ids)} emails. Fetching last {min(limit, len(email_ids))}...")

    for i, mail_id in enumerate(reversed(email_ids)):
        if i >= limit:
            break
        
        try:
            status, msg_data = imap.fetch(mail_id, "(RFC822)")
            if status != "OK":
                errors += 1
                continue
            
            # Parse email message
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Safely extract headers
            from_ = safe_decode_header(msg.get("From"))
            subject = safe_decode_header(msg.get("Subject"))
            date = msg.get("Date", "")
            message_id = msg.get("Message-ID", "")
            
            # Apply filters if configured
            if settings.filter_from:
                if not any(f.lower() in from_.lower() for f in settings.filter_from):
                    continue
            if settings.filter_subject:
                if not any(f.lower() in subject.lower() for f in settings.filter_subject):
                    continue
            
            # Extract body
            body = ""
            try:
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        disp = str(part.get("Content-Disposition", ""))
                        
                        # Get text/plain parts
                        if ctype == "text/plain" and "attachment" not in disp:
                            try:
                                charset = part.get_content_charset() or 'utf-8'
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(charset, errors='ignore')
                                    break
                            except Exception as e:
                                print(f"Error decoding body for email {i}: {e}")
                                continue
                else:
                    # Single part message
                    try:
                        charset = msg.get_content_charset() or 'utf-8'
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(charset, errors='ignore')
                    except Exception as e:
                        print(f"Error decoding body for email {i}: {e}")
                        body = ""
            except Exception as e:
                print(f"Error extracting body for email {i}: {e}")
                body = ""
            
            # Add to results
            results.append({
                "from": from_ or "Unknown",
                "subject": subject or "No Subject",
                "body": body,
                "date": date,
                "message_id": message_id,
                "uid": str(mail_id)
            })
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"Processed {i + 1}/{min(limit, len(email_ids))} emails...")
                
        except Exception as e:
            print(f"Error processing email {mail_id}: {e}")
            errors += 1
            continue

    # Close connection
    try:
        imap.close()
        imap.logout()
    except:
        pass

    print(f"Successfully fetched {len(results)} emails. Errors: {errors}")
    return results


def save_raw_emails(records):
    """Save email records to JSON file"""
    if not records:
        print("No emails to save")
        return None
    
    os.makedirs("data/raw", exist_ok=True)
    path = os.path.join("data/raw", f"emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    import json
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2, default=str)
        print(f"Saved {len(records)} emails to {path}")
        return path
    except Exception as e:
        print(f"Error saving emails: {e}")
        return None