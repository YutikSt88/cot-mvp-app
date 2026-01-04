from __future__ import annotations

import re


def normalize_contract_code(x) -> str:
    """
    Normalize contract code to standard format.
    
    - Convert to string, strip whitespace, uppercase
    - Remove trailing .0 (e.g., "099741.0" -> "099741")
    - Return normalized string (no zfill, preserves variable length)
    
    Examples:
        normalize_contract_code(99741) -> "99741"
        normalize_contract_code("099741.0") -> "099741"
        normalize_contract_code("06765A") -> "06765A"
        normalize_contract_code("12460+") -> "12460+"
    """
    s = str(x).strip().upper()
    # Remove trailing .0 if present
    s = re.sub(r"\.0$", "", s)
    return s


def is_valid_contract_code(code: str) -> bool:
    """
    Validate contract code format.
    
    Valid format: ^[A-Z0-9+]{1,20}$
    - Only uppercase letters, digits, and '+' allowed
    - Length: 1-20 characters
    
    Examples:
        is_valid_contract_code("099741") -> True
        is_valid_contract_code("06765A") -> True
        is_valid_contract_code("12460+") -> True
        is_valid_contract_code("abc123") -> False (lowercase)
        is_valid_contract_code("") -> False (empty)
    """
    if not isinstance(code, str):
        return False
    pattern = r"^[A-Z0-9+]{1,20}$"
    return bool(re.match(pattern, code))

