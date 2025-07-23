import re
from typing import Union

def validate_age(age_text: str) -> bool:
    """
    Validate age input.
    
    Args:
        age_text: String representation of age
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        age = int(age_text)
        return 16 <= age <= 70
    except ValueError:
        return False

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.
    Accepts Ukrainian and Russian formats:
    - +380XXXXXXXXX (Ukrainian)
    - +7XXXXXXXXXX (Russian)
    
    Args:
        phone: Phone number string
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Check for valid Ukrainian and Russian phone number patterns
    patterns = [
        r'^\+380\d{9}$',  # +380XXXXXXXXX (Ukrainian)
        r'^\+7\d{10}$',   # +7XXXXXXXXXX (Russian)
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False

def validate_name(name: str) -> bool:
    """
    Validate name input.
    
    Args:
        name: Name string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if len(name.strip()) < 2:
        return False
    
    # Allow letters, spaces, hyphens, and apostrophes
    if not re.match(r"^[a-zA-Zа-яёА-ЯЁ\s\-']+$", name.strip()):
        return False
    
    return True

def sanitize_input(text: str, max_length: int = 100) -> str:
    """
    Sanitize user input to prevent potential issues.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    # Remove leading/trailing whitespace
    sanitized = text.strip()
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    
    return sanitized

def format_phone(phone: str) -> str:
    """
    Format phone number to a standard format.
    
    Args:
        phone: Raw phone number
        
    Returns:
        str: Formatted phone number
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Convert to +7 format
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    elif not cleaned.startswith('+7'):
        # If it doesn't start with +7, assume it's a 10-digit number
        if len(cleaned) == 10:
            cleaned = '+7' + cleaned
    
    # Format as +7 (XXX) XXX-XX-XX
    if len(cleaned) == 12 and cleaned.startswith('+7'):
        formatted = f"+7 ({cleaned[2:5]}) {cleaned[5:8]}-{cleaned[8:10]}-{cleaned[10:12]}"
        return formatted
    
    return phone  # Return original if formatting fails
