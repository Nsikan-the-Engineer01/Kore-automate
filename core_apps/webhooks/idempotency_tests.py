"""
Tests for webhook idempotency and deduplication.

Tests cover:
1. Event ID extraction and deduplication
2. Processing lock functionality
3. Idempotent collection status updates
4. Race condition handling
"""
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.db import IntegrityError

from core_apps.webhooks.models import WebhookEvent
from core_apps.webhooks.idempotency import (
    IdempotencyChecker,
    ProcessingLock,
    IdempotentCollectionUpdate,
    has_redis,
    get_redis_client,
)
from core_apps.webhooks.utils import extract_event_id
from core_apps.collections.models import Collection
from core_apps.collections.idempotency import IdempotentCollectionUpdate as CollectionIdempotency


class ExtractEventIdTestCase(TestCase):
    """Tests for extract_event_id() function."""

    def test_top_level_event_id(self):
        """Should find event_id at top level."""
        payload = {'event_id': 'evt_123abc'}
        assert extract_event_id(payload) == 'evt_123abc'

    def test_top_level_eventId_camel(self):
        """Should find eventId (camelCase)."""
        payload = {'eventId': 'evt_456def'}
        assert extract_event_id(payload) == 'evt_456def'

    def test_top_level_event_field(self):
        """Should find event field (when it's a string ID)."""
        payload = {'event': 'evt_789ghi'}
        assert extract_event_id(payload) == 'evt_789ghi'

    def test_top_level_id(self):
        """Should find id at top level."""
        payload = {'id': 'evt_999zzz'}
        assert extract_event_id(payload) == 'evt_999zzz'

    def test_nested_in_event(self):
        """Should find nested in event.id."""
        payload = {'event': {'id': 'fw_evt_123'}}
        assert extract_event_id(payload) == 'fw_evt_123'

    def test_nested_in_data(self):
        """Should find nested in data.event_id."""
        payload = {'data': {'event_id': 'data_evt_456'}}
        assert extract_event_id(payload) == 'data_evt_456'

    def test_nested_in_meta(self):
        """Should find nested in meta.event_id."""
        payload = {'meta': {'event_id': 'meta_evt_789'}}
        assert extract_event_id(payload) == 'meta_evt_789'

    def test_provider_specific_flutterwave(self):
        """Should find flutterwave_event_id."""
        payload = {'flutterwave_event_id': 'fw_evt_xyz'}
        assert extract_event_id(payload) == 'fw_evt_xyz'

    def test_not_found(self):
        """Should return None if event_id not found."""
        payload = {'some_other_field': 'value'}
        assert extract_event_id(payload) is None

    def test_empty_payload(self):
        """Should return None for empty dict."""
        assert extract_event_id({}) is None


class IdempotentCollectionUpdateTestCase(TestCase):
    """Tests for IdempotentCollectionUpdate status rules."""

    def test_same_status_always_allowed(self):
        """Should always allow same status (idempotent)."""
        assert IdempotentCollectionUpdate.should_update('SUCCESS', 'SUCCESS') == True
        assert IdempotentCollectionUpdate.should_update('FAILED', 'FAILED') == True
        assert IdempotentCollectionUpdate.should_update('PENDING', 'PENDING') == True

    def test_terminal_to_terminal_same_allowed(self):
        """Should allow SUCCESS->SUCCESS and FAILED->FAILED."""
        assert IdempotentCollectionUpdate.should_update('SUCCESS', 'SUCCESS') == True
        assert IdempotentCollectionUpdate.should_update('FAILED', 'FAILED') == True

    def test_success_blocks_downgrade_to_pending(self):
        """Should block SUCCESS -> PENDING downgrade."""
        assert IdempotentCollectionUpdate.should_update('SUCCESS', 'PENDING') == False

    def test_success_blocks_downgrade_to_initiated(self):
        """Should block SUCCESS -> INITIATED downgrade."""
        assert IdempotentCollectionUpdate.should_update('SUCCESS', 'INITIATED') == False

    def test_failed_blocks_downgrade_to_pending(self):
        """Should block FAILED -> PENDING downgrade."""
        assert IdempotentCollectionUpdate.should_update('FAILED', 'PENDING') == False

    def test_forward_progression_initiated_to_success(self):
        """Should allow forward progression."""
        assert IdempotentCollectionUpdate.should_update('INITIATED', 'SUCCESS') == True

    def test_forward_progression_pending_to_success(self):
        """Should allow PENDING -> SUCCESS."""
        assert IdempotentCollectionUpdate.should_update('PENDING', 'SUCCESS') == True

    def test_forward_progression_initiated_to_failed(self):
        """Should allow INITIATED -> FAILED."""
        assert IdempotentCollectionUpdate.should_update('INITIATED', 'FAILED') == True

    def test_override_allows_terminal_change(self):
        """Should allow terminal status change with allow_override=True."""
        assert IdempotentCollectionUpdate.should_update(
            'SUCCESS', 'FAILED', allow_override=True
        ) == True

    def test_override_allows_downgrade(self):
        """Should allow downgrade with allow_override=True."""
        assert IdempotentCollectionUpdate.should_update(
            'SUCCESS', 'PENDING', allow_override=True
        ) == True

    def test_get_update_fields_when_allowed(self):
        """Should return update fields when update is allowed."""
        result = IdempotentCollectionUpdate.get_update_fields('INITIATED', 'SUCCESS')
        assert result == {'status': 'SUCCESS'}

    def test_get_update_fields_when_blocked(self):
        """Should return None when update is blocked."""
        result = IdempotentCollectionUpdate.get_update_fields('SUCCESS', 'PENDING')
        assert result is None

    def test_get_update_fields_with_override(self):
        """Should return update fields when override is enabled."""
        result = IdempotentCollectionUpdate.get_update_fields(
            'SUCCESS', 'FAILED', allow_override=True
        )
        assert result == {'status': 'FAILED'}


class ProcessingLockTestCase(TestCase):
    """Tests for ProcessingLock (without Redis)."""

    @override_settings(REDIS_URL=None)
    def test_lock_acquire_db_fallback(self):
        """Should acquire lock in DB fallback mode."""
        lock = ProcessingLock('test_key')
        assert lock.acquire() == True
        assert lock.acquired == True

    @override_settings(REDIS_URL=None)
    def test_lock_release_db_fallback(self):
        """Should release lock in DB fallback mode."""
        lock = ProcessingLock('test_key')
        lock.acquire()
        assert lock.release() == True
        assert lock.acquired == False

    @override_settings(REDIS_URL=None)
    def test_lock_context_manager(self):
        """Should work as context manager."""
        from core_apps.webhooks.idempotency import processing_lock
        
        with processing_lock('test_key'):
            # Inside lock context
            pass
        # Lock should be released

    @override_settings(REDIS_URL=None)
    def test_lock_without_acquire(self):
        """Should not release if never acquired."""
        lock = ProcessingLock('test_key')
        lock.acquired = False
        assert lock.release() == False


class IdempotencyCheckerTestCase(TestCase):
    """Tests for IdempotencyChecker (event caching)."""

    def test_checker_init(self):
        """Should initialize checker."""
        checker = IdempotencyChecker()
        assert checker.redis_client is None  # Unless Redis configured

    def test_get_cached_no_redis(self):
        """Should return None when Redis not available."""
        checker = IdempotencyChecker()
        checker.redis_client = None
        result = checker.get_cached_event_id('evt_123')
        assert result is None

    def test_cache_event_no_redis(self):
        """Should return False when Redis not available."""
        checker = IdempotencyChecker()
        checker.redis_client = None
        result = checker.cache_event_result('evt_123', {'status': 'SUCCESS'})
        assert result == False

    def test_empty_event_id_returns_none(self):
        """Should return None for empty event_id."""
        checker = IdempotencyChecker()
        assert checker.get_cached_event_id('') is None
        assert checker.get_cached_event_id(None) is None


class WebhookEventDeduplicationTestCase(TestCase):
    """Integration tests for webhook event deduplication."""

    def test_duplicate_event_id_rejected(self):
        """Should reject webhook with duplicate event_id."""
        # Create first event
        event1 = WebhookEvent.objects.create(
            provider='paywithaccount',
            event_id='evt_unique_123',
            request_ref='req_123',
            payload={'status': 'success'},
            status='RECEIVED'
        )

        # Try to create duplicate (should fail at DB level)
        with self.assertRaises(IntegrityError):
            WebhookEvent.objects.create(
                provider='paywithaccount',
                event_id='evt_unique_123',  # Duplicate
                request_ref='req_456',
                payload={'status': 'success'},
                status='RECEIVED'
            )

    def test_unique_event_ids_allowed(self):
        """Should allow different event_ids."""
        event1 = WebhookEvent.objects.create(
            provider='paywithaccount',
            event_id='evt_unique_123',
            request_ref='req_123',
            payload={'status': 'success'},
            status='RECEIVED'
        )

        event2 = WebhookEvent.objects.create(
            provider='paywithaccount',
            event_id='evt_unique_456',  # Different
            request_ref='req_456',
            payload={'status': 'success'},
            status='RECEIVED'
        )

        assert event1.id != event2.id
        assert event1.event_id != event2.event_id

    def test_null_event_ids_allowed(self):
        """Should allow multiple events with null event_id (old webhooks)."""
        event1 = WebhookEvent.objects.create(
            provider='paywithaccount',
            event_id=None,  # No event_id
            request_ref='req_123',
            payload={'status': 'success'},
            status='RECEIVED'
        )

        event2 = WebhookEvent.objects.create(
            provider='paywithaccount',
            event_id=None,  # Another null event_id
            request_ref='req_456',
            payload={'status': 'success'},
            status='RECEIVED'
        )

        assert event1.id != event2.id


class CollectionIdempotencyIntegrationTestCase(TestCase):
    """Integration tests for collection idempotent updates."""

    def setUp(self):
        """Set up test collection."""
        self.collection = Collection.objects.create(
            request_ref='req_test_123',
            status='INITIATED',
            goal_id='goal_dummy'
        )

    def test_success_webhook_updates_status(self):
        """Should update INITIATED collection to SUCCESS."""
        should_update = CollectionIdempotency.should_update(
            'INITIATED', 'SUCCESS'
        )
        assert should_update == True
        self.collection.status = 'SUCCESS'
        self.collection.save()
        self.collection.refresh_from_db()
        assert self.collection.status == 'SUCCESS'

    def test_duplicate_success_webhook_idempotent(self):
        """Second SUCCESS webhook shouldn't change SUCCESS collection."""
        self.collection.status = 'SUCCESS'
        self.collection.save()

        should_update = CollectionIdempotency.should_update('SUCCESS', 'SUCCESS')
        assert should_update == True  # Same status is idempotent

        # Verify no changes
        self.collection.refresh_from_db()
        assert self.collection.status == 'SUCCESS'

    def test_pending_webhook_after_success_blocked(self):
        """PENDING webhook should not change SUCCESS collection."""
        self.collection.status = 'SUCCESS'
        self.collection.save()

        should_update = CollectionIdempotency.should_update('SUCCESS', 'PENDING')
        assert should_update == False  # Blocked, would downgrade

        # Verify no changes
        self.collection.refresh_from_db()
        assert self.collection.status == 'SUCCESS'

    def test_failed_webhook_blocks_further_changes(self):
        """FAILED is terminal, no changes unless override."""
        self.collection.status = 'FAILED'
        self.collection.save()

        # Should block change to SUCCESS
        should_update = CollectionIdempotency.should_update(
            'FAILED', 'SUCCESS'
        )
        assert should_update == False

    def test_override_allows_failed_after_success(self):
        """With override, can change FAILED after SUCCESS."""
        should_update = CollectionIdempotency.should_update(
            'SUCCESS', 'FAILED', allow_override=True
        )
        assert should_update == True
