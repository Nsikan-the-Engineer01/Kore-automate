"""
Idempotency helpers for collections service (status update rules).

This module is imported by collections.services.update_collection_from_webhook
to enforce idempotent status updates.
"""


class IdempotentCollectionUpdate:
    """
    Ensure collection status updates are idempotent.
    
    Rules:
    - If collection is SUCCESS: only update if new status is SUCCESS (idempotent)
    - If collection is FAILED: only update if new status is FAILED (idempotent)
    - If collection is PENDING/INITIATED: update to any new status
    - Never go backwards (e.g., SUCCESS -> PENDING is blocked)
    """
    
    # Status hierarchy (cannot move backwards)
    STATUS_HIERARCHY = {
        'INITIATED': 1,
        'PENDING': 2,
        'PROCESSING': 3,
        'SUCCESS': 4,
        'FAILED': 4,  # FAILED is terminal, same level as SUCCESS
    }
    
    # Terminal statuses (no further updates unless idempotent)
    TERMINAL_STATUSES = {'SUCCESS', 'FAILED'}
    
    @staticmethod
    def should_update(
        current_status: str,
        new_status: str,
        allow_override: bool = False
    ) -> bool:
        """
        Check if collection status should be updated (idempotency).
        
        Args:
            current_status: Current collection status
            new_status: New status from webhook
            allow_override: If True, allow override of terminal statuses
            
        Returns:
            True if update should proceed, False if update should be skipped
            
        Logic:
        - If current is terminal (SUCCESS/FAILED): only allow if new == current (idempotent)
        - Unless allow_override=True, then always allow
        - Otherwise, allow forward progression
        """
        if current_status == new_status:
            # Idempotent: same status
            return True
        
        if allow_override:
            # Forced update allowed
            return True
        
        if current_status in IdempotentCollectionUpdate.TERMINAL_STATUSES:
            # Terminal status: no changes unless idempotent
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Skipping status update: collection already in terminal status "
                f"{current_status}, new status {new_status}"
            )
            return False
        
        # Allow forward progression
        current_level = IdempotentCollectionUpdate.STATUS_HIERARCHY.get(current_status, 0)
        new_level = IdempotentCollectionUpdate.STATUS_HIERARCHY.get(new_status, 0)
        
        if new_level < current_level:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Skipping status update: cannot go backwards from {current_status} "
                f"to {new_status}"
            )
            return False
        
        return True
    
    @staticmethod
    def get_update_fields(
        current_status: str,
        new_status: str,
        allow_override: bool = False
    ):
        """
        Get update fields for status change (or None if no update).
        
        Args:
            current_status: Current collection status
            new_status: New status from webhook
            allow_override: If True, allow override of terminal statuses
            
        Returns:
            Dict with fields to update, or None if no update should occur
        """
        if not IdempotentCollectionUpdate.should_update(current_status, new_status, allow_override):
            return None
        
        return {
            'status': new_status,
        }
