# Goal Serializers Documentation

**File:** `core_apps/goals/serializers.py`  
**Status:** ✅ Complete  
**Date:** January 29, 2026

---

## Overview

Three DRF serializers for the Goal model, each designed for a specific use case:

1. **GoalCreateSerializer** — Creating new goals
2. **GoalUpdateSerializer** — Updating existing goals
3. **GoalDetailSerializer** — Retrieving goal details with computed fields

---

## GoalCreateSerializer

### Purpose
Handles creation of new financial goals with validation and automatic user assignment.

### Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `name` | String | Yes | — | Max 120 chars; validated as non-empty |
| `target_amount` | Decimal | Yes | — | Must be > 0; stored as Decimal(14,2) |
| `currency` | String | No | "NGN" | 3-char code; converted to uppercase |
| `metadata` | JSON | No | {} | Optional custom metadata object |

### Automatic Fields

| Field | Value |
|-------|-------|
| `user` | Set to `request.user` on creation |
| `status` | Set to "ACTIVE" on creation |

### Usage

```python
from core_apps.goals.serializers import GoalCreateSerializer

# In a CreateAPIView
serializer = GoalCreateSerializer(
    data=request.data,
    context={'request': request}  # IMPORTANT: Pass request context
)
if serializer.is_valid():
    goal = serializer.save()  # User & status auto-set
else:
    return Response(serializer.errors, status=400)
```

### Validations

1. **target_amount > 0**
   ```python
   def validate_target_amount(self, value):
       if value <= 0:
           raise serializers.ValidationError("Target amount must be greater than 0.")
   ```

2. **name is not empty**
   ```python
   def validate_name(self, value):
       if not value or not value.strip():
           raise serializers.ValidationError("Goal name cannot be empty.")
       return value.strip()
   ```

3. **currency is 3-character code**
   ```python
   def validate_currency(self, value):
       if not value or len(value) != 3:
           raise serializers.ValidationError("Currency must be a 3-character code (e.g., 'NGN').")
       return value.upper()
   ```

### Error Examples

**Invalid Amount:**
```json
{
  "target_amount": ["Target amount must be greater than 0."]
}
```

**Empty Name:**
```json
{
  "name": ["Goal name cannot be empty."]
}
```

**Invalid Currency:**
```json
{
  "currency": ["Currency must be a 3-character code (e.g., 'NGN')."]
}
```

### Request Example

```json
{
  "name": "Emergency Fund",
  "target_amount": "500000.00",
  "currency": "ngn",
  "metadata": {
    "category": "savings",
    "priority": "high"
  }
}
```

### Response Example

```json
{
  "name": "Emergency Fund",
  "target_amount": "500000.00",
  "currency": "NGN",
  "metadata": {
    "category": "savings",
    "priority": "high"
  }
}
```

Note: `user` and `status` are set automatically but not returned (write_only behavior).

---

## GoalUpdateSerializer

### Purpose
Handles partial updates to existing goals while preventing user and status changes.

### Fields

| Field | Type | Required | Updatable |
|-------|------|----------|-----------|
| `name` | String | No | ✅ Yes |
| `target_amount` | Decimal | No | ✅ Yes |
| `currency` | String | No | ✅ Yes |
| `metadata` | JSON | No | ✅ Yes |
| `user` | Foreign Key | — | ❌ No |
| `status` | String | — | ❌ No |

### Usage

```python
from core_apps.goals.serializers import GoalUpdateSerializer

# In an UpdateAPIView
goal = Goal.objects.get(id=goal_id)
serializer = GoalUpdateSerializer(
    goal,
    data=request.data,
    partial=True  # Enable partial updates
)
if serializer.is_valid():
    goal = serializer.save()
else:
    return Response(serializer.errors, status=400)
```

### Partial Updates

The serializer enforces `partial=True` semantics:

```python
# Update only name
PATCH /api/v1/goals/{id}/
{
  "name": "New Goal Name"
}
```

```python
# Update only target amount
PATCH /api/v1/goals/{id}/
{
  "target_amount": "750000.00"
}
```

```python
# Update metadata
PATCH /api/v1/goals/{id}/
{
  "metadata": {
    "updated_priority": "low"
  }
}
```

### Validation

Same validations as GoalCreateSerializer, but applied only to provided fields:

1. **target_amount > 0 (if provided)**
2. **name is not empty (if provided)**
3. **currency is 3-character code (if provided)**

### Restrictions

**User Change Prevention:**
```python
def update(self, instance, validated_data):
    validated_data.pop('user', None)  # Silently removes any user attempt
    ...
```

**Status Change Prevention:**
```python
def update(self, instance, validated_data):
    validated_data.pop('status', None)  # Silently removes any status attempt
    ...
```

If a client tries to change `user` or `status`, they are silently ignored (not returned as errors).

### Request Example

```json
{
  "name": "Updated Goal Name"
}
```

### Response Example

```json
{
  "name": "Updated Goal Name",
  "target_amount": "500000.00",
  "currency": "NGN",
  "metadata": {
    "category": "savings",
    "priority": "high"
  }
}
```

---

## GoalDetailSerializer

### Purpose
Exposes complete goal information with computed read-only fields (total_contributed, progress_percent).

### Fields

| Field | Type | Read-Only | Notes |
|-------|------|-----------|-------|
| `id` | UUID | ✅ Yes | Auto-generated |
| `name` | String | — | Goal name |
| `target_amount` | Decimal | — | Returned as string |
| `currency` | String | — | 3-char code |
| `status` | String | — | ACTIVE, PAUSED, COMPLETED, CANCELLED |
| `metadata` | JSON | — | Custom metadata |
| `total_contributed` | String | ✅ Yes | Computed; "0.00" for now |
| `progress_percent` | Integer | ✅ Yes | 0-100 percentage |
| `created_at` | DateTime | ✅ Yes | Timestamp |
| `updated_at` | DateTime | ✅ Yes | Timestamp |

### Decimal Handling

Per DRF standard, decimals are returned as strings to preserve precision:

```python
target_amount = serializers.DecimalField(
    max_digits=14,
    decimal_places=2,
    coerce_to_string=True  # Returns "500000.00" not 500000.00
)
```

### Computed Fields

#### total_contributed

**Current Implementation:**
```python
def get_total_contributed(self, obj):
    """Returns '0.00' as placeholder."""
    return "0.00"
```

**Placeholder Status:**
- ⏳ Waiting for ledger aggregation implementation
- Returns decimal as string ("0.00")

**Future Implementation:**
```python
def get_total_contributed(self, obj):
    """Query ledger for total contributions."""
    from core_apps.ledger.models import LedgerEntry
    total = LedgerEntry.objects.filter(
        goal=obj,
        entry_type='DEBIT'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    return str(total)
```

#### progress_percent

**Formula:**
```
progress = (total_contributed / target_amount) * 100
```

**Clamping:**
- Minimum: 0 (never negative)
- Maximum: 100 (even if over-contributed)

**Current Calculation:**
```python
def get_progress_percent(self, obj):
    total_contributed = Decimal(self.get_total_contributed(obj))
    if obj.target_amount <= 0:
        return 0
    progress = (total_contributed / obj.target_amount) * 100
    return int(min(100, max(0, progress)))  # Clamp 0-100
```

**Example:**
```
target_amount = 500000.00
total_contributed = 250000.00  # (once ledger aggregation ready)
progress = (250000.00 / 500000.00) * 100 = 50%
```

### Usage

```python
from core_apps.goals.serializers import GoalDetailSerializer

# In a RetrieveAPIView
goal = Goal.objects.get(id=goal_id)
serializer = GoalDetailSerializer(goal)
return Response(serializer.data)
```

### Response Example

**Success Case (No Contributions):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Emergency Fund",
  "target_amount": "500000.00",
  "currency": "NGN",
  "status": "ACTIVE",
  "metadata": {
    "category": "savings",
    "priority": "high"
  },
  "total_contributed": "0.00",
  "progress_percent": 0,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

**With Contributions (Future):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Emergency Fund",
  "target_amount": "500000.00",
  "currency": "NGN",
  "status": "ACTIVE",
  "metadata": {
    "category": "savings",
    "priority": "high"
  },
  "total_contributed": "250000.00",
  "progress_percent": 50,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

**Over-Contributed (Clamped):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Vacation Fund",
  "target_amount": "100000.00",
  "currency": "NGN",
  "status": "COMPLETED",
  "metadata": {
    "category": "travel"
  },
  "total_contributed": "125000.00",
  "progress_percent": 100,
  "created_at": "2026-01-01T08:00:00Z",
  "updated_at": "2026-01-25T14:30:00Z"
}
```

---

## API Endpoint Integration

### Create Goal

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import GoalCreateSerializer

class GoalCreateView(APIView):
    def post(self, request):
        serializer = GoalCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            goal = serializer.save()
            return Response(
                GoalDetailSerializer(goal).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Update Goal

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import GoalUpdateSerializer, GoalDetailSerializer
from .models import Goal

class GoalUpdateView(APIView):
    def patch(self, request, goal_id):
        goal = Goal.objects.get(id=goal_id)
        self.check_object_permissions(request, goal)
        
        serializer = GoalUpdateSerializer(
            goal,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            goal = serializer.save()
            return Response(
                GoalDetailSerializer(goal).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Retrieve Goal

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import GoalDetailSerializer
from .models import Goal

class GoalDetailView(APIView):
    def get(self, request, goal_id):
        goal = Goal.objects.get(id=goal_id)
        self.check_object_permissions(request, goal)
        
        serializer = GoalDetailSerializer(goal)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

---

## Testing

### Test GoalCreateSerializer

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from core_apps.goals.serializers import GoalCreateSerializer

class GoalCreateSerializerTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='testuser')
    
    def test_create_valid_goal(self):
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Emergency Fund',
            'target_amount': '500000.00',
            'currency': 'ngn',
            'metadata': {'priority': 'high'}
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        goal = serializer.save()
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.status, 'ACTIVE')
        self.assertEqual(goal.currency, 'NGN')  # Uppercased
    
    def test_invalid_target_amount(self):
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Invalid Goal',
            'target_amount': '0.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('target_amount', serializer.errors)
    
    def test_empty_name_validation(self):
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': '   ',  # Whitespace only
            'target_amount': '500000.00'
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
    
    def test_invalid_currency(self):
        request = self.factory.post('/goals/')
        request.user = self.user
        
        data = {
            'name': 'Goal',
            'target_amount': '500000.00',
            'currency': 'US'  # Only 2 chars
        }
        serializer = GoalCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('currency', serializer.errors)
```

### Test GoalUpdateSerializer

```python
def test_update_prevents_user_change(self):
    goal = Goal.objects.create(
        user=self.user,
        name='Original Name',
        target_amount=500000.00,
        status='ACTIVE'
    )
    
    other_user = User.objects.create_user(username='otheruser')
    
    data = {
        'name': 'Updated Name',
        'user': other_user.id  # Attempt to change user
    }
    serializer = GoalUpdateSerializer(goal, data=data, partial=True)
    self.assertTrue(serializer.is_valid())
    updated_goal = serializer.save()
    
    # User should not change
    self.assertEqual(updated_goal.user, self.user)
    self.assertEqual(updated_goal.name, 'Updated Name')

def test_update_prevents_status_change(self):
    goal = Goal.objects.create(
        user=self.user,
        name='Goal',
        target_amount=500000.00,
        status='ACTIVE'
    )
    
    data = {
        'status': 'COMPLETED'  # Attempt to change status
    }
    serializer = GoalUpdateSerializer(goal, data=data, partial=True)
    self.assertTrue(serializer.is_valid())
    updated_goal = serializer.save()
    
    # Status should not change
    self.assertEqual(updated_goal.status, 'ACTIVE')
```

### Test GoalDetailSerializer

```python
def test_detail_includes_computed_fields(self):
    goal = Goal.objects.create(
        user=self.user,
        name='Test Goal',
        target_amount=500000.00,
        status='ACTIVE'
    )
    
    serializer = GoalDetailSerializer(goal)
    data = serializer.data
    
    self.assertIn('total_contributed', data)
    self.assertIn('progress_percent', data)
    self.assertEqual(data['total_contributed'], '0.00')
    self.assertEqual(data['progress_percent'], 0)
    self.assertIsInstance(data['target_amount'], str)  # Decimal as string

def test_progress_percent_calculation(self):
    goal = Goal.objects.create(
        user=self.user,
        name='Test Goal',
        target_amount=100.00,
        status='ACTIVE'
    )
    
    # Mock total_contributed to test progress calculation
    serializer = GoalDetailSerializer(goal)
    # Since we're using "0.00", progress should be 0
    self.assertEqual(serializer.get_progress_percent(goal), 0)
```

---

## API Responses Summary

| Operation | Serializer | Status Code | Notes |
|-----------|-----------|-------------|-------|
| Create | GoalCreateSerializer | 201 Created | Returns created goal details |
| Retrieve | GoalDetailSerializer | 200 OK | Includes computed fields |
| Update | GoalUpdateSerializer | 200 OK | Prevents user/status changes |
| Delete | — | 204 No Content | No serializer needed |
| List | GoalDetailSerializer | 200 OK | Multiple goals with computed fields |

---

## Security Considerations

✅ **User Isolation** — Goals must belong to requesting user  
✅ **Status Protection** — Status changes restricted to dedicated endpoints  
✅ **User Protection** — Cannot reassign goal to different user via update  
✅ **Validation** — All inputs validated before database operations  

---

## Future Enhancements

1. **Ledger Aggregation** — Update `total_contributed` to query ledger
2. **Status Transitions** — Add dedicated endpoint for status changes
3. **Goal Categories** — Add category field with choices
4. **Recurrence** — Add recurring contribution support
5. **Notifications** — Notify user when progress milestones reached

---

**Status:** ✅ Complete  
**Last Updated:** January 29, 2026
