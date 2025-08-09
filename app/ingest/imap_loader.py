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
    """Fetch emails from IMAP server with secure connection and error handling"""
    from app.security.encryption import settings_manager
    from app.security.sanitizer import sanitizer
    
    # Input validation
    if not isinstance(limit, int) or limit < 1 or limit > 10000:
        limit = 200  # Safe default
    
    # Get secure credentials
    try:
        secure_password = settings_manager.get_secure_imap_password()
        if not secure_password:
            print("IMAP password not available or invalid")
            return []
    except Exception as e:
        print(f"Failed to get secure IMAP password: {e}")
        return []
    
    # Validate IMAP settings
    if not all([settings.imap_host, settings.imap_user]):
        print("IMAP host or user not configured")
        return []
    
    # Sanitize IMAP settings
    try:
        safe_host = sanitizer.sanitize_field_input(settings.imap_host, "IMAP host")
        safe_user = sanitizer.sanitize_field_input(settings.imap_user, "IMAP user")
        safe_folder = sanitizer.sanitize_field_input(settings.imap_folder, "IMAP folder")
    except ValueError as e:
        print(f"IMAP settings validation failed: {e}")
        return []
    
    # Establish secure IMAP connection
    try:
        # Create SSL context with certificate verification
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Connect with SSL certificate validation
        imap = imaplib.IMAP4_SSL(
            safe_host, 
            settings.imap_port,
            ssl_context=ssl_context
        )
        
        # Authenticate with secure password
        imap.login(safe_user, secure_password)
        imap.select(safe_folder)
        
        print(f"✅ Secure IMAP connection established to {safe_host}")
        
    except ssl.SSLError as e:
        print(f"SSL certificate validation failed: {e}")
        return []
    except imaplib.IMAP4.error as e:
        print(f"IMAP authentication failed: {e}")
        return []
    except Exception as e:
        print(f"Failed to establish secure IMAP connection: {e}")
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
            
            # Parse email message with clean parser
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Use clean email parser
            from app.ingest.email_parser import email_parser
            parsed_email = email_parser.parse_email(msg)
            
            # Apply filters using clean sender and subject
            if settings.filter_from:
                if not any(f.lower() in parsed_email["sender"].lower() for f in settings.filter_from):
                    continue
            if settings.filter_subject:
                if not any(f.lower() in parsed_email["subject"].lower() for f in settings.filter_subject):
                    continue
            
            # Create clean email record
            email_record = {
                "sender": parsed_email["sender"],
                "subject": parsed_email["subject"],
                "cc_recipients": parsed_email["cc_recipients"],
                "body": parsed_email["body"],
                "date": parsed_email["date"],
                "message_id": parsed_email["message_id"],
                "uid": str(mail_id),
                # Keep original fields for backward compatibility
                "from": parsed_email["from"],
                "raw_subject": parsed_email["raw_subject"]
            }
            
            # Sanitize email data before adding to results
            try:
                safe_record = sanitizer.sanitize_email_content(email_record)
                results.append(safe_record)
            except Exception as e:
                print(f"Email sanitization failed for UID {mail_id}: {e}")
                errors += 1
                continue
            
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
    """Save email records to encrypted JSON file with security measures"""
    from app.security.encryption import credential_manager
    from app.security.sanitizer import sanitizer
    
    if not records:
        print("No emails to save")
        return None
    
    # Input validation
    if not isinstance(records, list) or len(records) > 50000:
        print("Invalid or too many email records")
        return None
    
    # Create secure data directory with proper permissions
    data_dir = "data/raw"
    os.makedirs(data_dir, mode=0o700, exist_ok=True)  # Only owner can access
    
    # Generate secure filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"emails_{timestamp}.json.enc"
    path = os.path.join(data_dir, filename)
    
    try:
        # Validate and sanitize all records
        sanitized_records = []
        for i, record in enumerate(records):
            try:
                if sanitizer.validate_json_structure(record):
                    sanitized_record = sanitizer.sanitize_email_content(record)
                    sanitized_records.append(sanitized_record)
                else:
                    print(f"Skipping invalid email record {i}")
            except Exception as e:
                print(f"Failed to sanitize email record {i}: {e}")
                continue
        
        if not sanitized_records:
            print("No valid email records to save")
            return None
        
        # Serialize and encrypt data
        import json
        json_data = json.dumps(sanitized_records, ensure_ascii=False, indent=2, default=str)
        encrypted_data = credential_manager.encrypt_credential(json_data)
        
        # Save encrypted data with secure file permissions
        with open(path, "w", encoding="utf-8") as f:
            f.write(encrypted_data)
        
        # Set restrictive file permissions (owner read/write only)
        os.chmod(path, 0o600)
        
        print(f"✅ Securely saved {len(sanitized_records)} emails to {path}")
        return path
        
    except Exception as e:
        print(f"Error saving emails securely: {e}")
        # Clean up partial file if it exists
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
        return None