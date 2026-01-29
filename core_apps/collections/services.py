import json
import logging
from decimal import Decimal
from os import getenv
from typing import Optional, Dict, Any

from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from core_apps.goals.models import Goal
from .models import Collection
from core_apps.transactions.models import Transaction
from core_apps.integrations.paywithaccount.client import (
    PayWithAccountClient,
    PayWithAccountError
)
from core_apps.integrations.paywithaccount.normalization import normalize_provider_status

User = get_user_model()
logger = logging.getLogger(__name__)


class CollectionError(Exception):
    """Exception raised for collection-related errors."""
    pass


class CollectionsService:
    """Service for managing collection operations and PayWithAccount integration."""
    
    def __init__(self):
        self.pwa_client = PayWithAccountClient()
        self.request_type = getenv("PWA_REQUEST_TYPE", "invoice")
        
        # Fee configuration - percent takes precedence if both set
        self.fee_percent = self._parse_float(getenv("KORE_FEE_PERCENT"))
        self.fee_flat = self._parse_float(getenv("KORE_FEE_FLAT"))
    
    @staticmethod
    def _parse_float(value: Optional[str]) -> Optional[Decimal]:
        """Parse string to Decimal, return None if invalid or missing."""
        if not value:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse fee value: {value}")
            return None
    
    def compute_fee(self, amount_allocation: Decimal) -> Decimal:
        """
        Compute kore fee based on configuration.
        
        Priority: fee_percent > fee_flat > 0
        
        Args:
            amount_allocation: Amount being allocated to goal
            
        Returns:
            Fee amount as Decimal
        """
        if self.fee_percent is not None:
            return (amount_allocation * self.fee_percent / Decimal('100')).quantize(
                Decimal('0.01')
            )
        elif self.fee_flat is not None:
            return self.fee_flat
        else:
            return Decimal('0.00')
    
    def build_pwa_payload(
        self,
        user: User,
        goal: Optional[Goal],
        amount_allocation: Decimal,
        kore_fee: Decimal,
        amount_total: Decimal,
        currency: str,
        narrative: str = "",
        request_ref: str = None
    ) -> Dict[str, Any]:
        """
        Build PayWithAccount /v2/transact payload.
        
        Args:
            user: User making the collection
            goal: Goal being funded (optional)
            amount_allocation: Amount allocated to goal
            kore_fee: Fee charged by Kore
            amount_total: Total amount to be collected
            currency: Currency code (NGN, etc)
            narrative: Optional narrative/description
            request_ref: Optional request reference (will be set by client if not provided)
            
        Returns:
            Dictionary payload for PWA API
        """
        payload = {
            "request_type": self.request_type,
            "transaction": {
                "type": "debit",
                "amount": str(amount_total),
                "currency": currency,
                "narration": narrative or f"Kore Collection - {goal.name if goal else 'General'}",
                "mock_mode": getenv("PWA_MOCK_MODE", "false").lower() == "true"
            },
            "meta": {
                "user_id": str(user.id),
                "narrative": narrative,
                "split": {
                    "amount_allocation": str(amount_allocation),
                    "kore_fee": str(kore_fee),
                    "amount_total": str(amount_total)
                }
            }
        }
        
        if goal:
            payload["meta"]["goal_id"] = str(goal.id)
            payload["meta"]["goal_name"] = goal.name
        
        if request_ref:
            payload["request_ref"] = request_ref
        
        return payload
    
    @db_transaction.atomic
    def create_collection(
        self,
        user: User,
        goal: Optional[Goal],
        amount_allocation: Decimal,
        currency: str = "NGN",
        narrative: str = "",
        idempotency_key: Optional[str] = None
    ) -> Collection:
        """
        Create a collection and initiate PayWithAccount transaction.
        
        Atomically:
        1. Compute fees
        2. Build PWA payload
        3. Call PayWithAccount API
        4. Persist Collection
        5. Create Transaction records
        
        Args:
            user: User making the collection
            goal: Goal to fund (optional)
            amount_allocation: Amount to allocate to goal
            currency: Currency code (default "NGN")
            narrative: Optional description
            idempotency_key: Optional key for idempotency (prevents duplicate collections)
            
        Returns:
            Collection instance (status=INITIATED)
            
        Raises:
            CollectionError: If validation or API call fails
            PayWithAccountError: If PWA API returns error
        """
        
        # Validate input
        if amount_allocation <= 0:
            raise CollectionError("amount_allocation must be greater than 0")
        
        if goal and goal.user_id != user.id:
            raise CollectionError("Goal does not belong to this user")
        
        # Check idempotency
        if idempotency_key:
            existing = Collection.objects.filter(
                user=user,
                metadata__idempotency_key=idempotency_key
            ).first()
            if existing:
                logger.info(
                    f"Idempotent request detected: returning existing collection {existing.id}"
                )
                return existing
        
        # Compute fee
        kore_fee = self.compute_fee(amount_allocation)
        amount_total = amount_allocation + kore_fee
        
        logger.info(
            f"Creating collection: user={user.id}, goal={goal.id if goal else 'None'}, "
            f"allocation={amount_allocation}, fee={kore_fee}, total={amount_total}"
        )
        
        # Build PWA payload
        payload = self.build_pwa_payload(
            user=user,
            goal=goal,
            amount_allocation=amount_allocation,
            kore_fee=kore_fee,
            amount_total=amount_total,
            currency=currency,
            narrative=narrative
        )
        
        try:
            # Call PayWithAccount API
            result = self.pwa_client.transact(payload)
            response_json = result.data
            request_ref = result.request_ref
            
            # Extract provider_ref from response if present
            provider_ref = response_json.get('reference') or response_json.get('transaction_ref')
            
            # Normalize provider status and detect validation requirement (defensive)
            provider_status = response_json.get('status') or response_json.get('transaction_status')
            normalized_status, needs_validation = normalize_provider_status(provider_status)
            
            logger.debug(
                f"Collection response: provider_status={provider_status}, "
                f"normalized={normalized_status}, needs_validation={needs_validation}"
            )
            
            # Determine collection status based on normalized status and validation requirement
            if needs_validation:
                # Validation (OTP, etc.) required; set to PENDING and store validation fields
                collection_status = "PENDING"
                logger.info(
                    f"Collection requires validation: user={user.id}, "
                    f"provider_status={provider_status}"
                )
            elif normalized_status == "SUCCESS":
                collection_status = "SUCCESS"
            elif normalized_status == "FAILED":
                collection_status = "FAILED"
            else:
                # Any other status (unlikely if normalization works correctly) defaults to PENDING
                collection_status = "PENDING"
            
            # Create Collection record
            collection_metadata = {
                "split": payload["meta"]["split"],
                "narrative": narrative,
                "normalized_status": normalized_status,
                "needs_validation": needs_validation
            }
            if idempotency_key:
                collection_metadata["idempotency_key"] = idempotency_key
            
            # Store validation fields in metadata if needed (defensive extraction)
            if needs_validation:
                validation_fields = {}
                # Common validation field names (best effort)
                for field in ['validation_ref', 'session_id', 'otp_reference', 'challenge_ref', 'auth_token']:
                    if field in response_json:
                        validation_fields[field] = response_json[field]
                if validation_fields:
                    collection_metadata['validation_fields'] = validation_fields
                    logger.debug(f"Stored validation fields: {list(validation_fields.keys())}")
            
            collection = Collection.objects.create(
                user=user,
                goal=goal,
                amount_allocation=amount_allocation,
                kore_fee=kore_fee,
                amount_total=amount_total,
                currency=currency,
                provider="paywithaccount",
                request_ref=request_ref,
                provider_ref=provider_ref,
                status=collection_status,
                narrative=narrative,
                raw_request=payload,
                raw_response=response_json,
                metadata=collection_metadata
            )
            
            logger.info(
                f"Collection created: {collection.id} (request_ref={request_ref}, "
                f"status={collection_status}, needs_validation={needs_validation})"
            )
            
            # Create Transaction records with appropriate status
            transaction_status = "PENDING" if collection_status in ["PENDING", "INITIATED"] else collection_status
            
            Transaction.objects.create(
                user=user,
                goal=goal,
                collection=collection,
                type="DEBIT",
                amount=amount_allocation,
                currency=currency,
                status=transaction_status,
                request_ref=request_ref,
                occurred_at=timezone.now(),
                metadata={"narrative": narrative}
            )
            
            if kore_fee > 0:
                Transaction.objects.create(
                    user=user,
                    goal=goal,
                    collection=collection,
                    type="FEE",
                    amount=kore_fee,
                    currency=currency,
                    status=transaction_status,
                    request_ref=request_ref,
                    occurred_at=timezone.now(),
                    metadata={"narrative": "Kore processing fee"}
                )
            
            logger.info(f"Transactions created for collection {collection.id}")
            
            return collection
        
        except PayWithAccountError as e:
            logger.error(
                f"PWA API error creating collection: status={e.status_code}, "
                f"ref={e.request_ref}"
            )
            raise CollectionError(
                f"Failed to initiate collection with PayWithAccount: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating collection: {str(e)}")
            raise CollectionError(f"Unexpected error creating collection: {str(e)}")
    
    @db_transaction.atomic
    def update_collection_from_webhook(
        self,
        request_ref: str,
        provider_ref: str,
        new_status: str,
        payload: Dict[str, Any],
        response_body: Optional[Dict[str, Any]] = None,
        allow_override: bool = False
    ) -> Collection:
        """
        Update collection and related transactions from webhook notification.
        
        Implements idempotency:
        - If collection already SUCCESS or FAILED, skips status update unless allow_override=True
        - Only updates transaction statuses if they're currently PENDING
        - Prevents accidental downgrades (e.g., SUCCESS -> PENDING)
        
        Translates webhook status to Collection.status and Transaction.status.
        
        Webhook status mapping (example):
        - "success" / "completed" -> "SUCCESS"
        - "failed" -> "FAILED"
        - "pending" / "processing" -> "INITIATED"
        
        Args:
            request_ref: Request reference from original API call
            provider_ref: Provider reference from webhook
            new_status: Status from webhook (e.g., "success", "failed")
            payload: Full webhook payload for audit
            response_body: Response data from provider (optional)
            allow_override: If True, allows overwriting terminal statuses (SUCCESS/FAILED)
            
        Returns:
            Updated Collection instance (or unchanged if idempotency prevented update)
            
        Raises:
            CollectionError: If collection not found or status update invalid
        """
        from .idempotency import IdempotentCollectionUpdate
        
        # Normalize status
        status_map = {
            "success": "SUCCESS",
            "completed": "SUCCESS",
            "failed": "FAILED",
            "pending": "INITIATED",
            "processing": "INITIATED",
            "initiated": "INITIATED",
        }
        
        normalized_status = status_map.get(new_status.lower(), new_status.upper())
        
        # Find collection
        try:
            collection = Collection.objects.get(request_ref=request_ref)
        except Collection.DoesNotExist:
            raise CollectionError(f"Collection not found for request_ref={request_ref}")
        
        # Check idempotency: should we update status?
        should_update = IdempotentCollectionUpdate.should_update(
            collection.status,
            normalized_status,
            allow_override=allow_override
        )
        
        logger.info(
            f"Updating collection {collection.id} from webhook: "
            f"new_status={normalized_status}, provider_ref={provider_ref}, "
            f"current_status={collection.status}, should_update={should_update}"
        )
        
        update_fields = ['provider_ref', 'metadata']
        
        # Update collection status only if idempotency allows
        if should_update:
            collection.status = normalized_status
            update_fields.insert(0, 'status')
        
        if provider_ref:
            collection.provider_ref = provider_ref
        
        if response_body:
            collection.raw_response = response_body
            update_fields.append('raw_response')
        
        # Store webhook payload in metadata
        if "webhook_payload" not in collection.metadata:
            collection.metadata["webhook_payload"] = payload
        
        collection.save(update_fields=update_fields)
        
        # Update related transactions (only if collection status was updated)
        if should_update:
            transaction_status = {
                "SUCCESS": "SUCCESS",
                "FAILED": "FAILED",
                "CANCELLED": "FAILED",
                "INITIATED": "PENDING"
            }.get(normalized_status, "PENDING")
            
            updated_count = Transaction.objects.filter(
                collection=collection,
                status="PENDING"  # Only update pending transactions
            ).update(status=transaction_status)
            
            logger.info(
                f"Updated {updated_count} transaction(s) for collection {collection.id} "
                f"to status={transaction_status}"
            )
        else:
            logger.info(
                f"Skipped transaction update for collection {collection.id} "
                f"(idempotency: collection already in terminal status)"
            )
        
        return collection    
    @db_transaction.atomic
    def validate_collection(
        self,
        collection: Collection,
        otp: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> Collection:
        """
        Submit validation (OTP, challenge response, etc.) for a collection.
        
        Calls PayWithAccountClient.validate() with collection context and user input.
        Updates collection and transactions based on response status.
        
        Args:
            collection: Collection to validate (must be PENDING with needs_validation=True)
            otp: OTP code from user (if required by provider)
            extra_fields: Additional provider-required fields (e.g., challenge_response)
            
        Returns:
            Updated Collection instance
            
        Raises:
            CollectionError: If validation fails or collection not in validatable state
            PayWithAccountError: If provider API returns error
        """
        # Defensive check
        if not collection:
            raise CollectionError("Collection not found")
        
        if collection.status != "PENDING":
            raise CollectionError(
                f"Collection status is {collection.status}, must be PENDING to validate"
            )
        
        if not collection.metadata or not collection.metadata.get('needs_validation'):
            raise CollectionError(
                "Collection does not require validation"
            )
        
        # Build validation payload with collection context
        payload = {
            "request_ref": collection.request_ref,
            "meta": {
                "collection_id": str(collection.id),
                "user_id": str(collection.user_id),
            }
        }
        
        # Add OTP if provided
        if otp:
            payload["otp"] = otp
        
        # Add any extra fields
        if extra_fields:
            payload.update(extra_fields)
        
        logger.info(
            f"Validating collection: {collection.id}, request_ref={collection.request_ref}"
        )
        
        try:
            # Call validate endpoint
            result = self.pwa_client.validate(
                payload,
                request_ref=collection.request_ref,
                header_request_ref=collection.request_ref
            )
            response_json = result.data
            
            # Extract and normalize provider status
            provider_status = response_json.get('status') or response_json.get('transaction_status')
            normalized_status, needs_validation = normalize_provider_status(provider_status)
            
            logger.debug(
                f"Validation response: provider_status={provider_status}, "
                f"normalized={normalized_status}, needs_validation={needs_validation}"
            )
            
            # Determine new collection status
            if normalized_status == "SUCCESS":
                new_status = "SUCCESS"
            elif normalized_status == "FAILED":
                new_status = "FAILED"
            elif needs_validation:
                # Still waiting for validation
                new_status = "PENDING"
            else:
                new_status = "PENDING"
            
            # Update collection
            collection.status = new_status
            collection.raw_response = response_json
            collection.metadata['normalized_status'] = normalized_status
            collection.metadata['needs_validation'] = needs_validation
            collection.metadata['validation_attempt_at'] = timezone.now().isoformat()
            
            # Update validation fields if new ones provided
            if needs_validation and 'validation_fields' not in collection.metadata:
                validation_fields = {}
                for field in ['validation_ref', 'session_id', 'otp_reference', 'challenge_ref', 'auth_token']:
                    if field in response_json:
                        validation_fields[field] = response_json[field]
                if validation_fields:
                    collection.metadata['validation_fields'] = validation_fields
            
            collection.save()
            
            # Update transactions to match new status
            transaction_status = "PENDING" if new_status == "PENDING" else new_status
            Transaction.objects.filter(
                collection=collection,
                status="PENDING"  # Only update pending transactions
            ).update(status=transaction_status)
            
            logger.info(
                f"Collection validation completed: {collection.id}, "
                f"new_status={new_status}, needs_validation={needs_validation}"
            )
            
            return collection
        
        except PayWithAccountError as e:
            logger.error(
                f"PWA validation error: collection={collection.id}, "
                f"status={e.status_code}, ref={e.request_ref}"
            )
            raise CollectionError(f"Validation failed with provider: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error validating collection {collection.id}: {str(e)}"
            )
            raise CollectionError(f"Unexpected error during validation: {str(e)}")
    
    @db_transaction.atomic
    def query_collection_status(self, collection: Collection) -> Collection:
        """
        Query current status of a collection from provider.
        
        Calls PayWithAccountClient.query() using collection references.
        Updates collection and transactions based on response status.
        
        Args:
            collection: Collection to query
            
        Returns:
            Updated Collection instance
            
        Raises:
            CollectionError: If query fails
            PayWithAccountError: If provider API returns error
        """
        # Defensive check
        if not collection:
            raise CollectionError("Collection not found")
        
        # Build query payload (best effort)
        # Try to use provider_ref; fall back to request_ref
        reference = collection.provider_ref or collection.request_ref
        
        if not reference:
            raise CollectionError(
                "Cannot query status: no provider_ref or request_ref available"
            )
        
        payload = {
            "reference": reference,
            "meta": {
                "collection_id": str(collection.id),
                "user_id": str(collection.user_id),
            }
        }
        
        logger.info(
            f"Querying collection status: {collection.id}, reference={reference}"
        )
        
        try:
            # Call query endpoint
            result = self.pwa_client.query(payload)
            response_json = result.data
            
            # Extract and normalize provider status
            provider_status = response_json.get('status') or response_json.get('transaction_status')
            normalized_status, needs_validation = normalize_provider_status(provider_status)
            
            logger.debug(
                f"Query response: provider_status={provider_status}, "
                f"normalized={normalized_status}, needs_validation={needs_validation}"
            )
            
            # Determine new status
            if normalized_status == "SUCCESS":
                new_status = "SUCCESS"
            elif normalized_status == "FAILED":
                new_status = "FAILED"
            elif needs_validation:
                new_status = "PENDING"
            else:
                new_status = "PENDING"
            
            # Update collection only if status changed
            if collection.status != new_status:
                collection.status = new_status
                collection.raw_response = response_json
                collection.metadata['normalized_status'] = normalized_status
                collection.metadata['needs_validation'] = needs_validation
                collection.metadata['queried_at'] = timezone.now().isoformat()
                collection.save()
                
                # Update transactions
                transaction_status = "PENDING" if new_status == "PENDING" else new_status
                Transaction.objects.filter(
                    collection=collection,
                    status="PENDING"  # Only update pending transactions
                ).update(status=transaction_status)
                
                logger.info(
                    f"Collection status updated: {collection.id}, "
                    f"old_status={collection.status}, new_status={new_status}"
                )
            else:
                logger.info(f"Collection status unchanged: {collection.id}, status={new_status}")
            
            return collection
        
        except PayWithAccountError as e:
            logger.error(
                f"PWA query error: collection={collection.id}, "
                f"status={e.status_code}, ref={e.request_ref}"
            )
            raise CollectionError(f"Query failed with provider: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error querying collection {collection.id}: {str(e)}"
            )
            raise CollectionError(f"Unexpected error during status query: {str(e)}")