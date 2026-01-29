"""
PayWithAccount (OnePipe) API client.

This module provides a client for interacting with the PayWithAccount API.
All requests use the base URL configured via PWA_BASE_URL environment variable
(default: https://api.dev.onepipe.io) and the /v2/transact endpoint.
"""
import hashlib
import uuid
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from loguru import logger

from .encryption import encrypt_secure_field


class PayWithAccountClient:
    """
    Client for PayWithAccount (OnePipe) API.

    Base URL is configurable via PWA_BASE_URL env var (defaults to
    https://api.dev.onepipe.io). All requests are made to /v2/transact endpoint.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the PayWithAccount client.

        Args:
            api_key: API key for authentication. If not provided, reads from
                     settings.PWA_API_KEY.
            client_secret: Client secret for signature generation. If not provided,
                          reads from settings.PWA_CLIENT_SECRET.
            base_url: Base URL for API requests. If not provided, reads from
                     settings.PWA_BASE_URL (defaults to https://api.dev.onepipe.io).
        """
        self.api_key = api_key or getattr(settings, "PWA_API_KEY", "")
        self.client_secret = client_secret or getattr(settings, "PWA_CLIENT_SECRET", "")
        self.base_url = base_url or getattr(
            settings, "PWA_BASE_URL", "https://api.dev.onepipe.io"
        )

        # Ensure base_url doesn't end with a slash
        self.base_url = self.base_url.rstrip("/")

        # The endpoint path is always /v2/transact
        self.endpoint_path = "/v2/transact"
        self.full_url = f"{self.base_url}{self.endpoint_path}"

    def _generate_request_ref(self) -> str:
        """Generate a unique request reference."""
        return str(uuid.uuid4())

    def _generate_signature(self, request_ref: str) -> str:
        """
        Generate MD5 signature for request authentication.

        Signature is computed as: MD5(request_ref;client_secret)
        """
        signature_string = f"{request_ref};{self.client_secret}"
        return hashlib.md5(signature_string.encode("utf-8")).hexdigest()

    def _build_headers(self, request_ref: str) -> Dict[str, str]:
        """
        Build request headers including Authorization and Signature.

        Args:
            request_ref: Unique request reference for this API call.

        Returns:
            Dictionary of headers to include in the request.
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Signature": self._generate_signature(request_ref),
        }

    def _build_payload(
        self,
        request_type: str,
        transaction: Dict[str, Any],
        auth_type: Optional[str] = None,
        secure_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build the standard PayWithAccount request payload structure.

        Args:
            request_type: Type of request (e.g., "Get Accounts Max", "send invoice", "collect").
            transaction: Transaction object containing mock_mode, transaction_ref, amount, customer, etc.
            auth_type: Auth type (e.g., "bank.account" or None).
            secure_value: Encrypted secure value if auth_type is provided.

        Returns:
            Complete request payload dictionary.
        """
        request_ref = self._generate_request_ref()

        auth = {
            "type": auth_type,
            "secure": secure_value,
            "auth_provider": "PaywithAccount",
        }

        payload = {
            "request_ref": request_ref,
            "request_type": request_type,
            "auth": auth,
            "transaction": transaction,
        }

        return payload

    def transact(
        self,
        request_type: str,
        transaction: Dict[str, Any],
        auth_type: Optional[str] = None,
        secure_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make a transaction request to the PayWithAccount API.

        Args:
            request_type: Type of request (e.g., "Get Accounts Max", "send invoice", "collect").
            transaction: Transaction object containing mock_mode, transaction_ref, amount, customer, etc.
            auth_type: Auth type (e.g., "bank.account" or None).
            secure_value: Encrypted secure value if auth_type is provided. If None and auth_type
                         is "bank.account", this should be encrypted account details.

        Returns:
            Response data from the API.

        Raises:
            requests.RequestException: If the API request fails.
        """
        payload = self._build_payload(request_type, transaction, auth_type, secure_value)
        request_ref = payload["request_ref"]
        headers = self._build_headers(request_ref)

        logger.info(
            f"PayWithAccount API request: {request_type} to {self.full_url}",
            extra={"request_ref": request_ref},
        )

        try:
            response = requests.post(
                self.full_url,
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(
                f"PayWithAccount API request failed: {e}",
                extra={"request_ref": request_ref, "url": self.full_url},
            )
            raise
