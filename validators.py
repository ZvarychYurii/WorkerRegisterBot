import re

def validate_age(age_text: str) -> bool:
    """
    Validate age input from 16 to 40
    """
    try:
        age = int(age_text)
        return 16 <= age <= 40
    except ValueError:
        return False

def validate_phone(phone: str) -> bool:
    """
    Validate Ukrainian phone numbers:
    - +380XXXXXXXXX
    - 0XXXXXXXXX
    Reject Russian numbers: +7, 8
    """
    phone = phone.strip().replace(" ", "").replace("-", "")

    # Reject Russian numbers
    if phone.startswith("+7") or phone.startswith("8"):
        return False

    # Ukrainian international
    if re.fullmatch(r"\+380\d{9}", phone):
        return True

    # Ukrainian local
    if re.fullmatch(r"0\d{9}", phone):
        return True

    return False

def format_phone_variants(phone: str) -> dict:
    """
    Convert phone into both international and local format.
    Args:
        phone (str): Raw number
    Returns:
        dict: {"international": "+380...", "local": "0..."}
    """
    phone = phone.strip().replace(" ", "").replace("-", "")

    # If local, convert to international
    if re.fullmatch(r"0\d{9}", phone):
        return {
            "international": "+38" + phone,
            "local": phone
        }

    # If international, convert to local
    if re.fullmatch(r"\+380\d{9}", phone):
        return {
            "international": phone,
            "local": "0" + phone[4:]
        }

    # Fallback: return as-is
    return {
        "international": phone,
        "local": phone
    }

def validate_name(name: str) -> bool:
    """
    Validate name (2+ characters, Ukrainian/English letters allowed)
    """
    name = name.strip()
    if len(name) < 2:
        return False
    return bool(re.fullmatch(r"[a-zA-Zа-яА-ЯёЁіІїЇєЄ\s\-']+", name))

def sanitize_input(text: str, max_length: int = 100) -> str:
    """
    Clean user input to prevent dangerous characters and limit length
    """
    sanitized = text.strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    return sanitized
