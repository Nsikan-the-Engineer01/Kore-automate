"""
Helper utilities for extracting common fields from provider webhook payloads.

Provides defensive helpers that try multiple common nesting paths and
key name variants (snake_case, camelCase, PascalCase). Functions return a string
or None when the field cannot be found.

These are intentionally conservative—no exceptions are raised on bad
input types. Numeric values are converted to strings.

Supported extraction helpers:
- extract_request_ref(): Request/transaction reference
- extract_provider_ref(): Provider transaction ID
- extract_status(): Transaction status
- extract_amount(): Transaction amount (numeric or string)
- extract_currency(): Currency code (usually 3-letter ISO code)
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union


def _get_by_path(payload: Dict[str, Any], path: List[str]) -> Optional[Any]:
    """Traverse a dict by a list of keys and return the value or None."""
    if not isinstance(payload, dict):
        return None
    node: Any = payload
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
        if node is None:
            return None
    return node


def _first_non_empty(payload: Dict[str, Any], paths: List[List[str]]) -> Optional[str]:
    """Return the first non-empty string found following candidate paths."""
    for path in paths:
        val = _get_by_path(payload, path)
        if val is None:
            continue
        # Accept numbers and UUIDs by converting to str, but reject empty strings
        try:
            s = str(val).strip() if isinstance(val, str) else str(val)
        except Exception:
            continue
        if s == "":
            continue
        return s
    return None


def _first_numeric(payload: Dict[str, Any], paths: List[List[str]]) -> Optional[Union[float, int]]:
    """Return the first numeric value found following candidate paths."""
    for path in paths:
        val = _get_by_path(payload, path)
        if val is None:
            continue
        # Accept numeric types or numeric strings
        try:
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, str):
                # Try to parse as float/decimal
                return float(val)
            if isinstance(val, Decimal):
                return float(val)
        except (ValueError, TypeError):
            continue
    return None


def extract_request_ref(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract request reference from provider payload.
    
    Tries multiple common nesting paths and key variants:
    - Top-level: request_ref, requestRef, request_reference
    - Nested in transaction, data, meta objects
    - Both snake_case and camelCase variants
    
    Args:
        payload: Webhook payload dict
        
    Returns:
        Request reference as string, or None if not found
        
    Example:
        >>> extract_request_ref({'request_ref': 'abc123'})
        'abc123'
        >>> extract_request_ref({'data': {'requestRef': 'def456'}})
        'def456'
    """
    candidate_paths = [
        # Top-level variants
        ["request_ref"],
        ["requestRef"],
        ["request_reference"],
        ["requestReference"],
        ["ref"],
        # Nested in common containers
        ["transaction", "request_ref"],
        ["transaction", "requestRef"],
        ["transaction", "reference"],
        ["data", "request_ref"],
        ["data", "requestRef"],
        ["data", "reference"],
        ["meta", "request_ref"],
        ["meta", "requestRef"],
        ["event", "request_ref"],
        ["event", "requestRef"],
        # Deeply nested
        ["payload", "request_ref"],
        ["payload", "requestRef"],
    ]
    return _first_non_empty(payload, candidate_paths)


def extract_provider_ref(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract provider transaction reference from payload.
    
    Tries multiple common nesting paths for provider-specific identifiers:
    - Top-level: provider_ref, providerRef, transaction_ref, transactionRef, txRef
    - Nested in transaction, data, meta objects
    - Both snake_case and camelCase variants
    
    Args:
        payload: Webhook payload dict
        
    Returns:
        Provider reference as string, or None if not found
        
    Example:
        >>> extract_provider_ref({'txRef': 'prov_12345'})
        'prov_12345'
        >>> extract_provider_ref({'data': {'transaction_ref': 'tx_abc'}})
        'tx_abc'
    """
    candidate_paths = [
        # Top-level variants
        ["provider_ref"],
        ["providerRef"],
        ["transaction_ref"],
        ["transactionRef"],
        ["txRef"],
        ["tx_ref"],
        ["reference"],
        ["ref"],
        # Provider-specific identifiers
        ["flutterwave_ref"],
        ["flutterwaveRef"],
        ["paystack_ref"],
        ["paystackRef"],
        ["monnify_ref"],
        ["monnifyRef"],
        # Nested in common containers
        ["transaction", "reference"],
        ["transaction", "ref"],
        ["transaction", "transaction_ref"],
        ["transaction", "transactionRef"],
        ["data", "reference"],
        ["data", "transaction_ref"],
        ["data", "transactionRef"],
        ["data", "txRef"],
        ["meta", "provider_ref"],
        ["meta", "providerRef"],
        ["event", "reference"],
    ]
    return _first_non_empty(payload, candidate_paths)


def extract_status(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract transaction status from provider payload.
    
    Tries multiple common nesting paths and status field names:
    - Top-level and nested in transaction, data, event, meta objects
    - Variants: status, transaction_status, transactionStatus, payment_status
    
    Args:
        payload: Webhook payload dict
        
    Returns:
        Status string (e.g., "SUCCESS", "PENDING", "FAILED"), or None if not found
        
    Example:
        >>> extract_status({'status': 'SUCCESS'})
        'SUCCESS'
        >>> extract_status({'data': {'transaction_status': 'completed'}})
        'completed'
    """
    candidate_paths = [
        # Top-level variants
        ["status"],
        ["transaction_status"],
        ["transactionStatus"],
        ["payment_status"],
        ["paymentStatus"],
        ["state"],
        # Nested in common containers
        ["transaction", "status"],
        ["transaction", "state"],
        ["data", "status"],
        ["data", "transaction_status"],
        ["data", "transactionStatus"],
        ["event", "status"],
        ["event", "state"],
        ["meta", "status"],
        ["response", "status"],
    ]
    return _first_non_empty(payload, candidate_paths)


def extract_amount(payload: Dict[str, Any]) -> Optional[Union[float, int]]:
    """
    Extract transaction amount from provider payload.
    
    Tries multiple common nesting paths and amount field names:
    - Top-level and nested in transaction, data, meta objects
    - Variants: amount, value, total, transaction_amount, payable_amount
    - Converts to float; returns None if not numeric
    
    Args:
        payload: Webhook payload dict
        
    Returns:
        Amount as float/int, or None if not found or not numeric
        
    Example:
        >>> extract_amount({'amount': 50000})
        50000
        >>> extract_amount({'data': {'total': '25000.50'}})
        25000.5
    """
    candidate_paths = [
        # Top-level variants
        ["amount"],
        ["value"],
        ["total"],
        ["total_amount"],
        ["totalAmount"],
        ["transaction_amount"],
        ["transactionAmount"],
        ["payable_amount"],
        ["payableAmount"],
        # Nested in common containers
        ["transaction", "amount"],
        ["transaction", "value"],
        ["transaction", "total"],
        ["data", "amount"],
        ["data", "value"],
        ["data", "total"],
        ["data", "transaction_amount"],
        ["meta", "amount"],
        ["meta", "value"],
        ["body", "amount"],
        ["body", "value"],
    ]
    return _first_numeric(payload, candidate_paths)


def extract_currency(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract currency code from provider payload.
    
    Tries multiple common nesting paths and currency field names:
    - Top-level and nested in transaction, data, meta objects
    - Variants: currency, currency_code, currencyCode, currencyType
    - Usually returns 3-letter ISO code (NGN, USD, GBP, etc.)
    
    Args:
        payload: Webhook payload dict
        
    Returns:
        Currency code as string (e.g., "NGN", "USD"), or None if not found
        
    Example:
        >>> extract_currency({'currency': 'NGN'})
        'NGN'
        >>> extract_currency({'data': {'currency_code': 'usd'}})
        'usd'
    """
    candidate_paths = [
        # Top-level variants
        ["currency"],
        ["currency_code"],
        ["currencyCode"],
        ["currency_type"],
        ["currencyType"],
        ["curr"],
        # Nested in common containers
        ["transaction", "currency"],
        ["transaction", "currency_code"],
        ["data", "currency"],
        ["data", "currency_code"],
        ["data", "currencyCode"],
        ["meta", "currency"],
        ["body", "currency"],
    ]
    return _first_non_empty(payload, candidate_paths)


def extract_event_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract event ID from provider webhook payload (for idempotency).
    
    Tries multiple common nesting paths and event identifier field names:
    - Top-level: event_id, eventId, event, id, webhook_id, webhookId, event_key
    - Nested: event.id, data.event_id, meta.event_id
    - Provider-specific: flutterwave_event_id, paystack_reference, monnify_transaction_ref
    
    Event IDs are used to detect and reject duplicate webhook deliveries from
    the provider, ensuring idempotency of webhook processing.
    
    Args:
        payload: Webhook payload dict
        
    Returns:
        Event ID as string if found, None otherwise
        
    Example:
        >>> extract_event_id({'event_id': 'evt_123abc'})
        'evt_123abc'
        >>> extract_event_id({'event': {'id': 'fw_evt_999'}})
        'fw_evt_999'
        >>> extract_event_id({'webhookId': 'wh_server_2024_001'})
        'wh_server_2024_001'
    """
    candidate_paths = [
        # Top-level variants
        ["event_id"],
        ["eventId"],
        ["event"],
        ["id"],
        ["webhook_id"],
        ["webhookId"],
        ["event_key"],
        ["eventKey"],
        # Provider-specific top-level
        ["flutterwave_event_id"],
        ["flutterwaveEventId"],
        ["paystack_reference"],
        ["monnify_transaction_ref"],
        # Nested in event
        ["event", "id"],
        ["event", "event_id"],
        # Nested in data
        ["data", "event_id"],
        ["data", "eventId"],
        ["data", "id"],
        # Nested in meta
        ["meta", "event_id"],
        ["meta", "eventId"],
        # Deeply nested
        ["payload", "event_id"],
        ["payload", "id"],
    ]
    return _first_non_empty(payload, candidate_paths)
