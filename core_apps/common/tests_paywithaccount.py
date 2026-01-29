"""
Tests for PayWithAccount client.
"""
from unittest.mock import Mock, patch

from django.test import TestCase
from django.test.utils import override_settings

from .paywithaccount_client import PayWithAccountClient


class PayWithAccountClientTests(TestCase):
    """Test cases for PayWithAccountClient."""

    def setUp(self):
        """Set up test client with mock credentials."""
        self.client = PayWithAccountClient(
            api_key="test_api_key",
            client_secret="test_secret",
            base_url="https://api.dev.onepipe.io",
        )

    def test_client_initializes_with_default_base_url(self):
        """Test that client uses default base URL when not provided."""
        client = PayWithAccountClient(api_key="key", client_secret="secret")
        self.assertEqual(client.base_url, "https://api.dev.onepipe.io")
        self.assertEqual(client.endpoint_path, "/v2/transact")
        self.assertEqual(client.full_url, "https://api.dev.onepipe.io/v2/transact")

    def test_client_initializes_with_custom_base_url(self):
        """Test that client uses custom base URL when provided."""
        custom_url = "https://api.custom.onepipe.io"
        client = PayWithAccountClient(
            api_key="key", client_secret="secret", base_url=custom_url
        )
        self.assertEqual(client.base_url, custom_url)
        self.assertEqual(client.full_url, f"{custom_url}/v2/transact")

    def test_client_strips_trailing_slash_from_base_url(self):
        """Test that trailing slashes are removed from base URL."""
        client = PayWithAccountClient(
            api_key="key",
            client_secret="secret",
            base_url="https://api.dev.onepipe.io/",
        )
        self.assertEqual(client.base_url, "https://api.dev.onepipe.io")
        self.assertEqual(client.full_url, "https://api.dev.onepipe.io/v2/transact")

    def test_endpoint_path_is_v2_transact(self):
        """Test that endpoint path is always /v2/transact."""
        self.assertEqual(self.client.endpoint_path, "/v2/transact")

    def test_full_url_combines_base_url_and_endpoint(self):
        """Test that full_url correctly combines base_url and endpoint_path."""
        expected_url = "https://api.dev.onepipe.io/v2/transact"
        self.assertEqual(self.client.full_url, expected_url)

    @patch("core_apps.common.paywithaccount_client.requests.post")
    def test_transact_makes_request_to_correct_url(self, mock_post):
        """Test that transact method makes request to the correct full URL."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "Successful"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        transaction = {
            "mock_mode": "Inspect",
            "transaction_ref": "test-ref-123",
            "transaction_desc": "Test transaction",
            "amount": 0,
            "customer": {
                "customer_ref": "2348022221412",
                "firstname": "Test",
                "surname": "User",
                "email": "test@example.com",
                "mobile_no": "2348022221412",
            },
            "meta": {},
            "details": {},
        }

        self.client.transact("Get Accounts Max", transaction)

        # Assert that the request was made to the correct URL
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.dev.onepipe.io/v2/transact")

    @override_settings(PWA_BASE_URL="https://api.prod.onepipe.io")
    def test_client_uses_settings_base_url_when_not_provided(self):
        """Test that client reads PWA_BASE_URL from settings when not provided."""
        client = PayWithAccountClient(api_key="key", client_secret="secret")
        self.assertEqual(client.base_url, "https://api.prod.onepipe.io")
        self.assertEqual(client.full_url, "https://api.prod.onepipe.io/v2/transact")

    def test_generate_request_ref_creates_unique_values(self):
        """Test that request references are unique."""
        ref1 = self.client._generate_request_ref()
        ref2 = self.client._generate_request_ref()
        self.assertNotEqual(ref1, ref2)
        self.assertIsInstance(ref1, str)
        self.assertIsInstance(ref2, str)

    def test_generate_signature_creates_md5_hash(self):
        """Test that signature generation creates MD5 hash."""
        request_ref = "test-ref-123"
        signature = self.client._generate_signature(request_ref)
        expected_string = f"{request_ref};{self.client.client_secret}"
        import hashlib

        expected_hash = hashlib.md5(expected_string.encode("utf-8")).hexdigest()
        self.assertEqual(signature, expected_hash)

    def test_build_headers_includes_required_fields(self):
        """Test that headers include Authorization, Signature, and Content-Type."""
        request_ref = "test-ref-123"
        headers = self.client._build_headers(request_ref)

        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))
        self.assertIn("Signature", headers)
        self.assertEqual(len(headers["Signature"]), 32)  # MD5 hash length
