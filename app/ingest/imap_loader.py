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

def fetch_emails(settings, limit=200, since_date=None):
    """
    Fetch emails from IMAP server with secure connection and error handling.
    
    Args:
        settings: Application settings object
        limit: Maximum number of emails to fetch (default 200)
        since_date: Optional datetime to fetch emails since (for incremental updates)
    
    Returns:
        List of email dictionaries with metadata and content
    """
    from app.security.encryption import settings_manager
    from app.security.sanitizer import sanitizer
    
    # Input validation
    if not isinstance(limit, int) or limit < 1 or limit > 10000:
        limit = 200  # Safe default
    
    # Get secure credentials
    try:
        secure_password = settings_manager.get_secure_imap_password()
        if not secure_password:
            # Fallback to direct password from settings if secure method fails
            secure_password = settings.imap_password
            if not secure_password:
                print("IMAP password not available or invalid")
                return []
    except Exception as e:
        # Fallback to direct password from settings
        secure_password = settings.imap_password
        if not secure_password:
            print(f"Failed to get IMAP password: {e}")
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
        
        print(f"[SUCCESS] Secure IMAP connection established to {safe_host}")
        
    except ssl.SSLError as e:
        print(f"SSL certificate validation failed: {e}")
        return []
    except imaplib.IMAP4.error as e:
        print(f"IMAP authentication failed: {e}")
        return []
    except Exception as e:
        print(f"Failed to establish secure IMAP connection: {e}")
        return []

    # Build search criteria based on date filter
    if since_date:
        # Format date for IMAP search (DD-Mon-YYYY format)
        from datetime import datetime
        if isinstance(since_date, datetime):
            date_str = since_date.strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{date_str}")'
            print(f"[INFO] Fetching emails since {date_str}")
        else:
            search_criteria = "ALL"
    else:
        search_criteria = "ALL"
    
    # Search for emails based on criteria
    try:
        if search_criteria == "ALL":
            status, messages = imap.search(None, "ALL")
        else:
            status, messages = imap.search(None, search_criteria)
    except Exception as e:
        print(f"Search failed with criteria '{search_criteria}': {e}")
        # Fallback to ALL if date search fails
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
            
            # Convert email message to dict format for parsing
            # Decode headers properly using our safe decoder
            email_dict = {
                'from': safe_decode_header(msg.get('From', '')),
                'to': safe_decode_header(msg.get('To', '')),
                'cc': safe_decode_header(msg.get('Cc', '')),
                'subject': safe_decode_header(msg.get('Subject', '')),
                'date': msg.get('Date', ''),  # Date doesn't need decoding
                'message_id': msg.get('Message-ID', ''),
                'uid': mail_id.decode()
            }
            
            # Extract body text
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body += payload.decode('utf-8', errors='ignore')
                        except:
                            pass
                    elif content_type == "text/html" and not body:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                html_content = payload.decode('utf-8', errors='ignore')
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html_content, 'html.parser')
                                body = soup.get_text()
                        except:
                            pass
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                except:
                    body = str(msg.get_payload())
            
            email_dict['body'] = body.strip()
            
            # Use MailParserAdapter for parsing
            from app.ingest.mailparser_adapter import MailParserAdapter
            parser = MailParserAdapter()
            parsed_email = parser.parse_email_advanced(email_dict)
            
            # Apply filters using parsed data - FIXED to use correct keys
            sender_name = parsed_email.get('clean_sender', '')
            sender_email = parsed_email.get('clean_sender', '')  # Parser returns full sender string
            subject = parsed_email.get('clean_subject', '')
            
            if settings.filter_from:
                sender_combined = f"{sender_name} {sender_email}".lower()
                if not any(f.lower() in sender_combined for f in settings.filter_from):
                    continue
            if settings.filter_subject:
                if not any(f.lower() in subject.lower() for f in settings.filter_subject):
                    continue
            
            # Create email record using parsed data
            email_record = {
                # Basic fields for backward compatibility - FIXED to use correct keys
                'from': parsed_email.get('clean_sender', email_dict.get('from', '')),
                'to': email_dict.get('to', ''),  # Parser doesn't extract 'to' field
                'subject': parsed_email.get('clean_subject', email_dict.get('subject', '')),
                'date': parsed_email.get('date', email_dict.get('date', '')),
                'body': parsed_email.get('clean_body', ''),
                'message_id': email_dict.get('message_id', ''),
                'uid': email_dict.get('uid', ''),
                
                # Enhanced fields - using actual parsed data
                'from_name': parsed_email.get('clean_sender', ''),
                'from_email': parsed_email.get('clean_sender', ''),
                'to_email': email_dict.get('to', ''),
                'clean_body': parsed_email.get('clean_body', ''),
                'quality_score': parsed_email.get('quality_score', 0),
                'marketing_score': parsed_email.get('marketing_score', 0),
                'content_ratio': parsed_email.get('content_ratio', 0),
                'language_confidence': parsed_email.get('language_confidence', 0)
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
    """Save email records to JSON file"""
    from app.security.sanitizer import sanitizer
    import json
    
    if not records:
        print("No emails to save")
        return None
    
    # Input validation
    if not isinstance(records, list) or len(records) > 50000:
        print("Invalid or too many email records")
        return None
    
    # Create data directory
    data_dir = "data/raw"
    os.makedirs(data_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"emails_{timestamp}.json"
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
        
        # Save data as plain JSON (no encryption for now)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sanitized_records, ensure_ascii=False, indent=2, default=str, fp=f)
        
        print(f"[SUCCESS] Saved {len(sanitized_records)} emails to {path}")
        return path
        
    except Exception as e:
        print(f"Error saving emails: {e}")
        # Clean up partial file if it exists
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
        return None