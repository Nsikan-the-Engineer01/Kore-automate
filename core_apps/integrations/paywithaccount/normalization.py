"""
PayWithAccount provider status normalization.

Normalizes diverse provider status strings into standardized internal enum values
and flags whether validation (e.g., OTP) is required.

The status mapping is configurable via settings.PAYWITHACCOUNT_STATUS_MAP
to support different provider status strings without code changes.

Status Enum Values:
    - SUCCESS: Transaction completed successfully
    - FAILED: Transaction failed (error, declined, rejected, etc.)
    - PENDING: Transaction in progress (processing, awaiting confirmation)

Example:
    from core_apps.integrations.paywithaccount.normalization import normalize_provider_status
    
    status, needs_validation = normalize_provider_status("WaitingForOTP")
    # status == "PENDING"
    # needs_validation == True
    
    status, needs_validation = normalize_provider_status("SUCCESS")
    # status == "SUCCESS"
    # needs_validation == False
"""

from typing import Tuple, Optional
from django.conf import settings

# Internal enum values
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_PENDING = "PENDING"

# Default mapping table: provider status strings -> (internal_status, needs_validation)
# Keys are normalized to uppercase for case-insensitive matching
DEFAULT_STATUS_MAP = {
    # Success indicators
    "SUCCESS": (STATUS_SUCCESS, False),
    "SUCCESSFUL": (STATUS_SUCCESS, False),
    "COMPLETED": (STATUS_SUCCESS, False),
    "APPROVED": (STATUS_SUCCESS, False),
    "CONFIRMED": (STATUS_SUCCESS, False),
    "SETTLED": (STATUS_SUCCESS, False),
    "PAID": (STATUS_SUCCESS, False),
    "PROCESSED": (STATUS_SUCCESS, False),
    
    # Failed indicators
    "FAILED": (STATUS_FAILED, False),
    "ERROR": (STATUS_FAILED, False),
    "DECLINED": (STATUS_FAILED, False),
    "REJECTED": (STATUS_FAILED, False),
    "CANCELLED": (STATUS_FAILED, False),
    "TIMEOUT": (STATUS_FAILED, False),
    "EXPIRED": (STATUS_FAILED, False),
    "ABORTED": (STATUS_FAILED, False),
    "INVALID": (STATUS_FAILED, False),
    
    # Pending indicators
    "PENDING": (STATUS_PENDING, False),
    "PROCESSING": (STATUS_PENDING, False),
    "INITIATED": (STATUS_PENDING, False),
    "IN_PROGRESS": (STATUS_PENDING, False),
    "AWAITING": (STATUS_PENDING, False),
    "QUEUED": (STATUS_PENDING, False),
    
    # OTP / Validation required
    "WAITINGFOROTP": (STATUS_PENDING, True),
    "WAITING_FOR_OTP": (STATUS_PENDING, True),
    "OTP_PENDING": (STATUS_PENDING, True),
    "PENDINGVALIDATION": (STATUS_PENDING, True),
    "PENDING_VALIDATION": (STATUS_PENDING, True),
    "VALIDATION_REQUIRED": (STATUS_PENDING, True),
    "AWAITING_VALIDATION": (STATUS_PENDING, True),
    "REQUIRES_OTP": (STATUS_PENDING, True),
    "OTP_REQUIRED": (STATUS_PENDING, True),
}


def _get_status_map() -> dict:
    """
    Retrieve status mapping from settings, with fallback to defaults.
    
    Looks for settings.PAYWITHACCOUNT_STATUS_MAP. If not defined,
    uses DEFAULT_STATUS_MAP.
    
    Returns:
        Dict mapping uppercase status strings to (internal_status, needs_validation) tuples
    """
    if hasattr(settings, 'PAYWITHACCOUNT_STATUS_MAP'):
        return settings.PAYWITHACCOUNT_STATUS_MAP
    return DEFAULT_STATUS_MAP


def normalize_provider_status(raw_status: Optional[str]) -> Tuple[str, bool]:
    """
    Normalize a provider status string to internal enum and validation flag.
    
    Maps provider-specific status strings (case-insensitive) to standardized
    internal values: SUCCESS, FAILED, or PENDING.
    
    Handles None gracefully by returning (PENDING, False).
    
    Args:
        raw_status: Provider status string (e.g., "WaitingForOTP", "SUCCESS", None)
        
    Returns:
        Tuple of (internal_status, needs_validation):
        - internal_status (str): One of SUCCESS, FAILED, PENDING
        - needs_validation (bool): True if status indicates OTP or validation required
        
    Example:
        >>> normalize_provider_status("SUCCESS")
        ("SUCCESS", False)
        
        >>> normalize_provider_status("WaitingForOTP")
        ("PENDING", True)
        
        >>> normalize_provider_status("DECLINED")
        ("FAILED", False)
        
        >>> normalize_provider_status(None)
        ("PENDING", False)
        
        >>> normalize_provider_status("UnknownStatus")
        ("PENDING", False)
    """
    # Handle None or empty status
    if not raw_status or not isinstance(raw_status, str):
        return STATUS_PENDING, False
    
    # Normalize to uppercase for lookup
    normalized_key = raw_status.upper().strip()
    
    # Get configured mapping
    status_map = _get_status_map()
    
    # Look up in map; default to PENDING if not found
    if normalized_key in status_map:
        return status_map[normalized_key]
    
    # Unknown status defaults to PENDING with no validation requirement
    return STATUS_PENDING, False


def get_available_status_map() -> dict:
    """
    Retrieve the currently active status mapping.
    
    Useful for debugging, logging, or dynamically checking what statuses are mapped.
    
    Returns:
        Dict of provider status -> (internal_status, needs_validation)
    """
    return _get_status_map()
