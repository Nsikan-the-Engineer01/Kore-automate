"""
Tests for webhook payload extraction utilities.

Tests all helpers (request_ref, provider_ref, status, amount, currency) against
multiple payload shapes representing different provider formats:

1. OnePipe-style: Nested under 'transaction' with rich metadata
2. Flat-style: All fields at top level
3. Meta-wrapped: Fields nested under 'data' and 'meta' objects
4. Provider-wrapped: Fields inside event/response wrapper (e.g., Flutterwave style)

Each test verifies both found and not-found cases.
"""
from decimal import Decimal
from typing import Any, Dict

from django.test import TestCase

from .utils import (
    extract_amount,
    extract_currency,
    extract_provider_ref,
    extract_request_ref,
    extract_status,
)


# ===== Sample Payload Shapes =====
# These represent real-world webhook payload structures from various providers.

PAYLOAD_ONEPIPE_STYLE: Dict[str, Any] = {
    """OnePipe style: nested transaction with rich structure"""
    "request_ref": "req_1001_abc",
    "webhook_id": "wh_123",
    "event_type": "transaction.completed",
    "timestamp": "2024-01-15T10:30:00Z",
    "transaction": {
        "transaction_ref": "txn_server_2024_001",
        "requestRef": "req_1001_abc",
        "amount": 50000,
        "currency": "NGN",
        "status": "SUCCESS",
        "payment_method": "card",
    },
    "data": {
        "reference": "ref_xyz789",
    },
}

PAYLOAD_FLAT_STYLE: Dict[str, Any] = {
    """Flat style: all fields at top level"""
    "request_ref": "req_2002_def",
    "provider_ref": "prov_ghi_888",
    "txRef": "tx_flat_9999",
    "status": "COMPLETED",
    "amount": 25000.50,
    "currency": "USD",
    "timestamp": "2024-01-15T11:00:00Z",
    "message": "Payment successful",
}

PAYLOAD_META_WRAPPED: Dict[str, Any] = {
    """Meta-wrapped style: nested under data/meta containers"""
    "event": "payment.complete",
    "webhook_timestamp": "2024-01-15T11:30:00Z",
    "data": {
        "id": "evt_metadata",
        "reference": "req_3003_ghi",
        "transactionRef": "tx_meta_5555",
        "transaction_status": "PAID",
        "total": "75000",
        "currency_code": "NGN",
        "customer": {
            "id": "cust_123",
            "email": "user@example.com",
        },
    },
    "meta": {
        "request_ref": "req_3003_ghi_meta",
        "provider_ref": "prov_meta_777",
    },
}

PAYLOAD_PROVIDER_WRAPPED: Dict[str, Any] = {
    """Provider-wrapped style: fields inside event/response wrapper"""
    "event": {
        "type": "charge.success",
        "timestamp": 1705324200,
        "data": {
            "id": "evt_flutterwave",
            "txRef": "tx_fw_6666",
            "flutterwaveRef": "FLW1234567890",
            "amount": 10000,
            "currency": "NGN",
            "status": "successful",
            "reference": "req_4004_jkl",
        },
    },
    "body": {
        "amount": 10000,
        "value": 10000,
        "payable_amount": 10000,
    },
}

PAYLOAD_MINIMAL: Dict[str, Any] = {
    """Minimal payload: only request_ref and status"""
    "request_ref": "req_minimal",
    "status": "PENDING",
}

PAYLOAD_EMPTY: Dict[str, Any] = {
    """Empty payload: no relevant fields"""
    "webhook_id": "wh_empty",
    "timestamp": "2024-01-15T12:00:00Z",
}


# ===== Tests =====

class ExtractRequestRefTestCase(TestCase):
    """Tests for extract_request_ref()"""

    def test_top_level_snake_case(self):
        """Should find request_ref at top level"""
        assert extract_request_ref(PAYLOAD_FLAT_STYLE) == "req_2002_def"

    def test_top_level_camel_case(self):
        """Should find requestRef at top level"""
        payload = {"requestRef": "abc_123"}
        assert extract_request_ref(payload) == "abc_123"

    def test_nested_in_transaction(self):
        """Should find nested in transaction object"""
        payload = {"transaction": {"request_ref": "txn_req_001"}}
        assert extract_request_ref(payload) == "txn_req_001"

    def test_nested_in_data(self):
        """Should find nested in data object"""
        payload = {"data": {"reference": "data_ref_002"}}
        assert extract_request_ref(payload) == "data_ref_002"

    def test_nested_in_meta(self):
        """Should find nested in meta object"""
        payload = {"meta": {"requestRef": "meta_req_003"}}
        assert extract_request_ref(payload) == "meta_req_003"

    def test_onepipe_style(self):
        """Should extract from OnePipe-style payload"""
        assert extract_request_ref(PAYLOAD_ONEPIPE_STYLE) == "req_1001_abc"

    def test_meta_wrapped_style(self):
        """Should extract from meta-wrapped style (prefer top-level data.reference)"""
        result = extract_request_ref(PAYLOAD_META_WRAPPED)
        assert result in ("req_3003_ghi", "req_3003_ghi_meta")  # First match from candidate_paths

    def test_not_found(self):
        """Should return None if not found"""
        assert extract_request_ref(PAYLOAD_EMPTY) is None

    def test_empty_payload(self):
        """Should handle empty dict gracefully"""
        assert extract_request_ref({}) is None

    def test_numeric_request_ref(self):
        """Should convert numeric request_ref to string"""
        payload = {"request_ref": 12345}
        assert extract_request_ref(payload) == "12345"

    def test_non_dict_input(self):
        """Should return None for non-dict input"""
        assert extract_request_ref(None) is None  # type: ignore
        assert extract_request_ref("not_a_dict") is None  # type: ignore

    def test_deeply_nested_request_ref(self):
        """Should find request_ref in deeply nested payload"""
        payload = {"payload": {"request_ref": "deep_ref_999"}}
        assert extract_request_ref(payload) == "deep_ref_999"


class ExtractProviderRefTestCase(TestCase):
    """Tests for extract_provider_ref()"""

    def test_top_level_provider_ref(self):
        """Should find provider_ref at top level"""
        payload = {"provider_ref": "prov_12345"}
        assert extract_provider_ref(payload) == "prov_12345"

    def test_top_level_transaction_ref(self):
        """Should find transaction_ref at top level"""
        payload = {"transaction_ref": "txn_ref_001"}
        assert extract_provider_ref(payload) == "txn_ref_001"

    def test_top_level_txref(self):
        """Should find txRef at top level"""
        payload = {"txRef": "tx_flat_9999"}
        assert extract_provider_ref(payload) == "tx_flat_9999"

    def test_flat_style(self):
        """Should extract from flat-style payload"""
        assert extract_provider_ref(PAYLOAD_FLAT_STYLE) == "prov_ghi_888"

    def test_nested_in_transaction(self):
        """Should find nested in transaction object"""
        payload = {"transaction": {"reference": "txn_ref_555"}}
        assert extract_provider_ref(payload) == "txn_ref_555"

    def test_nested_in_data(self):
        """Should find nested in data object"""
        payload = {"data": {"transaction_ref": "data_txn_666"}}
        assert extract_provider_ref(payload) == "data_txn_666"

    def test_provider_specific_flutterwave_ref(self):
        """Should find flutterwaveRef"""
        payload = {"flutterwaveRef": "FLW9876543210"}
        assert extract_provider_ref(payload) == "FLW9876543210"

    def test_provider_wrapped_style(self):
        """Should extract from provider-wrapped payload"""
        result = extract_provider_ref(PAYLOAD_PROVIDER_WRAPPED)
        assert result in ("tx_fw_6666", "FLW1234567890", "req_4004_jkl")  # Multiple matches in nested structure

    def test_onepipe_style(self):
        """Should extract from OnePipe payload"""
        result = extract_provider_ref(PAYLOAD_ONEPIPE_STYLE)
        assert result == "txn_server_2024_001"

    def test_not_found(self):
        """Should return None if not found"""
        assert extract_provider_ref(PAYLOAD_MINIMAL) is None

    def test_empty_payload(self):
        """Should handle empty dict gracefully"""
        assert extract_provider_ref({}) is None


class ExtractStatusTestCase(TestCase):
    """Tests for extract_status()"""

    def test_top_level_status(self):
        """Should find status at top level"""
        payload = {"status": "SUCCESS"}
        assert extract_status(payload) == "SUCCESS"

    def test_top_level_transaction_status(self):
        """Should find transaction_status at top level"""
        payload = {"transaction_status": "COMPLETED"}
        assert extract_status(payload) == "COMPLETED"

    def test_nested_in_transaction(self):
        """Should find nested in transaction object"""
        payload = {"transaction": {"status": "PAID"}}
        assert extract_status(payload) == "PAID"

    def test_nested_in_data(self):
        """Should find nested in data object"""
        payload = {"data": {"status": "PENDING"}}
        assert extract_status(payload) == "PENDING"

    def test_nested_in_event(self):
        """Should find nested in event object"""
        payload = {"event": {"status": "FAILED"}}
        assert extract_status(payload) == "FAILED"

    def test_meta_wrapped_style(self):
        """Should extract from meta-wrapped payload"""
        result = extract_status(PAYLOAD_META_WRAPPED)
        assert result == "PAID"

    def test_provider_wrapped_style(self):
        """Should extract from provider-wrapped payload"""
        result = extract_status(PAYLOAD_PROVIDER_WRAPPED)
        assert result == "successful"

    def test_flat_style(self):
        """Should extract from flat-style payload"""
        assert extract_status(PAYLOAD_FLAT_STYLE) == "COMPLETED"

    def test_case_sensitive(self):
        """Should return status as-is (case-sensitive)"""
        payload = {"status": "pending"}  # lowercase
        assert extract_status(payload) == "pending"

    def test_status_with_whitespace(self):
        """Should strip whitespace from status"""
        payload = {"status": "  SUCCESS  "}
        assert extract_status(payload) == "SUCCESS"

    def test_minimal_payload(self):
        """Should extract from minimal payload"""
        assert extract_status(PAYLOAD_MINIMAL) == "PENDING"

    def test_not_found(self):
        """Should return None if not found"""
        assert extract_status(PAYLOAD_EMPTY) is None


class ExtractAmountTestCase(TestCase):
    """Tests for extract_amount()"""

    def test_top_level_amount_int(self):
        """Should find amount as integer at top level"""
        payload = {"amount": 50000}
        assert extract_amount(payload) == 50000

    def test_top_level_amount_float(self):
        """Should find amount as float at top level"""
        payload = {"amount": 25000.50}
        assert extract_amount(payload) == 25000.50

    def test_top_level_amount_string(self):
        """Should parse amount from string"""
        payload = {"amount": "75000"}
        assert extract_amount(payload) == 75000.0

    def test_top_level_value(self):
        """Should find value field"""
        payload = {"value": 30000}
        assert extract_amount(payload) == 30000

    def test_top_level_total(self):
        """Should find total field"""
        payload = {"total": 100000.25}
        assert extract_amount(payload) == 100000.25

    def test_nested_in_transaction(self):
        """Should find nested in transaction object"""
        payload = {"transaction": {"amount": 45000}}
        assert extract_amount(payload) == 45000

    def test_nested_in_data(self):
        """Should find nested in data object"""
        payload = {"data": {"amount": 60000}}
        assert extract_amount(payload) == 60000

    def test_nested_in_body(self):
        """Should find nested in body object"""
        payload = {"body": {"payable_amount": 80000}}
        assert extract_amount(payload) == 80000

    def test_flat_style(self):
        """Should extract from flat-style payload"""
        assert extract_amount(PAYLOAD_FLAT_STYLE) == 25000.50

    def test_onepipe_style(self):
        """Should extract from OnePipe payload"""
        assert extract_amount(PAYLOAD_ONEPIPE_STYLE) == 50000

    def test_meta_wrapped_style(self):
        """Should extract from meta-wrapped payload (string amount)"""
        result = extract_amount(PAYLOAD_META_WRAPPED)
        assert result == 75000.0  # Parsed from "75000" string

    def test_provider_wrapped_style(self):
        """Should extract from provider-wrapped payload"""
        result = extract_amount(PAYLOAD_PROVIDER_WRAPPED)
        assert result == 10000  # First match

    def test_amount_as_decimal(self):
        """Should handle Decimal amounts"""
        payload = {"amount": Decimal("99999.99")}
        assert extract_amount(payload) == 99999.99

    def test_invalid_amount_string(self):
        """Should return None for non-numeric string"""
        payload = {"amount": "not_a_number"}
        assert extract_amount(payload) is None

    def test_zero_amount(self):
        """Should accept zero amount"""
        payload = {"amount": 0}
        assert extract_amount(payload) == 0

    def test_negative_amount(self):
        """Should accept negative amounts (refunds)"""
        payload = {"amount": -5000}
        assert extract_amount(payload) == -5000

    def test_not_found(self):
        """Should return None if amount not found"""
        assert extract_amount(PAYLOAD_MINIMAL) is None

    def test_empty_payload(self):
        """Should return None for empty dict"""
        assert extract_amount({}) is None


class ExtractCurrencyTestCase(TestCase):
    """Tests for extract_currency()"""

    def test_top_level_currency(self):
        """Should find currency at top level"""
        payload = {"currency": "NGN"}
        assert extract_currency(payload) == "NGN"

    def test_top_level_currency_code(self):
        """Should find currency_code at top level"""
        payload = {"currency_code": "USD"}
        assert extract_currency(payload) == "USD"

    def test_top_level_camel_case(self):
        """Should find currencyCode (camelCase)"""
        payload = {"currencyCode": "GBP"}
        assert extract_currency(payload) == "GBP"

    def test_nested_in_transaction(self):
        """Should find nested in transaction object"""
        payload = {"transaction": {"currency": "EUR"}}
        assert extract_currency(payload) == "EUR"

    def test_nested_in_data(self):
        """Should find nested in data object"""
        payload = {"data": {"currency": "JPY"}}
        assert extract_currency(payload) == "JPY"

    def test_nested_in_meta(self):
        """Should find nested in meta object"""
        payload = {"meta": {"currency": "AUD"}}
        assert extract_currency(payload) == "AUD"

    def test_flat_style(self):
        """Should extract from flat-style payload"""
        assert extract_currency(PAYLOAD_FLAT_STYLE) == "USD"

    def test_onepipe_style(self):
        """Should extract from OnePipe payload"""
        assert extract_currency(PAYLOAD_ONEPIPE_STYLE) == "NGN"

    def test_meta_wrapped_style(self):
        """Should extract from meta-wrapped payload"""
        assert extract_currency(PAYLOAD_META_WRAPPED) == "NGN"

    def test_provider_wrapped_style(self):
        """Should extract from provider-wrapped payload"""
        assert extract_currency(PAYLOAD_PROVIDER_WRAPPED) == "NGN"

    def test_lowercase_currency(self):
        """Should accept lowercase currency codes"""
        payload = {"currency": "ngn"}
        assert extract_currency(payload) == "ngn"

    def test_currency_whitespace(self):
        """Should strip whitespace from currency"""
        payload = {"currency": "  NGN  "}
        assert extract_currency(payload) == "NGN"

    def test_currency_numeric(self):
        """Should handle numeric currency codes (though rare)"""
        payload = {"currency": 566}  # ISO 4217 numeric for NGN
        assert extract_currency(payload) == "566"

    def test_not_found(self):
        """Should return None if currency not found"""
        assert extract_currency(PAYLOAD_MINIMAL) is None

    def test_empty_payload(self):
        """Should return None for empty dict"""
        assert extract_currency({}) is None


class ExtractorIntegrationTestCase(TestCase):
    """Integration tests: verify all extractors work together on realistic payloads"""

    def test_all_extractors_onepipe_style(self):
        """All extractors should work correctly on OnePipe-style payload"""
        assert extract_request_ref(PAYLOAD_ONEPIPE_STYLE) == "req_1001_abc"
        assert extract_provider_ref(PAYLOAD_ONEPIPE_STYLE) == "txn_server_2024_001"
        assert extract_status(PAYLOAD_ONEPIPE_STYLE) == "SUCCESS"
        assert extract_amount(PAYLOAD_ONEPIPE_STYLE) == 50000
        assert extract_currency(PAYLOAD_ONEPIPE_STYLE) == "NGN"

    def test_all_extractors_flat_style(self):
        """All extractors should work correctly on flat-style payload"""
        assert extract_request_ref(PAYLOAD_FLAT_STYLE) == "req_2002_def"
        assert extract_provider_ref(PAYLOAD_FLAT_STYLE) == "prov_ghi_888"
        assert extract_status(PAYLOAD_FLAT_STYLE) == "COMPLETED"
        assert extract_amount(PAYLOAD_FLAT_STYLE) == 25000.50
        assert extract_currency(PAYLOAD_FLAT_STYLE) == "USD"

    def test_all_extractors_meta_wrapped(self):
        """All extractors should work correctly on meta-wrapped payload"""
        assert extract_request_ref(PAYLOAD_META_WRAPPED) is not None
        assert extract_provider_ref(PAYLOAD_META_WRAPPED) is not None
        assert extract_status(PAYLOAD_META_WRAPPED) == "PAID"
        assert extract_amount(PAYLOAD_META_WRAPPED) == 75000.0
        assert extract_currency(PAYLOAD_META_WRAPPED) == "NGN"

    def test_all_extractors_provider_wrapped(self):
        """All extractors should work correctly on provider-wrapped payload"""
        assert extract_request_ref(PAYLOAD_PROVIDER_WRAPPED) is not None
        assert extract_provider_ref(PAYLOAD_PROVIDER_WRAPPED) is not None
        assert extract_status(PAYLOAD_PROVIDER_WRAPPED) == "successful"
        assert extract_amount(PAYLOAD_PROVIDER_WRAPPED) == 10000
        assert extract_currency(PAYLOAD_PROVIDER_WRAPPED) == "NGN"

    def test_minimal_payload_graceful_degradation(self):
        """Extractors should degrade gracefully on minimal payload"""
        assert extract_request_ref(PAYLOAD_MINIMAL) == "req_minimal"
        assert extract_provider_ref(PAYLOAD_MINIMAL) is None
        assert extract_status(PAYLOAD_MINIMAL) == "PENDING"
        assert extract_amount(PAYLOAD_MINIMAL) is None
        assert extract_currency(PAYLOAD_MINIMAL) is None

    def test_empty_payload_graceful_degradation(self):
        """All extractors should return None on empty payload"""
        assert extract_request_ref(PAYLOAD_EMPTY) is None
        assert extract_provider_ref(PAYLOAD_EMPTY) is None
        assert extract_status(PAYLOAD_EMPTY) is None
        assert extract_amount(PAYLOAD_EMPTY) is None
        assert extract_currency(PAYLOAD_EMPTY) is None
