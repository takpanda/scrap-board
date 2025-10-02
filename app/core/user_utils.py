"""User utility functions for handling user identification."""

from typing import Optional


GUEST_USER_ID = "guest"


def normalize_user_id(user_id: Optional[str]) -> str:
    """
    Normalize user_id to use a consistent guest identifier.
    
    When user_id is None or empty, return the standard guest user ID.
    Otherwise, return the user_id as-is.
    
    Args:
        user_id: The user ID to normalize, may be None
        
    Returns:
        The normalized user ID - "guest" for unidentified users, or the original user_id
    """
    if user_id is None or (isinstance(user_id, str) and not user_id.strip()):
        return GUEST_USER_ID
    return str(user_id).strip()
