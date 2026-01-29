# Goal Serializers Quick Reference

**Quick Links:** [Full Documentation](GOAL_SERIALIZERS_DOCUMENTATION.md) | [Implementation Summary](GOAL_SERIALIZERS_IMPLEMENTATION.md) | [Tests](core_apps/goals/tests_serializers.py)

---

## At a Glance

Three serializers for Goal model operations:

| Serializer | Purpose | Use Case |
|-----------|---------|----------|
| **GoalCreateSerializer** | Create goals | POST /api/v1/goals/ |
| **GoalUpdateSerializer** | Update goals | PATCH /api/v1/goals/{id}/ |
| **GoalDetailSerializer** | Retrieve goals | GET /api/v1/goals/{id}/ |

---

## Quick Copy-Paste Examples

### Create Goal
```bash
curl -X POST http://localhost:8000/api/v1/goals/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emergency Fund",
    "target_amount": "500000.00",
    "currency": "NGN",
    "metadata": {"priority": "high"}
  }'
```

**Response:**
```json
{
  "id": "550e8400-...",
  "name": "Emergency Fund",
  "target_amount": "500000.00",
  "currency": "NGN",
  "status": "ACTIVE",
  "total_contributed": "0.00",
  "progress_percent": 0
}
```

### Update Goal
```bash
curl -X PATCH http://localhost:8000/api/v1/goals/550e8400-.../ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Goal Name",
    "target_amount": "750000.00"
  }'
```

### Get Goal
```bash
curl -X GET http://localhost:8000/api/v1/goals/550e8400-.../ \
  -H "Authorization: Bearer <token>"
```

---

## Field Reference

### GoalCreateSerializer
**Required:** name, target_amount  
**Optional:** currency (default: "NGN"), metadata (default: {})  
**Auto-set:** user=request.user, status="ACTIVE"

### GoalUpdateSerializer
**Updatable:** name, target_amount, currency, metadata  
**Protected:** user (cannot change), status (cannot change)  
**Partial:** Enable with `partial=True`

### GoalDetailSerializer
**All Fields:** id, name, target_amount, currency, status, metadata, created_at, updated_at  
**Computed:** total_contributed (string), progress_percent (int 0-100)

---

## Validation Rules

| Field | Rule | Example |
|-------|------|---------|
| `name` | Non-empty, stripped | "Emergency Fund" ✅ |
| `target_amount` | > 0 | "500000.00" ✅, "0.00" ❌ |
| `currency` | 3-char code (auto-uppercase) | "ngn" → "NGN" ✅ |
| `metadata` | Valid JSON object | {"key": "value"} ✅ |
| `status` | Not updatable | Always "ACTIVE" on create |
| `user` | Not updatable | Always request.user on create |

---

## In Views

### CreateAPIView
```python
from rest_framework.generics import CreateAPIView
from .serializers import GoalCreateSerializer, GoalDetailSerializer

class GoalCreateView(CreateAPIView):
    serializer_class = GoalCreateSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request  # Important!
        return context
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Return detail serializer for full response
        goal_id = response.data['id']  # Adjust based on response
        goal = Goal.objects.get(id=goal_id)
        response.data = GoalDetailSerializer(goal).data
        return response
```

### UpdateAPIView
```python
from rest_framework.generics import UpdateAPIView
from .serializers import GoalUpdateSerializer

class GoalUpdateView(UpdateAPIView):
    queryset = Goal.objects.all()
    serializer_class = GoalUpdateSerializer
    lookup_field = 'id'
    partial = True  # Enable PATCH
```

### RetrieveAPIView
```python
from rest_framework.generics import RetrieveAPIView
from .serializers import GoalDetailSerializer

class GoalDetailView(RetrieveAPIView):
    queryset = Goal.objects.all()
    serializer_class = GoalDetailSerializer
    lookup_field = 'id'
```

---

## Error Responses

### Invalid target_amount
```json
{
  "target_amount": ["Target amount must be greater than 0."]
}
```

### Empty name
```json
{
  "name": ["Goal name cannot be empty."]
}
```

### Invalid currency
```json
{
  "currency": ["Currency must be a 3-character code (e.g., 'NGN')."]
}
```

### Missing required field
```json
{
  "target_amount": ["This field is required."]
}
```

---

## Testing

Run tests:
```bash
python manage.py test core_apps.goals.tests_serializers
```

Run specific test class:
```bash
python manage.py test core_apps.goals.tests_serializers.GoalCreateSerializerTestCase
```

With verbose output:
```bash
python manage.py test core_apps.goals.tests_serializers -v 2
```

---

## Key Gotchas

⚠️ **Always pass request context when creating**
```python
# ❌ Wrong
serializer = GoalCreateSerializer(data=request.data)

# ✅ Right
serializer = GoalCreateSerializer(
    data=request.data,
    context={'request': request}
)
```

⚠️ **Enable partial=True for PATCH**
```python
# ❌ Wrong
serializer = GoalUpdateSerializer(goal, data=data)  # Full validation

# ✅ Right
serializer = GoalUpdateSerializer(goal, data=data, partial=True)
```

⚠️ **Decimals returned as strings**
```python
# Response has:
"target_amount": "500000.00"  # String, not float

# Access as:
decimal_value = Decimal(data['target_amount'])
```

⚠️ **User and status changes silently ignored (not errors)**
```python
# This will NOT error, just ignore status change
data = {"status": "COMPLETED"}
serializer = GoalUpdateSerializer(goal, data=data, partial=True)
serializer.is_valid()  # Returns True
serializer.save()      # Status remains unchanged
```

---

## Computed Fields

### total_contributed
- **Current:** Placeholder "0.00"
- **Type:** String (Decimal)
- **Future:** Will aggregate from ledger

### progress_percent
- **Current:** Calculated as (0.00 / target) * 100 = 0
- **Type:** Integer 0-100
- **Clamping:** Max 100 (even if over-contributed)
- **Formula:** `(total_contributed / target_amount) * 100`

---

## File Locations

| File | Purpose | Lines |
|------|---------|-------|
| [serializers.py](core_apps/goals/serializers.py) | Implementation | 190 |
| [tests_serializers.py](core_apps/goals/tests_serializers.py) | Tests (50+) | 530 |
| [GOAL_SERIALIZERS_DOCUMENTATION.md](GOAL_SERIALIZERS_DOCUMENTATION.md) | Full docs | 700+ |
| [GOAL_SERIALIZERS_IMPLEMENTATION.md](GOAL_SERIALIZERS_IMPLEMENTATION.md) | Summary | 400+ |
| [GOAL_SERIALIZERS_QUICK_REFERENCE.md](GOAL_SERIALIZERS_QUICK_REFERENCE.md) | This file | — |

---

## Next Steps

1. Create GoalViewSet in views.py
2. Register routes in urls.py
3. Add to API documentation
4. Test with curl/Postman

---

**Status:** ✅ Complete  
**Last Updated:** January 29, 2026  
**Test Coverage:** 50+ cases, all passing
