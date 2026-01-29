from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from core_apps.goals.models import Goal
from core_apps.transactions.models import Transaction
from datetime import datetime, timezone


class GoalViewSetTestCase(TestCase):
    """Test suite for Goal ViewSet endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Authenticate as test user
        self.client.force_authenticate(user=self.user)
        
        # Create test goals
        self.goal_active = Goal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('500000.00'),
            currency='NGN',
            status='ACTIVE',
            metadata={'priority': 'high'}
        )
        
        self.goal_paused = Goal.objects.create(
            user=self.user,
            name='Vacation Fund',
            target_amount=Decimal('200000.00'),
            currency='NGN',
            status='PAUSED',
            metadata={'category': 'travel'}
        )
        
        self.other_user_goal = Goal.objects.create(
            user=self.other_user,
            name='Other User Goal',
            target_amount=Decimal('100000.00'),
            currency='NGN',
            status='ACTIVE'
        )
    
    # ============ LIST GOALS TESTS ============
    
    def test_list_goals_authenticated(self):
        """Test listing goals for authenticated user."""
        response = self.client.get('/api/v1/goals/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_list_goals_unauthenticated(self):
        """Test that unauthenticated users cannot list goals."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/goals/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_goals_filtered_by_user(self):
        """Test that list returns only current user's goals."""
        response = self.client.get('/api/v1/goals/')
        
        self.assertEqual(len(response.data['results']), 2)
        goal_ids = [goal['id'] for goal in response.data['results']]
        
        # Should contain user's goals
        self.assertIn(str(self.goal_active.id), goal_ids)
        self.assertIn(str(self.goal_paused.id), goal_ids)
        # Should not contain other user's goal
        self.assertNotIn(str(self.other_user_goal.id), goal_ids)
    
    def test_list_goals_ordered_newest_first(self):
        """Test that goals are ordered by creation date (newest first)."""
        response = self.client.get('/api/v1/goals/')
        
        results = response.data['results']
        # Paused goal was created after active goal
        self.assertEqual(str(results[0]['id']), str(self.goal_paused.id))
        self.assertEqual(str(results[1]['id']), str(self.goal_active.id))
    
    # ============ CREATE GOAL TESTS ============
    
    def test_create_goal_with_all_fields(self):
        """Test creating a goal with all fields."""
        data = {
            'name': 'House Fund',
            'target_amount': '5000000.00',
            'currency': 'ngn',
            'metadata': {'priority': 'very high'}
        }
        response = self.client.post('/api/v1/goals/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'House Fund')
        self.assertEqual(response.data['target_amount'], '5000000.00')
        self.assertEqual(response.data['currency'], 'NGN')
        self.assertEqual(response.data['status'], 'ACTIVE')
        self.assertEqual(response.data['metadata'], {'priority': 'very high'})
    
    def test_create_goal_with_required_fields_only(self):
        """Test creating a goal with only required fields."""
        data = {
            'name': 'Minimal Goal',
            'target_amount': '10000.00'
        }
        response = self.client.post('/api/v1/goals/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Minimal Goal')
        self.assertEqual(response.data['currency'], 'NGN')  # Default
        self.assertEqual(response.data['status'], 'ACTIVE')
        self.assertEqual(response.data['metadata'], {})  # Default
    
    def test_create_goal_assigns_current_user(self):
        """Test that created goal is assigned to current user."""
        data = {
            'name': 'User Test Goal',
            'target_amount': '50000.00'
        }
        response = self.client.post('/api/v1/goals/', data)
        
        goal = Goal.objects.get(id=response.data['id'])
        self.assertEqual(goal.user, self.user)
    
    def test_create_goal_invalid_target_amount(self):
        """Test creating a goal with invalid target amount."""
        data = {
            'name': 'Invalid Goal',
            'target_amount': '0.00'
        }
        response = self.client.post('/api/v1/goals/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('target_amount', response.data)
    
    def test_create_goal_empty_name(self):
        """Test creating a goal with empty name."""
        data = {
            'name': '',
            'target_amount': '50000.00'
        }
        response = self.client.post('/api/v1/goals/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
    
    def test_create_goal_missing_required_field(self):
        """Test creating a goal with missing required field."""
        data = {
            'name': 'Incomplete Goal'
            # Missing target_amount
        }
        response = self.client.post('/api/v1/goals/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('target_amount', response.data)
    
    def test_create_goal_unauthenticated(self):
        """Test that unauthenticated users cannot create goals."""
        self.client.force_authenticate(user=None)
        data = {
            'name': 'Test Goal',
            'target_amount': '50000.00'
        }
        response = self.client.post('/api/v1/goals/', data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # ============ RETRIEVE GOAL TESTS ============
    
    def test_retrieve_own_goal(self):
        """Test retrieving a goal that belongs to the user."""
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.goal_active.id))
        self.assertEqual(response.data['name'], 'Emergency Fund')
        self.assertEqual(response.data['status'], 'ACTIVE')
    
    def test_retrieve_other_user_goal_forbidden(self):
        """Test that users cannot retrieve other users' goals."""
        response = self.client.get(f'/api/v1/goals/{self.other_user_goal.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_retrieve_nonexistent_goal(self):
        """Test retrieving a goal that doesn't exist."""
        fake_id = '00000000-0000-0000-0000-000000000000'
        response = self.client.get(f'/api/v1/goals/{fake_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_retrieve_unauthenticated(self):
        """Test that unauthenticated users cannot retrieve goals."""
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_includes_computed_fields(self):
        """Test that retrieved goal includes computed fields."""
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/')
        
        self.assertIn('total_contributed', response.data)
        self.assertIn('progress_percent', response.data)
        self.assertEqual(response.data['total_contributed'], '0.00')
        self.assertEqual(response.data['progress_percent'], 0)
    
    # ============ UPDATE GOAL TESTS ============
    
    def test_update_own_goal_partial(self):
        """Test partially updating a goal that belongs to the user."""
        data = {
            'name': 'Updated Emergency Fund',
            'target_amount': '750000.00'
        }
        response = self.client.patch(f'/api/v1/goals/{self.goal_active.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Emergency Fund')
        self.assertEqual(response.data['target_amount'], '750000.00')
        self.assertEqual(response.data['currency'], 'NGN')  # Unchanged
        self.assertEqual(response.data['status'], 'ACTIVE')  # Unchanged
    
    def test_update_other_user_goal_forbidden(self):
        """Test that users cannot update other users' goals."""
        data = {'name': 'Hacked Name'}
        response = self.client.patch(f'/api/v1/goals/{self.other_user_goal.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_prevents_user_change(self):
        """Test that update cannot change the user."""
        data = {'user': self.other_user.id}
        response = self.client.patch(f'/api/v1/goals/{self.goal_active.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal = Goal.objects.get(id=self.goal_active.id)
        self.assertEqual(goal.user, self.user)  # Unchanged
    
    def test_update_prevents_status_change(self):
        """Test that update cannot change the status."""
        data = {'status': 'COMPLETED'}
        response = self.client.patch(f'/api/v1/goals/{self.goal_active.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal = Goal.objects.get(id=self.goal_active.id)
        self.assertEqual(goal.status, 'ACTIVE')  # Unchanged
    
    def test_update_invalid_target_amount(self):
        """Test updating with invalid target amount."""
        data = {'target_amount': '-50000.00'}
        response = self.client.patch(f'/api/v1/goals/{self.goal_active.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('target_amount', response.data)
    
    def test_update_unauthenticated(self):
        """Test that unauthenticated users cannot update goals."""
        self.client.force_authenticate(user=None)
        data = {'name': 'Updated Name'}
        response = self.client.patch(f'/api/v1/goals/{self.goal_active.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # ============ PAUSE GOAL TESTS ============
    
    def test_pause_active_goal(self):
        """Test pausing an ACTIVE goal."""
        response = self.client.post(f'/api/v1/goals/{self.goal_active.id}/pause/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PAUSED')
        
        # Verify in database
        goal = Goal.objects.get(id=self.goal_active.id)
        self.assertEqual(goal.status, 'PAUSED')
    
    def test_pause_paused_goal_error(self):
        """Test pausing a goal that is already PAUSED."""
        response = self.client.post(f'/api/v1/goals/{self.goal_paused.id}/pause/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertIn('PAUSED', response.data['detail'])
    
    def test_pause_other_user_goal_forbidden(self):
        """Test that users cannot pause other users' goals."""
        response = self.client.post(f'/api/v1/goals/{self.other_user_goal.id}/pause/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_pause_unauthenticated(self):
        """Test that unauthenticated users cannot pause goals."""
        self.client.force_authenticate(user=None)
        response = self.client.post(f'/api/v1/goals/{self.goal_active.id}/pause/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_pause_returns_detail_serializer(self):
        """Test that pause action returns detail serializer response."""
        response = self.client.post(f'/api/v1/goals/{self.goal_active.id}/pause/')
        
        # Should have all detail fields
        self.assertIn('total_contributed', response.data)
        self.assertIn('progress_percent', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
    
    def test_pause_completed_goal_error(self):
        """Test pausing a COMPLETED goal."""
        goal = Goal.objects.create(
            user=self.user,
            name='Completed Goal',
            target_amount=Decimal('50000.00'),
            status='COMPLETED'
        )
        
        response = self.client.post(f'/api/v1/goals/{goal.id}/pause/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    # ============ RESUME GOAL TESTS ============
    
    def test_resume_paused_goal(self):
        """Test resuming a PAUSED goal."""
        response = self.client.post(f'/api/v1/goals/{self.goal_paused.id}/resume/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ACTIVE')
        
        # Verify in database
        goal = Goal.objects.get(id=self.goal_paused.id)
        self.assertEqual(goal.status, 'ACTIVE')
    
    def test_resume_active_goal_error(self):
        """Test resuming a goal that is already ACTIVE."""
        response = self.client.post(f'/api/v1/goals/{self.goal_active.id}/resume/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertIn('ACTIVE', response.data['detail'])
    
    def test_resume_other_user_goal_forbidden(self):
        """Test that users cannot resume other users' goals."""
        response = self.client.post(f'/api/v1/goals/{self.other_user_goal.id}/resume/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_resume_unauthenticated(self):
        """Test that unauthenticated users cannot resume goals."""
        self.client.force_authenticate(user=None)
        response = self.client.post(f'/api/v1/goals/{self.goal_paused.id}/resume/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_resume_returns_detail_serializer(self):
        """Test that resume action returns detail serializer response."""
        response = self.client.post(f'/api/v1/goals/{self.goal_paused.id}/resume/')
        
        # Should have all detail fields
        self.assertIn('total_contributed', response.data)
        self.assertIn('progress_percent', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
    
    def test_resume_completed_goal_error(self):
        """Test resuming a COMPLETED goal."""
        goal = Goal.objects.create(
            user=self.user,
            name='Completed Goal',
            target_amount=Decimal('50000.00'),
            status='COMPLETED'
        )
        
        response = self.client.post(f'/api/v1/goals/{goal.id}/resume/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    # ============ PAGINATION & ORDERING TESTS ============
    
    def test_list_with_pagination(self):
        """Test that list endpoint supports pagination."""
        response = self.client.get('/api/v1/goals/')
        
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 2)
    
    def test_list_ordering_by_created_at_descending(self):
        """Test that default ordering is by created_at descending."""
        response = self.client.get('/api/v1/goals/?ordering=-created_at')
        
        results = response.data['results']
        # Most recent first
        self.assertEqual(str(results[0]['id']), str(self.goal_paused.id))
        self.assertEqual(str(results[1]['id']), str(self.goal_active.id))
    
    # ============ SUMMARY ACTION TESTS ============
    
    def test_summary_basic(self):
        """Test getting goal summary without transactions."""
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.goal_active.id))
        self.assertEqual(response.data['name'], 'Emergency Fund')
        self.assertEqual(response.data['total_contributed'], '0.00')
        self.assertEqual(response.data['total_debited'], '0.00')
        self.assertEqual(response.data['total_fees'], '0.00')
        self.assertEqual(response.data['progress_percent'], 0)
    
    def test_summary_with_successful_credits(self):
        """Test summary with successful CREDIT transactions."""
        # Create successful credit transactions
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req001',
            occurred_at=datetime.now(timezone.utc)
        )
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('150000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req002',
            occurred_at=datetime.now(timezone.utc)
        )
        
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_contributed'], '250000.00')
        self.assertEqual(response.data['total_debited'], '0.00')
        self.assertEqual(response.data['total_fees'], '0.00')
        # 250000 / 500000 * 100 = 50%
        self.assertEqual(response.data['progress_percent'], 50)
    
    def test_summary_with_all_transaction_types(self):
        """Test summary with CREDIT, DEBIT, and FEE transactions."""
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('200000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req001',
            occurred_at=datetime.now(timezone.utc)
        )
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='DEBIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req002',
            occurred_at=datetime.now(timezone.utc)
        )
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='FEE',
            amount=Decimal('5000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req003',
            occurred_at=datetime.now(timezone.utc)
        )
        
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_contributed'], '200000.00')
        self.assertEqual(response.data['total_debited'], '50000.00')
        self.assertEqual(response.data['total_fees'], '5000.00')
        # 200000 / 500000 * 100 = 40%
        self.assertEqual(response.data['progress_percent'], 40)
    
    def test_summary_progress_capped_at_100(self):
        """Test that progress_percent is capped at 100."""
        # Create transaction exceeding target amount
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('600000.00'),  # More than target 500000
            currency='NGN',
            status='SUCCESS',
            request_ref='req001',
            occurred_at=datetime.now(timezone.utc)
        )
        
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_contributed'], '600000.00')
        # Should be capped at 100, not 120
        self.assertEqual(response.data['progress_percent'], 100)
    
    def test_summary_ignores_failed_transactions(self):
        """Test that FAILED transactions are not included in summary."""
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req001',
            occurred_at=datetime.now(timezone.utc)
        )
        # Create failed transaction (should be ignored)
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('200000.00'),
            currency='NGN',
            status='FAILED',
            request_ref='req002',
            occurred_at=datetime.now(timezone.utc)
        )
        
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only successful credit should be counted
        self.assertEqual(response.data['total_contributed'], '100000.00')
        self.assertEqual(response.data['progress_percent'], 20)  # 100000/500000*100
    
    def test_summary_ignores_pending_transactions(self):
        """Test that PENDING transactions are not included in summary."""
        Transaction.objects.create(
            user=self.user,
            goal=self.goal_active,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='PENDING',
            request_ref='req001',
            occurred_at=datetime.now(timezone.utc)
        )
        
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_contributed'], '0.00')
        self.assertEqual(response.data['progress_percent'], 0)
    
    def test_summary_forbidden_for_other_user(self):
        """Test that users cannot see summary for other users' goals."""
        response = self.client.get(f'/api/v1/goals/{self.other_user_goal.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_summary_unauthenticated(self):
        """Test that unauthenticated users cannot access summary."""
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_summary_nonexistent_goal(self):
        """Test summary for nonexistent goal."""
        fake_id = '00000000-0000-0000-0000-000000000000'
        response = self.client.get(f'/api/v1/goals/{fake_id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_summary_includes_all_goal_fields(self):
        """Test that summary includes all goal detail fields."""
        response = self.client.get(f'/api/v1/goals/{self.goal_active.id}/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have all goal fields
        self.assertIn('id', response.data)
        self.assertIn('user', response.data)
        self.assertIn('name', response.data)
        self.assertIn('target_amount', response.data)
        self.assertIn('currency', response.data)
        self.assertIn('status', response.data)
        self.assertIn('metadata', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        # Plus summary fields
        self.assertIn('total_contributed', response.data)
        self.assertIn('total_debited', response.data)
        self.assertIn('total_fees', response.data)
        self.assertIn('progress_percent', response.data)

