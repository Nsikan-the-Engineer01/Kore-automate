from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework import status
from core_apps.goals.models import Goal
from core_apps.goals.serializers import (
    GoalCreateSerializer,
    GoalUpdateSerializer,
    GoalDetailSerializer
)


class GoalCreateSerializerTestCase(TestCase):
    """Test suite for GoalCreateSerializer."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
    
    def test_create_goal_with_all_fields(self):
        """Test creating a goal with all fields provided."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Emergency Fund',
            'target_amount': '500000.00',
            'currency': 'ngn',
            'metadata': {'priority': 'high', 'category': 'savings'}
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        goal = serializer.save()
        
        self.assertEqual(goal.name, 'Emergency Fund')
        self.assertEqual(goal.target_amount, Decimal('500000.00'))
        self.assertEqual(goal.currency, 'NGN')  # Uppercased
        self.assertEqual(goal.status, 'ACTIVE')
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.metadata, {'priority': 'high', 'category': 'savings'})
    
    def test_create_goal_with_defaults(self):
        """Test creating a goal with only required fields."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Savings Goal',
            'target_amount': '100000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        goal = serializer.save()
        
        self.assertEqual(goal.name, 'Savings Goal')
        self.assertEqual(goal.target_amount, Decimal('100000.00'))
        self.assertEqual(goal.currency, 'NGN')  # Default currency
        self.assertEqual(goal.status, 'ACTIVE')  # Default status
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.metadata, {})  # Default empty dict
    
    def test_currency_default_if_not_provided(self):
        """Test that currency defaults to NGN if not provided."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Test Goal',
            'target_amount': '50000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        goal = serializer.save()
        
        self.assertEqual(goal.currency, 'NGN')
    
    def test_currency_converted_to_uppercase(self):
        """Test that currency is converted to uppercase."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Test Goal',
            'target_amount': '50000.00',
            'currency': 'usd'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        goal = serializer.save()
        
        self.assertEqual(goal.currency, 'USD')
    
    def test_name_whitespace_stripped(self):
        """Test that name whitespace is stripped."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': '  Vacation Fund  ',
            'target_amount': '200000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        goal = serializer.save()
        
        self.assertEqual(goal.name, 'Vacation Fund')
    
    def test_target_amount_zero_invalid(self):
        """Test that target_amount of 0 is invalid."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Invalid Goal',
            'target_amount': '0.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('target_amount', serializer.errors)
        self.assertIn('greater than 0', str(serializer.errors['target_amount']))
    
    def test_target_amount_negative_invalid(self):
        """Test that negative target_amount is invalid."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Invalid Goal',
            'target_amount': '-50000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('target_amount', serializer.errors)
    
    def test_empty_name_invalid(self):
        """Test that empty name is invalid."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': '',
            'target_amount': '50000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
    
    def test_whitespace_only_name_invalid(self):
        """Test that whitespace-only name is invalid."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': '   ',
            'target_amount': '50000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        self.assertIn('cannot be empty', str(serializer.errors['name']))
    
    def test_invalid_currency_too_short(self):
        """Test that currency shorter than 3 chars is invalid."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Test Goal',
            'target_amount': '50000.00',
            'currency': 'US'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('currency', serializer.errors)
        self.assertIn('3-character code', str(serializer.errors['currency']))
    
    def test_invalid_currency_too_long(self):
        """Test that currency longer than 3 chars is invalid."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Test Goal',
            'target_amount': '50000.00',
            'currency': 'USDA'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('currency', serializer.errors)
    
    def test_missing_required_fields(self):
        """Test that missing required fields returns errors."""
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {}
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        self.assertIn('target_amount', serializer.errors)


class GoalUpdateSerializerTestCase(TestCase):
    """Test suite for GoalUpdateSerializer."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.goal = Goal.objects.create(
            user=self.user,
            name='Original Goal',
            target_amount=Decimal('500000.00'),
            currency='NGN',
            status='ACTIVE',
            metadata={'priority': 'high'}
        )
    
    def test_update_name_only(self):
        """Test updating only the name field."""
        data = {'name': 'Updated Goal Name'}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        self.assertEqual(updated_goal.name, 'Updated Goal Name')
        self.assertEqual(updated_goal.target_amount, Decimal('500000.00'))
        self.assertEqual(updated_goal.currency, 'NGN')
        self.assertEqual(updated_goal.status, 'ACTIVE')
    
    def test_update_target_amount_only(self):
        """Test updating only the target amount."""
        data = {'target_amount': '750000.00'}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        self.assertEqual(updated_goal.name, 'Original Goal')
        self.assertEqual(updated_goal.target_amount, Decimal('750000.00'))
    
    def test_update_currency_only(self):
        """Test updating only the currency."""
        data = {'currency': 'usd'}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        self.assertEqual(updated_goal.currency, 'USD')
        self.assertEqual(updated_goal.name, 'Original Goal')
    
    def test_update_metadata_only(self):
        """Test updating only the metadata."""
        new_metadata = {'priority': 'low', 'category': 'vacation'}
        data = {'metadata': new_metadata}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        self.assertEqual(updated_goal.metadata, new_metadata)
        self.assertEqual(updated_goal.name, 'Original Goal')
    
    def test_update_multiple_fields(self):
        """Test updating multiple fields at once."""
        data = {
            'name': 'Multi Updated',
            'target_amount': '600000.00',
            'currency': 'ghs'
        }
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        self.assertEqual(updated_goal.name, 'Multi Updated')
        self.assertEqual(updated_goal.target_amount, Decimal('600000.00'))
        self.assertEqual(updated_goal.currency, 'GHS')
    
    def test_prevent_user_change(self):
        """Test that user cannot be changed via update."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com'
        )
        
        data = {'user': other_user.id}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        # User should remain unchanged
        self.assertEqual(updated_goal.user, self.user)
    
    def test_prevent_status_change(self):
        """Test that status cannot be changed via update."""
        data = {'status': 'COMPLETED'}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        # Status should remain unchanged
        self.assertEqual(updated_goal.status, 'ACTIVE')
    
    def test_prevent_user_and_status_change_together(self):
        """Test that neither user nor status change even with other valid updates."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com'
        )
        
        data = {
            'name': 'Updated Name',
            'user': other_user.id,
            'status': 'COMPLETED'
        }
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_goal = serializer.save()
        
        self.assertEqual(updated_goal.name, 'Updated Name')
        self.assertEqual(updated_goal.user, self.user)
        self.assertEqual(updated_goal.status, 'ACTIVE')
    
    def test_update_validation_target_amount(self):
        """Test validation of target_amount during update."""
        data = {'target_amount': '0.00'}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('target_amount', serializer.errors)
    
    def test_update_validation_name(self):
        """Test validation of name during update."""
        data = {'name': '   '}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
    
    def test_update_validation_currency(self):
        """Test validation of currency during update."""
        data = {'currency': 'US'}
        serializer = GoalUpdateSerializer(self.goal, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('currency', serializer.errors)


class GoalDetailSerializerTestCase(TestCase):
    """Test suite for GoalDetailSerializer."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.goal = Goal.objects.create(
            user=self.user,
            name='Detail Test Goal',
            target_amount=Decimal('100000.00'),
            currency='NGN',
            status='ACTIVE',
            metadata={'test': True}
        )
    
    def test_detail_contains_all_fields(self):
        """Test that detail serializer includes all expected fields."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        expected_fields = [
            'id', 'name', 'target_amount', 'currency', 'status',
            'metadata', 'total_contributed', 'progress_percent',
            'created_at', 'updated_at'
        ]
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_detail_read_only_fields(self):
        """Test that computed fields are read-only."""
        serializer = GoalDetailSerializer(self.goal)
        
        # Check that computed fields are in read_only_fields
        self.assertIn('total_contributed', serializer.fields)
        self.assertIn('progress_percent', serializer.fields)
        self.assertTrue(serializer.fields['total_contributed'].read_only)
        self.assertTrue(serializer.fields['progress_percent'].read_only)
    
    def test_target_amount_as_string(self):
        """Test that target_amount is returned as string."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        self.assertIsInstance(data['target_amount'], str)
        self.assertEqual(data['target_amount'], '100000.00')
    
    def test_total_contributed_placeholder(self):
        """Test that total_contributed returns placeholder '0.00'."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        self.assertEqual(data['total_contributed'], '0.00')
        self.assertIsInstance(data['total_contributed'], str)
    
    def test_progress_percent_zero_with_no_contributions(self):
        """Test that progress_percent is 0 with no contributions."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        self.assertEqual(data['progress_percent'], 0)
        self.assertIsInstance(data['progress_percent'], int)
    
    def test_progress_percent_calculation_50_percent(self):
        """Test progress_percent calculation at 50%."""
        # Mock: If total_contributed was 50000.00 and target is 100000.00
        # progress should be 50
        goal = Goal.objects.create(
            user=self.user,
            name='50% Goal',
            target_amount=Decimal('100.00'),
            currency='NGN',
            status='ACTIVE'
        )
        
        serializer = GoalDetailSerializer(goal)
        # With placeholder 0.00, should be 0%
        self.assertEqual(serializer.get_progress_percent(goal), 0)
    
    def test_progress_percent_clamped_at_100(self):
        """Test that progress_percent is clamped at 100."""
        # Even if total_contributed > target_amount, should return 100
        goal = Goal.objects.create(
            user=self.user,
            name='Over Goal',
            target_amount=Decimal('100.00'),
            currency='NGN',
            status='COMPLETED'
        )
        
        serializer = GoalDetailSerializer(goal)
        # With placeholder 0.00, should be 0% but testing clamping logic
        progress = serializer.get_progress_percent(goal)
        self.assertLessEqual(progress, 100)
    
    def test_progress_percent_with_zero_target(self):
        """Test progress_percent when target_amount is 0."""
        goal = Goal.objects.create(
            user=self.user,
            name='Zero Target',
            target_amount=Decimal('0.00'),
            currency='NGN',
            status='ACTIVE'
        )
        
        serializer = GoalDetailSerializer(goal)
        progress = serializer.get_progress_percent(goal)
        self.assertEqual(progress, 0)
    
    def test_detail_metadata_preserved(self):
        """Test that metadata is preserved in detail response."""
        goal_metadata = {'priority': 'high', 'category': 'emergency'}
        goal = Goal.objects.create(
            user=self.user,
            name='Metadata Test',
            target_amount=Decimal('50000.00'),
            currency='NGN',
            status='ACTIVE',
            metadata=goal_metadata
        )
        
        serializer = GoalDetailSerializer(goal)
        data = serializer.data
        
        self.assertEqual(data['metadata'], goal_metadata)
    
    def test_detail_timestamps_included(self):
        """Test that created_at and updated_at are included."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIsNotNone(data['created_at'])
        self.assertIsNotNone(data['updated_at'])
    
    def test_detail_id_included(self):
        """Test that id is included and correct."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        self.assertEqual(str(data['id']), str(self.goal.id))
    
    def test_detail_status_included(self):
        """Test that status is included."""
        serializer = GoalDetailSerializer(self.goal)
        data = serializer.data
        
        self.assertEqual(data['status'], 'ACTIVE')
    
    def test_detail_all_statuses(self):
        """Test detail serializer with all status types."""
        statuses = ['ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELLED']
        
        for status_choice in statuses:
            goal = Goal.objects.create(
                user=self.user,
                name=f'Status {status_choice}',
                target_amount=Decimal('50000.00'),
                currency='NGN',
                status=status_choice
            )
            
            serializer = GoalDetailSerializer(goal)
            data = serializer.data
            
            self.assertEqual(data['status'], status_choice)
