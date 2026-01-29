"""
PayWithAccount transaction payload builders.

Provides factory functions to construct well-formed payloads for different
PayWithAccount transaction types (invoice, disburse, subscription, instalment).

Each builder:
- Reads settings.PAYWITHACCOUNT for defaults (mock_mode, request_type_*)
- Supports env var overrides for request_type_* without code changes
- Returns a dict ready to pass to PayWithAccountClient.transact()
- Includes comprehensive docstrings for expected field structure

Example:
    from core_apps.integrations.paywithaccount.payloads import build_invoice_payload
    
    payload = build_invoice_payload(
        amount_total=50000.00,
        customer_email="user@example.com",
        customer_name="John Doe",
        meta={"order_id": "12345"},
        currency="NGN",
        narrative="Purchase of goods"
    )
    result = client.transact(payload)
"""

from typing import Dict, Any, Optional
from django.conf import settings


def _get_request_type(config_key: str, default: str) -> str:
    """
    Retrieve request_type from settings, with env var override support.
    
    Looks for:
    1. settings.PAYWITHACCOUNT.get(config_key) — env-mapped value from PWA_REQUEST_TYPE_*
    2. Falls back to default if not found
    
    Args:
        config_key: Key in settings.PAYWITHACCOUNT (e.g., 'request_type_invoice')
        default: Fallback default value
        
    Returns:
        str: The request_type value to use
    """
    config = settings.PAYWITHACCOUNT
    return config.get(config_key, default)


def _get_mock_mode(mock_mode: Optional[str]) -> str:
    """
    Resolve mock_mode: explicit param takes precedence over settings default.
    
    Args:
        mock_mode: Explicit mock_mode or None to use settings default
        
    Returns:
        str: The mock_mode to use
    """
    if mock_mode is not None:
        return mock_mode
    return settings.PAYWITHACCOUNT.get('mock_mode', 'inspect')


def build_invoice_payload(
    amount_total: float,
    customer_email: str,
    customer_name: str,
    meta: Dict[str, Any],
    currency: str = "NGN",
    narrative: str = "",
    mock_mode: Optional[str] = None,
    request_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a transaction payload for invoice (payment collection) flow.
    
    Creates a payload for collecting payment from a customer with invoice details.
    Supports optional meta for associating with internal entities (e.g., orders, collections).
    
    Args:
        amount_total: Total amount to invoice (float, e.g., 50000.00)
        customer_email: Customer email address
        customer_name: Customer full name
        meta: Dict of metadata to attach (e.g., {"order_id": "12345", "goal_id": "abc"})
        currency: ISO currency code (default: "NGN")
        narrative: Optional description/reason for transaction
        mock_mode: Override settings mock_mode (e.g., "inspect", "true", "false")
        request_type: Override request_type (if None, reads from settings or PWA_REQUEST_TYPE_INVOICE)
        
    Returns:
        Dict ready to pass to PayWithAccountClient.transact()
        
    Example:
        payload = build_invoice_payload(
            amount_total=100000.00,
            customer_email="john@example.com",
            customer_name="John Doe",
            meta={"order_id": "ORD-123", "collection_id": "COL-456"},
            narrative="Invoice for goods purchased"
        )
        # {
        #     'transaction': {
        #         'type': 'debit',
        #         'amount': 100000.00,
        #         'currency': 'NGN',
        #         'request_type': 'invoice',
        #         'mock_mode': 'inspect',
        #         'narrative': 'Invoice for goods purchased',
        #         'customer': {
        #             'email': 'john@example.com',
        #             'name': 'John Doe'
        #         },
        #         'meta': {'order_id': 'ORD-123', 'collection_id': 'COL-456'}
        #     }
        # }
    """
    resolved_mock_mode = _get_mock_mode(mock_mode)
    resolved_request_type = request_type or _get_request_type('request_type_invoice', 'invoice')
    
    return {
        "transaction": {
            "type": "debit",
            "amount": amount_total,
            "currency": currency,
            "request_type": resolved_request_type,
            "mock_mode": resolved_mock_mode,
            "narrative": narrative,
            "customer": {
                "email": customer_email,
                "name": customer_name
            },
            "meta": meta or {}
        }
    }


def build_disburse_payload(
    amount: float,
    beneficiary_account: str,
    beneficiary_bank_code: str,
    meta: Dict[str, Any],
    currency: str = "NGN",
    narrative: str = "",
    mock_mode: Optional[str] = None,
    request_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a transaction payload for disbursement (payout) flow.
    
    Creates a payload for paying out funds to a beneficiary bank account.
    Typically used for refunds, commissions, or scheduled payouts.
    
    Args:
        amount: Amount to disburse (float, e.g., 25000.50)
        beneficiary_account: Destination bank account number
        beneficiary_bank_code: Bank code (e.g., "058" for GTBank)
        meta: Dict of metadata to attach (e.g., {"payout_id": "PO-789"})
        currency: ISO currency code (default: "NGN")
        narrative: Optional description/reason for payout
        mock_mode: Override settings mock_mode
        request_type: Override request_type (if None, reads PWA_REQUEST_TYPE_DISBURSE)
        
    Returns:
        Dict ready to pass to PayWithAccountClient.transact()
        
    Example:
        payload = build_disburse_payload(
            amount=50000.00,
            beneficiary_account="0123456789",
            beneficiary_bank_code="058",
            meta={"payout_id": "PO-001"},
            narrative="Commission payout"
        )
        # {
        #     'transaction': {
        #         'type': 'credit',
        #         'amount': 50000.00,
        #         'currency': 'NGN',
        #         'request_type': 'disburse',
        #         'mock_mode': 'inspect',
        #         'narrative': 'Commission payout',
        #         'beneficiary': {
        #             'account_number': '0123456789',
        #             'bank_code': '058'
        #         },
        #         'meta': {'payout_id': 'PO-001'}
        #     }
        # }
    """
    resolved_mock_mode = _get_mock_mode(mock_mode)
    resolved_request_type = request_type or _get_request_type('request_type_disburse', 'disburse')
    
    return {
        "transaction": {
            "type": "credit",
            "amount": amount,
            "currency": currency,
            "request_type": resolved_request_type,
            "mock_mode": resolved_mock_mode,
            "narrative": narrative,
            "beneficiary": {
                "account_number": beneficiary_account,
                "bank_code": beneficiary_bank_code
            },
            "meta": meta or {}
        }
    }


def build_subscription_payload(
    amount_total: float,
    schedule: Dict[str, Any],
    meta: Dict[str, Any],
    currency: str = "NGN",
    mock_mode: Optional[str] = None,
    request_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a transaction payload for recurring subscription flow.
    
    Creates a payload for setting up recurring charges (e.g., monthly subscriptions).
    The schedule dict should specify frequency and duration of charges.
    
    Args:
        amount_total: Total amount over subscription period (float, e.g., 120000.00)
        schedule: Dict specifying recurring charge details.
                  Expected keys (provider-dependent):
                  - 'frequency': 'daily', 'weekly', 'monthly', 'yearly', etc.
                  - 'interval': number of periods between charges (e.g., 1 for every month)
                  - 'duration': total number of charges or end_date
                  Example: {'frequency': 'monthly', 'interval': 1, 'duration': 12}
        meta: Dict of metadata to attach (e.g., {"subscription_id": "SUB-001"})
        currency: ISO currency code (default: "NGN")
        mock_mode: Override settings mock_mode
        request_type: Override request_type (if None, reads PWA_REQUEST_TYPE_SUBSCRIPTION)
        
    Returns:
        Dict ready to pass to PayWithAccountClient.transact()
        
    Example:
        payload = build_subscription_payload(
            amount_total=120000.00,
            schedule={'frequency': 'monthly', 'interval': 1, 'duration': 12},
            meta={"subscription_id": "SUB-001", "customer_id": "CUST-123"},
            currency="NGN"
        )
        # {
        #     'transaction': {
        #         'type': 'debit',
        #         'amount': 120000.00,
        #         'currency': 'NGN',
        #         'request_type': 'subscription',
        #         'mock_mode': 'inspect',
        #         'schedule': {'frequency': 'monthly', 'interval': 1, 'duration': 12},
        #         'meta': {'subscription_id': 'SUB-001', 'customer_id': 'CUST-123'}
        #     }
        # }
    """
    resolved_mock_mode = _get_mock_mode(mock_mode)
    resolved_request_type = request_type or _get_request_type('request_type_subscription', 'subscription')
    
    return {
        "transaction": {
            "type": "debit",
            "amount": amount_total,
            "currency": currency,
            "request_type": resolved_request_type,
            "mock_mode": resolved_mock_mode,
            "schedule": schedule or {},
            "meta": meta or {}
        }
    }


def build_instalment_payload(
    amount_total: float,
    down_payment: float,
    schedule: Dict[str, Any],
    meta: Dict[str, Any],
    currency: str = "NGN",
    mock_mode: Optional[str] = None,
    request_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a transaction payload for installment (BNPL-style) flow.
    
    Creates a payload for split payments over time with a down_payment upfront
    and remaining amount charged per schedule.
    
    Args:
        amount_total: Total amount including down_payment (float, e.g., 300000.00)
        down_payment: Initial payment amount (float, e.g., 100000.00)
        schedule: Dict specifying installment charge details.
                  Expected keys (provider-dependent):
                  - 'frequency': 'weekly', 'monthly', etc.
                  - 'num_installments': number of future payments (excluding down_payment)
                  - 'interval': periods between charges
                  Example: {'frequency': 'monthly', 'num_installments': 3, 'interval': 1}
        meta: Dict of metadata to attach (e.g., {"instalment_id": "INST-001"})
        currency: ISO currency code (default: "NGN")
        mock_mode: Override settings mock_mode
        request_type: Override request_type (if None, reads PWA_REQUEST_TYPE_INSTALMENT)
        
    Returns:
        Dict ready to pass to PayWithAccountClient.transact()
        
    Example:
        payload = build_instalment_payload(
            amount_total=300000.00,
            down_payment=100000.00,
            schedule={'frequency': 'monthly', 'num_installments': 3, 'interval': 1},
            meta={"instalment_id": "INST-001", "order_id": "ORD-999"},
            currency="NGN"
        )
        # {
        #     'transaction': {
        #         'type': 'debit',
        #         'amount': 300000.00,
        #         'currency': 'NGN',
        #         'request_type': 'instalment',
        #         'mock_mode': 'inspect',
        #         'down_payment': 100000.00,
        #         'schedule': {'frequency': 'monthly', 'num_installments': 3, 'interval': 1},
        #         'meta': {'instalment_id': 'INST-001', 'order_id': 'ORD-999'}
        #     }
        # }
    """
    resolved_mock_mode = _get_mock_mode(mock_mode)
    resolved_request_type = request_type or _get_request_type('request_type_instalment', 'instalment')
    
    return {
        "transaction": {
            "type": "debit",
            "amount": amount_total,
            "currency": currency,
            "request_type": resolved_request_type,
            "mock_mode": resolved_mock_mode,
            "down_payment": down_payment,
            "schedule": schedule or {},
            "meta": meta or {}
        }
    }
