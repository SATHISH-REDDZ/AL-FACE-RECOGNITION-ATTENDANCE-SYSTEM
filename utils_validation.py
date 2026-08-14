"""
Input Validation & Security Guard Module
----------------------------------------
Provides strict validation rules to protect against path traversal, XSS,
SQL injection vectors, open redirects, and invalid base64 image payloads.
"""

import re
import base64
from urllib.parse import urlparse
import cv2
import numpy as np

# Student ID regex: 3-30 alphanumeric, hyphen, underscore characters ONLY
STUDENT_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_student_id(student_id: str) -> tuple[bool, str]:
    """Validates student ID format to strictly prevent path traversal attacks."""
    if not student_id or not isinstance(student_id, str):
        return False, "Student ID is required."
    
    student_id = student_id.strip()
    if not STUDENT_ID_REGEX.match(student_id):
        return False, "Student ID must be 3-30 characters long and contain only letters, numbers, hyphens, or underscores."
    
    # Path traversal safety check
    for dangerous in ["..", "/", "\\", ":", "~"]:
        if dangerous in student_id:
            return False, f"Invalid character '{dangerous}' in Student ID."
            
    return True, student_id

def validate_name(name: str) -> tuple[bool, str]:
    """Validates full name format and length."""
    if not name or not isinstance(name, str):
        return False, "Full Name is required."
    
    name = name.strip()
    if len(name) < 2 or len(name) > 100:
        return False, "Name must be between 2 and 100 characters long."
    
    # Control character check
    if any(ord(c) < 32 for c in name):
        return False, "Name contains invalid control characters."
        
    return True, name

def validate_department(department: str) -> tuple[bool, str]:
    """Validates department string."""
    if not department or not isinstance(department, str):
        return False, "Department is required."
    
    dept = department.strip()
    if len(dept) < 2 or len(dept) > 50:
        return False, "Department must be between 2 and 50 characters long."
        
    return True, dept

def validate_email(email: str) -> tuple[bool, str]:
    """Validates email format if provided."""
    if not email:
        return True, ""
    
    email = email.strip()
    if len(email) > 120:
        return False, "Email exceeds maximum length of 120 characters."
    
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email address format."
        
    return True, email

def validate_base64_image(b64_string: str, max_size_mb: float = 5.0) -> tuple[bool, str, np.ndarray]:
    """
    Validates base64 image string:
    - Decodes base64 data
    - Enforces max payload size
    - Verifies OpenCV image format and minimum dimensions (100x100)
    Returns (is_valid, error_msg, cv2_image_matrix)
    """
    if not b64_string or not isinstance(b64_string, str):
        return False, "Image frame data is required.", None

    try:
        # Strip header if present
        if ',' in b64_string:
            header, b64_data = b64_string.split(',', 1)
            # MIME check
            if 'image' not in header.lower():
                return False, "Invalid image MIME header.", None
        else:
            b64_data = b64_string

        img_bytes = base64.b64decode(b64_data)
        
        # Max size check
        size_mb = len(img_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"Image size ({size_mb:.2f}MB) exceeds maximum limit of {max_size_mb}MB.", None

        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return False, "Unable to decode image data.", None

        h, w = img.shape[:2]
        if w < 100 or h < 100:
            return False, f"Image dimensions ({w}x{h}) are too small. Minimum size is 100x100 pixels.", None

        return True, "", img
    except Exception as e:
        return False, f"Image validation error: {str(e)}", None

def safe_next_url(target: str, default: str = "/") -> str:
    """Prevents open redirect vulnerabilities by checking redirect URL targets."""
    if not target or not isinstance(target, str):
        return default
    
    target = target.strip()
    # Reject protocol-relative or absolute URLs
    if target.startswith("//") or target.startswith("\\\\") or ":" in target:
        return default
        
    ref_url = urlparse(target)
    if ref_url.scheme or ref_url.netloc:
        return default
        
    if not target.startswith("/"):
        return default
        
    return target
