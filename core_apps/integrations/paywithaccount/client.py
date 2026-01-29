import uuid
import hashlib
import logging
from typing import Dict, Any, Tuple
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PayWithAccountError(Exception):
    """Exception raised for PayWithAccount API errors."""
    
    def __init__(self, exception: Exception = None, status_code: int = 0, response_text: str = "", request_ref: str = None):
        """
        Initialize PayWithAccountError.
        
        Args:
            exception: Original exception (can be requests.RequestException)
            status_code: HTTP status code
            response_text: Response body text
            request_ref: Request reference for tracking
        """
        self.exception = exception
        self.status_code = status_code
        self.response_text = response_text
        self.request_ref = request_ref
        
        if exception:
            message = f"PayWithAccount error: {str(exception)}"
        else:
            message = f"PayWithAccount API error (status {status_code}): {response_text}"
        
        super().__init__(message)


def compute_signature(request_ref: str, client_secret: str) -> str:
    """
    Compute MD5 signature for PayWithAccount requests.
    
    Format: MD5(request_ref;client_secret) with semicolon separator
    
    Args:
        request_ref: UUID reference for the request
        client_secret: Client secret from configuration
        
    Returns:
        MD5 hexadecimal hash
        
    Example:
        >>> compute_signature("abc123def456", "secret123")
        'e1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6'
    """
    data = f"{request_ref};{client_secret}"
    return hashlib.md5(data.encode()).hexdigest()


@dataclass
class TransactionResult:
    """Result of a PayWithAccount transaction."""
    request_ref: str  # Generated UUID for tracking
    data: Dict[str, Any]  # Response JSON from API


class PayWithAccountClient:
    """
    Client for OnePipe PayWithAccount API.
    
    Manages authentication, signature computation, and API communication.
    Uses settings.PAYWITHACCOUNT for configuration (base_url, api_key, etc).
    
    Example:
        client = PayWithAccountClient()
        result = client.transact({
            'transaction': {
                'amount': 10000.00,
                'currency': 'NGN'
            }
        })
        print(result.request_ref)  # UUID hex string
        print(result.data['status'])  # API response
    """
    
    def __init__(self):
        """Initialize client with settings from django.conf."""
        self.config = settings.PAYWITHACCOUNT
        self.base_url = self.config['base_url']
        self.transact_path = self.config['transact_path']
        # Optional new paths for query and validate
        self.query_path = self.config.get('query_path', '/transact/query')
        self.validate_path = self.config.get('validate_path', '/transact/validate')
        self.api_key = self.config['api_key']
        self.client_secret = self.config['client_secret']
        self.mock_mode = self.config['mock_mode']
        self.timeout = self.config['timeout_seconds']
        
        # Log initialization (redacted)
        logger.debug(
            f"PayWithAccountClient initialized: "
            f"base_url={self.base_url}, timeout={self.timeout}s"
        )
        
        if not self.api_key or not self.client_secret:
            logger.warning(
                "PayWithAccount credentials not fully configured. "
                "Ensure PWA_API_KEY and PWA_CLIENT_SECRET are set in environment."
            )
    
    def build_headers(self, request_ref: str) -> Dict[str, str]:
        """
        Build request headers with authorization and signature.
        
        Args:
            request_ref: UUID reference for the request
            
        Returns:
            Dictionary of headers with Authorization, Signature, Content-Type
            
        Example:
            headers = client.build_headers("abc123def456")
            # {
            #     'Authorization': 'Bearer <api_key>',
            #     'Signature': '<md5_hash>',
            #     'Content-Type': 'application/json'
            # }
        """
        signature = compute_signature(request_ref, self.client_secret)
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Signature": signature,
            "Content-Type": "application/json",
        }
    
    def _redact_sensitive(self, text: str) -> str:
        """
        Redact sensitive information from log strings.
        
        Redacts api_key and client_secret to prevent accidental logging.
        
        Args:
            text: Text that may contain secrets
            
        Returns:
            Text with secrets replaced with ***REDACTED***
        """
        if not text:
            return text
        redacted = text
        if self.api_key and len(self.api_key) > 0:
            redacted = redacted.replace(self.api_key, "***REDACTED_API_KEY***")
        if self.client_secret and len(self.client_secret) > 0:
            redacted = redacted.replace(self.client_secret, "***REDACTED_SECRET***")
        return redacted
    
    def transact(
        self,
        payload: Dict[str, Any],
        request_ref: str = None
    ) -> TransactionResult:
        """
        Execute a transaction request against PayWithAccount API.
        
        Generates request_ref if not provided, injects mock_mode into payload,
        computes signature, and posts to {base_url}{transact_path}.
        
        Args:
            payload: Transaction payload as dict. Should include 'transaction' key.
            request_ref: Optional UUID hex string. If not provided, generated via uuid.uuid4().hex
            
        Returns:
            TransactionResult with request_ref and API response data
            
        Raises:
            PayWithAccountError: On non-2xx status or request exception
            
        Example:
            payload = {
                'transaction': {
                    'amount': 10000.00,
                    'currency': 'NGN',
                    'type': 'debit'
                }
            }
            result = client.transact(payload)
            print(result.request_ref)  # 'abc123def456...'
            print(result.data['status'])  # 'success'
        """
        # Generate request_ref if not provided
        if not request_ref:
            request_ref = uuid.uuid4().hex
        
        # Ensure transaction key exists
        if "transaction" not in payload:
            payload["transaction"] = {}
        
        # Inject mock_mode if not already in payload
        if "mock_mode" not in payload["transaction"]:
            payload["transaction"]["mock_mode"] = self.mock_mode
        
        # Build headers with signature
        headers = self.build_headers(request_ref)
        
        # Construct full URL
        url = f"{self.base_url}{self.transact_path}"
        
        # Log request (redacted)
        logger.debug(
            f"PayWithAccount transact: POST {url} request_ref={request_ref}"
        )
        
        try:
            # Make request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Check for non-2xx status
            if response.status_code < 200 or response.status_code >= 300:
                error_text = response.text
                logger.error(
                    f"PayWithAccount API error: status={response.status_code} "
                    f"request_ref={request_ref} "
                    f"response={self._redact_sensitive(error_text)}"
                )
                raise PayWithAccountError(
                    status_code=response.status_code,
                    response_text=error_text,
                    request_ref=request_ref
                )
            
            # Parse and return response
            response_json = response.json()
            logger.debug(
                f"PayWithAccount transact success: request_ref={request_ref}"
            )
            
            return TransactionResult(
                request_ref=request_ref,
                data=response_json
            )
        
        except requests.RequestException as e:
            logger.error(
                f"PayWithAccount network error: request_ref={request_ref} "
                f"error={type(e).__name__}: {str(e)}"
            )
            raise PayWithAccountError(
                exception=e,
                request_ref=request_ref
            )

    def _extract_request_ref_from_payload(self, payload: Dict[str, Any]) -> str:
        """
        Helper to find an existing request_ref in the payload without modifying it.
        Looks for common keys at top-level and inside 'transaction'.
        """
        if not payload:
            return None
        # Top-level keys
        for key in ("request_ref", "requestRef", "requestReference"):
            if key in payload and payload[key]:
                return payload[key]
        # Inside transaction
        tx = payload.get("transaction")
        if isinstance(tx, dict):
            for key in ("request_ref", "requestRef", "requestReference"):
                if key in tx and tx[key]:
                    return tx[key]
        return None

    def _post_and_handle(self, url: str, headers: Dict[str, str], payload: Dict[str, Any], request_ref_for_error: str) -> TransactionResult:
        """
        Post JSON payload to url and handle response / errors consistently.
        Returns TransactionResult or raises PayWithAccountError on non-2xx or network errors.
        """
        logger.debug(f"PayWithAccount POST {url} request_ref={request_ref_for_error}")
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            if response.status_code < 200 or response.status_code >= 300:
                error_text = response.text
                logger.error(
                    f"PayWithAccount API error: status={response.status_code} "
                    f"request_ref={request_ref_for_error} "
                    f"response={self._redact_sensitive(error_text)}"
                )
                raise PayWithAccountError(
                    status_code=response.status_code,
                    response_text=error_text,
                    request_ref=request_ref_for_error
                )
            response_json = response.json()
            logger.debug(f"PayWithAccount POST success: request_ref={request_ref_for_error}")
            return TransactionResult(request_ref=request_ref_for_error, data=response_json)
        except requests.RequestException as e:
            logger.error(
                f"PayWithAccount network error: request_ref={request_ref_for_error} "
                f"error={type(e).__name__}: {str(e)}"
            )
            raise PayWithAccountError(exception=e, request_ref=request_ref_for_error)

    def query(self, payload: Dict[str, Any], request_ref: str = None, header_request_ref: str = None) -> TransactionResult:
        """
        Execute a query against PayWithAccount (POST {base_url}{query_path}).

        - Does NOT overwrite an existing request_ref in `payload`.
        - If `request_ref` param is provided and no request_ref exists in payload, it will be included in the payload.
        - The signature header is computed using `header_request_ref` if provided, otherwise a new request_ref is generated for the header.
        - Returns TransactionResult(request_ref=<header_ref>, data=<response_json>)
        """
        # Determine if payload already contains a body request_ref
        body_ref = self._extract_request_ref_from_payload(payload)
        # If caller provided a request_ref and payload has none, include it in payload (do not overwrite existing)
        if not body_ref and request_ref:
            # Prefer top-level insertion
            payload.setdefault("request_ref", request_ref)
            body_ref = request_ref
        # Determine header request_ref to compute signature
        header_ref = header_request_ref or uuid.uuid4().hex
        headers = self.build_headers(header_ref)
        url = f"{self.base_url}{self.query_path}"
        return self._post_and_handle(url, headers, payload, header_ref)

    def validate(self, payload: Dict[str, Any], request_ref: str = None, header_request_ref: str = None) -> TransactionResult:
        """
        Execute a validate call against PayWithAccount (POST {base_url}{validate_path}).

        Behavior mirrors `query` regarding request_ref handling and header signature.
        Returns TransactionResult(request_ref=<header_ref>, data=<response_json>)
        """
        body_ref = self._extract_request_ref_from_payload(payload)
        if not body_ref and request_ref:
            payload.setdefault("request_ref", request_ref)
            body_ref = request_ref
        header_ref = header_request_ref or uuid.uuid4().hex
        headers = self.build_headers(header_ref)
        url = f"{self.base_url}{self.validate_path}"
        return self._post_and_handle(url, headers, payload, header_ref)
