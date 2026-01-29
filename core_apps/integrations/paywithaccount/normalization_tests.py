"""
Unit tests for PayWithAccount provider status normalization.

Tests verify:
- Correct mapping of common provider statuses
- Case-insensitive matching
- Validation flag behavior for OTP/validation statuses
- Default behavior for unknown statuses
- Configurable status mapping via settings override
"""

from django.test import TestCase, override_settings
from core_apps.integrations.paywithaccount.normalization import (
    normalize_provider_status,
    get_available_status_map,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_PENDING,
)


class NormalizeProviderStatusSuccessTest(TestCase):
    """Tests for success status normalization"""
    
    def test_success_status(self):
        """Test 'SUCCESS' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("SUCCESS")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_successful_status(self):
        """Test 'SUCCESSFUL' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("SUCCESSFUL")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_completed_status(self):
        """Test 'COMPLETED' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("COMPLETED")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_approved_status(self):
        """Test 'APPROVED' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("APPROVED")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_confirmed_status(self):
        """Test 'CONFIRMED' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("CONFIRMED")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_settled_status(self):
        """Test 'SETTLED' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("SETTLED")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_paid_status(self):
        """Test 'PAID' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("PAID")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_processed_status(self):
        """Test 'PROCESSED' maps to SUCCESS"""
        status, needs_validation = normalize_provider_status("PROCESSED")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_success_case_insensitive(self):
        """Test case-insensitive matching for success"""
        for variant in ["success", "SUCCESS", "Success", "sUcCeSs"]:
            status, needs_validation = normalize_provider_status(variant)
            assert status == STATUS_SUCCESS
            assert needs_validation is False


class NormalizeProviderStatusFailedTest(TestCase):
    """Tests for failed status normalization"""
    
    def test_failed_status(self):
        """Test 'FAILED' maps to FAILED"""
        status, needs_validation = normalize_provider_status("FAILED")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_error_status(self):
        """Test 'ERROR' maps to FAILED"""
        status, needs_validation = normalize_provider_status("ERROR")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_declined_status(self):
        """Test 'DECLINED' maps to FAILED"""
        status, needs_validation = normalize_provider_status("DECLINED")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_rejected_status(self):
        """Test 'REJECTED' maps to FAILED"""
        status, needs_validation = normalize_provider_status("REJECTED")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_cancelled_status(self):
        """Test 'CANCELLED' maps to FAILED"""
        status, needs_validation = normalize_provider_status("CANCELLED")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_timeout_status(self):
        """Test 'TIMEOUT' maps to FAILED"""
        status, needs_validation = normalize_provider_status("TIMEOUT")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_expired_status(self):
        """Test 'EXPIRED' maps to FAILED"""
        status, needs_validation = normalize_provider_status("EXPIRED")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_aborted_status(self):
        """Test 'ABORTED' maps to FAILED"""
        status, needs_validation = normalize_provider_status("ABORTED")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_invalid_status(self):
        """Test 'INVALID' maps to FAILED"""
        status, needs_validation = normalize_provider_status("INVALID")
        assert status == STATUS_FAILED
        assert needs_validation is False
    
    def test_failed_case_insensitive(self):
        """Test case-insensitive matching for failed"""
        for variant in ["failed", "FAILED", "Failed", "fAiLeD"]:
            status, needs_validation = normalize_provider_status(variant)
            assert status == STATUS_FAILED
            assert needs_validation is False


class NormalizeProviderStatusPendingTest(TestCase):
    """Tests for pending status normalization"""
    
    def test_pending_status(self):
        """Test 'PENDING' maps to PENDING"""
        status, needs_validation = normalize_provider_status("PENDING")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_processing_status(self):
        """Test 'PROCESSING' maps to PENDING"""
        status, needs_validation = normalize_provider_status("PROCESSING")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_initiated_status(self):
        """Test 'INITIATED' maps to PENDING"""
        status, needs_validation = normalize_provider_status("INITIATED")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_in_progress_status(self):
        """Test 'IN_PROGRESS' maps to PENDING"""
        status, needs_validation = normalize_provider_status("IN_PROGRESS")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_awaiting_status(self):
        """Test 'AWAITING' maps to PENDING"""
        status, needs_validation = normalize_provider_status("AWAITING")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_queued_status(self):
        """Test 'QUEUED' maps to PENDING"""
        status, needs_validation = normalize_provider_status("QUEUED")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_pending_case_insensitive(self):
        """Test case-insensitive matching for pending"""
        for variant in ["pending", "PENDING", "Pending", "pEnDiNg"]:
            status, needs_validation = normalize_provider_status(variant)
            assert status == STATUS_PENDING
            assert needs_validation is False


class NormalizeProviderStatusValidationTest(TestCase):
    """Tests for OTP/validation status normalization"""
    
    def test_waiting_for_otp_no_underscore(self):
        """Test 'WaitingForOTP' flags validation required"""
        status, needs_validation = normalize_provider_status("WaitingForOTP")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_waiting_for_otp_with_underscore(self):
        """Test 'WAITING_FOR_OTP' flags validation required"""
        status, needs_validation = normalize_provider_status("WAITING_FOR_OTP")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_otp_pending(self):
        """Test 'OTP_PENDING' flags validation required"""
        status, needs_validation = normalize_provider_status("OTP_PENDING")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_pending_validation_no_underscore(self):
        """Test 'PendingValidation' flags validation required"""
        status, needs_validation = normalize_provider_status("PendingValidation")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_pending_validation_with_underscore(self):
        """Test 'PENDING_VALIDATION' flags validation required"""
        status, needs_validation = normalize_provider_status("PENDING_VALIDATION")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_validation_required(self):
        """Test 'VALIDATION_REQUIRED' flags validation required"""
        status, needs_validation = normalize_provider_status("VALIDATION_REQUIRED")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_awaiting_validation(self):
        """Test 'AWAITING_VALIDATION' flags validation required"""
        status, needs_validation = normalize_provider_status("AWAITING_VALIDATION")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_requires_otp(self):
        """Test 'REQUIRES_OTP' flags validation required"""
        status, needs_validation = normalize_provider_status("REQUIRES_OTP")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_otp_required(self):
        """Test 'OTP_REQUIRED' flags validation required"""
        status, needs_validation = normalize_provider_status("OTP_REQUIRED")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    def test_validation_case_insensitive(self):
        """Test case-insensitive matching for validation statuses"""
        for variant in ["waitingforotp", "WAITINGFOROTP", "WaitingForOtp"]:
            status, needs_validation = normalize_provider_status(variant)
            assert status == STATUS_PENDING
            assert needs_validation is True


class NormalizeProviderStatusEdgeCasesTest(TestCase):
    """Tests for edge cases and null handling"""
    
    def test_none_status(self):
        """Test None status defaults to PENDING, no validation"""
        status, needs_validation = normalize_provider_status(None)
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_empty_string_status(self):
        """Test empty string defaults to PENDING, no validation"""
        status, needs_validation = normalize_provider_status("")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_whitespace_string_status(self):
        """Test whitespace string defaults to PENDING, no validation"""
        status, needs_validation = normalize_provider_status("   ")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_unknown_status(self):
        """Test unknown status defaults to PENDING, no validation"""
        status, needs_validation = normalize_provider_status("UNKNOWN_RANDOM_STATUS")
        assert status == STATUS_PENDING
        assert needs_validation is False
    
    def test_status_with_leading_trailing_spaces(self):
        """Test status with leading/trailing spaces is normalized"""
        status, needs_validation = normalize_provider_status("  SUCCESS  ")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
    
    def test_non_string_input(self):
        """Test non-string input (e.g., int, dict) defaults to PENDING"""
        status, needs_validation = normalize_provider_status(123)
        assert status == STATUS_PENDING
        assert needs_validation is False


class NormalizeProviderStatusConfigurableTest(TestCase):
    """Tests for settings-based status mapping override"""
    
    @override_settings(
        PAYWITHACCOUNT_STATUS_MAP={
            "CUSTOM_SUCCESS": ("SUCCESS", False),
            "CUSTOM_FAILED": ("FAILED", False),
            "CUSTOM_PENDING": ("PENDING", False),
            "CUSTOM_VALIDATION": ("PENDING", True),
        }
    )
    def test_custom_status_mapping(self):
        """Test custom status mapping from settings"""
        # Custom success
        status, needs_validation = normalize_provider_status("CUSTOM_SUCCESS")
        assert status == STATUS_SUCCESS
        assert needs_validation is False
        
        # Custom failed
        status, needs_validation = normalize_provider_status("CUSTOM_FAILED")
        assert status == STATUS_FAILED
        assert needs_validation is False
        
        # Custom pending
        status, needs_validation = normalize_provider_status("CUSTOM_PENDING")
        assert status == STATUS_PENDING
        assert needs_validation is False
        
        # Custom validation
        status, needs_validation = normalize_provider_status("CUSTOM_VALIDATION")
        assert status == STATUS_PENDING
        assert needs_validation is True
    
    @override_settings(
        PAYWITHACCOUNT_STATUS_MAP={
            "CUSTOM_SUCCESS": ("SUCCESS", False),
            "CUSTOM_FAILED": ("FAILED", False),
            "CUSTOM_PENDING": ("PENDING", False),
            "CUSTOM_VALIDATION": ("PENDING", True),
        }
    )
    def test_unknown_status_with_custom_map(self):
        """Test unknown status still defaults to PENDING with custom map"""
        status, needs_validation = normalize_provider_status("NOT_IN_CUSTOM_MAP")
        assert status == STATUS_PENDING
        assert needs_validation is False


class GetAvailableStatusMapTest(TestCase):
    """Tests for get_available_status_map() function"""
    
    def test_get_default_status_map(self):
        """Test retrieving default status map"""
        status_map = get_available_status_map()
        
        # Verify map contains expected entries
        assert "SUCCESS" in status_map
        assert "FAILED" in status_map
        assert "PENDING" in status_map
        assert "WAITINGFOROTP" in status_map
        
        # Verify mapping values
        assert status_map["SUCCESS"] == (STATUS_SUCCESS, False)
        assert status_map["WAITINGFOROTP"] == (STATUS_PENDING, True)
    
    @override_settings(
        PAYWITHACCOUNT_STATUS_MAP={
            "CUSTOM_ONLY": ("PENDING", False),
        }
    )
    def test_get_custom_status_map(self):
        """Test retrieving custom status map from settings"""
        status_map = get_available_status_map()
        
        # Custom map should be used
        assert "CUSTOM_ONLY" in status_map
        assert status_map["CUSTOM_ONLY"] == (STATUS_PENDING, False)
        
        # Default entries should not be in custom map
        assert "SUCCESS" not in status_map
