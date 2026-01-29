"""
PayWithAccount Service - Thin wrapper around PayWithAccountClient.

Provides convenience methods for transaction handling and metadata building.
Core business logic remains in the Collections service.
"""

import logging
from typing import Dict, Any, Optional

from .client import PayWithAccountClient, PayWithAccountError

logger = logging.getLogger(__name__)


class PayWithAccountService:
    """
    Thin service wrapper for PayWithAccount API operations.
    
    Wraps PayWithAccountClient and provides:
    - Simplified transact() interface returning dict
    - Optional metadata builder for KORE fields
    
    Example:
        service = PayWithAccountService()
        response = service.transact(payload)
        # {'request_ref': 'abc123...', 'data': {...}}
    """
    
    def __init__(self):
        """Initialize service with PayWithAccountClient."""
        self.client = PayWithAccountClient()
    
    def transact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute transaction and return response with request_ref.
        
        Wraps client.transact() to return a simple dict format
        instead of TransactionResult dataclass.
        
        Args:
            payload: Transaction payload dict with 'transaction' key
            
        Returns:
            Dict with keys:
            - 'request_ref': Generated UUID hex string for tracking
            - 'data': API response JSON
            
        Raises:
            PayWithAccountError: On API or network errors
            
        Example:
            payload = {
                'transaction': {
                    'amount': 10000.00,
                    'currency': 'NGN'
                }
            }
            response = service.transact(payload)
            request_ref = response['request_ref']
            status = response['data']['status']
        """
        result = self.client.transact(payload)
        
        return {
            'request_ref': result.request_ref,
            'data': result.data
        }
    
    def build_meta_defaults(
        self,
        user_id: Optional[str] = None,
        goal_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build optional metadata defaults for KORE system fields.
        
        Creates a dict with KORE-specific metadata that can be
        merged into the main payload. Fields are only included if provided.
        
        Args:
            user_id: Optional KORE user ID (becomes 'kore_user_id' in meta)
            goal_id: Optional KORE goal ID (becomes 'kore_goal_id' in meta)
            
        Returns:
            Dict with KORE metadata fields (empty if no args provided)
            
        Example:
            # Build meta with both fields
            meta = service.build_meta_defaults(
                user_id='usr-123',
                goal_id='goal-456'
            )
            # {'kore_user_id': 'usr-123', 'kore_goal_id': 'goal-456'}
            
            # Build meta with just user_id
            meta = service.build_meta_defaults(user_id='usr-789')
            # {'kore_user_id': 'usr-789'}
            
            # Build empty meta
            meta = service.build_meta_defaults()
            # {}
        """
        meta = {}
        
        if user_id is not None:
            meta['kore_user_id'] = str(user_id)
        
        if goal_id is not None:
            meta['kore_goal_id'] = str(goal_id)
        
        return meta
