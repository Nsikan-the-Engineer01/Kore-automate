"""
Unit tests for PayWithAccount payload builders.

Tests verify:
- Correct structure for each transaction type
- Default and overridden values for mock_mode and request_type
- Meta dict handling
- Currency and narrative support
"""

from django.test import TestCase, override_settings
from core_apps.integrations.paywithaccount.payloads import (
    build_invoice_payload,
    build_disburse_payload,
    build_subscription_payload,
    build_instalment_payload,
)


class BuildInvoicePayloadTest(TestCase):
    """Tests for build_invoice_payload()"""
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'inspect',
        'request_type': 'invoice',
        'request_type_invoice': 'invoice',
        'transact_path': '/v2/transact',
    })
    def test_invoice_payload_structure(self):
        """Test invoice payload has correct structure"""
        payload = build_invoice_payload(
            amount_total=50000.00,
            customer_email="john@example.com",
            customer_name="John Doe",
            meta={"order_id": "ORD-123"}
        )
        
        # Check top-level structure
        assert "transaction" in payload
        tx = payload["transaction"]
        
        # Check required fields
        assert tx["type"] == "debit"
        assert tx["amount"] == 50000.00
        assert tx["currency"] == "NGN"  # default
        assert tx["request_type"] == "invoice"
        assert tx["mock_mode"] == "inspect"
        
        # Check customer details
        assert tx["customer"]["email"] == "john@example.com"
        assert tx["customer"]["name"] == "John Doe"
        
        # Check meta
        assert tx["meta"] == {"order_id": "ORD-123"}
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'false',
        'request_type': 'invoice',
        'request_type_invoice': 'custom_invoice',
        'transact_path': '/v2/transact',
    })
    def test_invoice_with_overrides(self):
        """Test invoice payload with mock_mode and request_type overrides"""
        payload = build_invoice_payload(
            amount_total=100000.00,
            customer_email="jane@example.com",
            customer_name="Jane Doe",
            meta={"order_id": "ORD-456"},
            currency="USD",
            narrative="Invoice for services",
            mock_mode="true",
            request_type="override_invoice"
        )
        
        tx = payload["transaction"]
        assert tx["mock_mode"] == "true"  # override param takes precedence
        assert tx["request_type"] == "override_invoice"  # explicit param overrides settings
        assert tx["currency"] == "USD"
        assert tx["narrative"] == "Invoice for services"


class BuildDisbursePayloadTest(TestCase):
    """Tests for build_disburse_payload()"""
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'inspect',
        'request_type': 'invoice',
        'request_type_disburse': 'disburse',
        'transact_path': '/v2/transact',
    })
    def test_disburse_payload_structure(self):
        """Test disburse payload has correct structure"""
        payload = build_disburse_payload(
            amount=50000.00,
            beneficiary_account="0123456789",
            beneficiary_bank_code="058",
            meta={"payout_id": "PO-001"}
        )
        
        assert "transaction" in payload
        tx = payload["transaction"]
        
        # Check required fields
        assert tx["type"] == "credit"  # disburse is credit
        assert tx["amount"] == 50000.00
        assert tx["currency"] == "NGN"  # default
        assert tx["request_type"] == "disburse"
        
        # Check beneficiary details
        assert tx["beneficiary"]["account_number"] == "0123456789"
        assert tx["beneficiary"]["bank_code"] == "058"
        
        # Check meta
        assert tx["meta"] == {"payout_id": "PO-001"}
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'false',
        'request_type': 'invoice',
        'request_type_disburse': 'disburse',
        'transact_path': '/v2/transact',
    })
    def test_disburse_with_settings_override(self):
        """Test disburse payload respects PWA_REQUEST_TYPE_DISBURSE env var via settings"""
        payload = build_disburse_payload(
            amount=25000.00,
            beneficiary_account="9876543210",
            beneficiary_bank_code="044",
            meta={},
            narrative="Refund"
        )
        
        tx = payload["transaction"]
        # request_type should come from settings, not the generic PWA_REQUEST_TYPE
        assert tx["request_type"] == "disburse"
        assert tx["narrative"] == "Refund"


class BuildSubscriptionPayloadTest(TestCase):
    """Tests for build_subscription_payload()"""
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'inspect',
        'request_type': 'invoice',
        'request_type_subscription': 'subscription',
        'transact_path': '/v2/transact',
    })
    def test_subscription_payload_structure(self):
        """Test subscription payload has correct structure"""
        schedule = {'frequency': 'monthly', 'interval': 1, 'duration': 12}
        payload = build_subscription_payload(
            amount_total=120000.00,
            schedule=schedule,
            meta={"subscription_id": "SUB-001"}
        )
        
        assert "transaction" in payload
        tx = payload["transaction"]
        
        # Check required fields
        assert tx["type"] == "debit"
        assert tx["amount"] == 120000.00
        assert tx["currency"] == "NGN"  # default
        assert tx["request_type"] == "subscription"
        
        # Check schedule
        assert tx["schedule"] == schedule
        assert tx["meta"] == {"subscription_id": "SUB-001"}


class BuildInstalmentPayloadTest(TestCase):
    """Tests for build_instalment_payload()"""
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'inspect',
        'request_type': 'invoice',
        'request_type_instalment': 'instalment',
        'transact_path': '/v2/transact',
    })
    def test_instalment_payload_structure(self):
        """Test instalment payload has correct structure"""
        schedule = {'frequency': 'monthly', 'num_installments': 3, 'interval': 1}
        payload = build_instalment_payload(
            amount_total=300000.00,
            down_payment=100000.00,
            schedule=schedule,
            meta={"instalment_id": "INST-001"}
        )
        
        assert "transaction" in payload
        tx = payload["transaction"]
        
        # Check required fields
        assert tx["type"] == "debit"
        assert tx["amount"] == 300000.00
        assert tx["currency"] == "NGN"  # default
        assert tx["request_type"] == "instalment"
        assert tx["down_payment"] == 100000.00
        
        # Check schedule
        assert tx["schedule"] == schedule
        assert tx["meta"] == {"instalment_id": "INST-001"}


class PayloadBuilderDefaultsTest(TestCase):
    """Tests for default behavior across all builders"""
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'true',  # Settings default
        'request_type': 'invoice',
        'request_type_invoice': 'invoice',
        'request_type_disburse': 'custom_disburse',
        'request_type_subscription': 'custom_subscription',
        'request_type_instalment': 'custom_instalment',
        'transact_path': '/v2/transact',
    })
    def test_all_builders_use_settings_defaults(self):
        """Test that all builders respect settings defaults for mock_mode and request_type"""
        
        # Invoice uses settings default
        inv = build_invoice_payload(50000.00, "a@b.com", "A B", {})
        assert inv["transaction"]["mock_mode"] == "true"
        assert inv["transaction"]["request_type"] == "invoice"
        
        # Disburse uses custom settings request_type
        dis = build_disburse_payload(50000.00, "123", "058", {})
        assert dis["transaction"]["mock_mode"] == "true"
        assert dis["transaction"]["request_type"] == "custom_disburse"
        
        # Subscription uses custom settings request_type
        sub = build_subscription_payload(120000.00, {}, {})
        assert sub["transaction"]["mock_mode"] == "true"
        assert sub["transaction"]["request_type"] == "custom_subscription"
        
        # Instalment uses custom settings request_type
        inst = build_instalment_payload(300000.00, 100000.00, {}, {})
        assert inst["transaction"]["mock_mode"] == "true"
        assert inst["transaction"]["request_type"] == "custom_instalment"
    
    @override_settings(PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'inspect',
        'request_type': 'invoice',
        'request_type_invoice': 'invoice',
        'request_type_disburse': 'disburse',
        'transact_path': '/v2/transact',
    })
    def test_empty_meta_defaults_to_empty_dict(self):
        """Test that None meta defaults to empty dict"""
        payload = build_invoice_payload(50000.00, "a@b.com", "A B", None)
        assert payload["transaction"]["meta"] == {}
