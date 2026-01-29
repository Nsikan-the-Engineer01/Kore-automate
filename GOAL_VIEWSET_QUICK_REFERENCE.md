# Goal ViewSet Quick Reference

**Files:** 
- [permissions.py](core_apps/goals/permissions.py) — IsOwner permission
- [views.py](core_apps/goals/views.py) — GoalViewSet
- [urls.py](core_apps/goals/urls.py) — URL router
- [tests_viewset.py](core_apps/goals/tests_viewset.py) — 60+ test cases

---

## API Endpoints At A Glance

| Method | Route | Purpose | Status |
|--------|-------|---------|--------|
| GET | /api/v1/goals/ | List user's goals | 200 OK |
| POST | /api/v1/goals/ | Create goal | 201 Created |
| GET | /api/v1/goals/{id}/ | Get goal details | 200 OK |
| PATCH | /api/v1/goals/{id}/ | Update goal | 200 OK |
| POST | /api/v1/goals/{id}/pause/ | Pause goal | 200 OK |
| POST | /api/v1/goals/{id}/resume/ | Resume goal | 200 OK |

---

## Quick Examples

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

**Response (201):**
```json
{
  "id": "550e8400-...",
  "name": "Emergency Fund",
  "target_amount": "500000.00",
  "currency": "NGN",
  "status": "ACTIVE",
  "total_contributed": "0.00",
  "progress_percent": 0,
  "created_at": "2026-01-29T10:30:00Z"
}
```

### List Goals
```bash
curl -X GET http://localhost:8000/api/v1/goals/ \
  -H "Authorization: Bearer <token>"
```

### Get Goal
```bash
curl -X GET http://localhost:8000/api/v1/goals/{id}/ \
  -H "Authorization: Bearer <token>"
```

### Update Goal
```bash
curl -X PATCH http://localhost:8000/api/v1/goals/{id}/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "target_amount": "750000.00"
  }'
```

### Pause Goal
```bash
curl -X POST http://localhost:8000/api/v1/goals/{id}/pause/ \
  -H "Authorization: Bearer <token>"
```

### Resume Goal
```bash
curl -X POST http://localhost:8000/api/v1/goals/{id}/resume/ \
  -H "Authorization: Bearer <token>"
```

---

## Permissions

### IsOwner Permission Class
- **Location:** `core_apps/goals/permissions.py`
- **Purpose:** Verify `obj.user == request.user`
- **Applied To:** All endpoints that access specific goals
- **Error:** 403 Forbidden if user doesn't own goal

### Usage
```python
permission_classes = [IsAuthenticated, IsOwner]
```

---

## Serializer Routing

The viewset automatically selects the correct serializer:

| Action | Serializer |
|--------|-----------|
| POST (create) | GoalCreateSerializer |
| PATCH (update) | GoalUpdateSerializer |
| GET (retrieve) | GoalDetailSerializer |
| GET (list) | GoalDetailSerializer |
| POST (pause) | GoalDetailSerializer |
| POST (resume) | GoalDetailSerializer |

---

## Status Transitions

### Pause Action
```
ACTIVE --pause--> PAUSED
  ✓ Works

PAUSED --pause--> Error (400)
COMPLETED --pause--> Error (400)
CANCELLED --pause--> Error (400)
```

### Resume Action
```
PAUSED --resume--> ACTIVE
  ✓ Works

ACTIVE --resume--> Error (400)
COMPLETED --resume--> Error (400)
CANCELLED --resume--> Error (400)
```

---

## Error Codes

| Code | Scenario |
|------|----------|
| 200 | Successful GET, PATCH, or action |
| 201 | Successful POST (create) |
| 400 | Invalid data or wrong state for action |
| 401 | Not authenticated |
| 403 | Don't own the goal |
| 404 | Goal not found |

---

## Common Error Responses

### Unauthorized (401)
```bash
# No token provided
curl http://localhost:8000/api/v1/goals/

# Response:
{
  "detail": "Authentication credentials were not provided."
}
```

### Forbidden (403)
```bash
# Accessing another user's goal
curl http://localhost:8000/api/v1/goals/{other_user_goal_id}/ \
  -H "Authorization: Bearer <token>"

# Response:
{
  "detail": "You do not have permission to access this goal. It belongs to another user."
}
```

### Bad Request - Invalid State (400)
```bash
# Pause already-paused goal
curl -X POST http://localhost:8000/api/v1/goals/{id}/pause/ \
  -H "Authorization: Bearer <token>"

# Response:
{
  "detail": "Can only pause ACTIVE goals. Current status: PAUSED"
}
```

### Bad Request - Validation (400)
```bash
# Invalid target_amount
{
  "target_amount": ["Target amount must be greater than 0."]
}
```

---

## Ordering

List endpoint supports ordering parameter:

```bash
# Newest first (default)
GET /api/v1/goals/?ordering=-created_at

# Oldest first
GET /api/v1/goals/?ordering=created_at
```

---

## Features

✅ **User Isolation** — Only see/manage your own goals  
✅ **Partial Updates** — Update only the fields you want  
✅ **Status Control** — Pause/resume with state validation  
✅ **Auto Serializer Selection** — Right serializer per action  
✅ **Computed Fields** — total_contributed, progress_percent  
✅ **Ordered Results** — Newest goals first by default  
✅ **Pagination** — Built-in DRF pagination  

---

## Testing

Run all tests:
```bash
python manage.py test core_apps.goals.tests_viewset
```

Run specific test class:
```bash
python manage.py test core_apps.goals.tests_viewset.GoalViewSetTestCase
```

Run specific test:
```bash
python manage.py test core_apps.goals.tests_viewset.GoalViewSetTestCase.test_create_goal_with_all_fields
```

With verbose output:
```bash
python manage.py test core_apps.goals.tests_viewset -v 2
```

---

## Integration

### Add to Main URLs

In your `config/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other patterns
    path('api/v1/', include('core_apps.goals.urls')),
]
```

Or with a centralized API router:

```python
from rest_framework.routers import DefaultRouter
from core_apps.goals.views import GoalViewSet

api_router = DefaultRouter()
api_router.register('goals', GoalViewSet, basename='goals')

urlpatterns = [
    path('api/v1/', include(api_router.urls)),
]
```

---

## Response Format

### List Response
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    { goal object },
    { goal object }
  ]
}
```

### Detail Response
```json
{
  "id": "uuid",
  "name": "string",
  "target_amount": "decimal",
  "currency": "string",
  "status": "ACTIVE|PAUSED|COMPLETED|CANCELLED",
  "metadata": {},
  "total_contributed": "0.00",
  "progress_percent": 0,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "<your-token>"
headers = {"Authorization": f"Bearer {TOKEN}"}

# Create goal
response = requests.post(
    f"{BASE_URL}/goals/",
    json={
        "name": "Emergency Fund",
        "target_amount": "500000.00"
    },
    headers=headers
)
goal_id = response.json()['id']

# Pause goal
response = requests.post(
    f"{BASE_URL}/goals/{goal_id}/pause/",
    headers=headers
)
print(f"Status: {response.json()['status']}")

# Resume goal
response = requests.post(
    f"{BASE_URL}/goals/{goal_id}/resume/",
    headers=headers
)
print(f"Status: {response.json()['status']}")
```

---

## JavaScript/Fetch Example

```javascript
const token = "<your-token>";
const baseUrl = "http://localhost:8000/api/v1";

// Create goal
const createResponse = await fetch(`${baseUrl}/goals/`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    name: "Emergency Fund",
    target_amount: "500000.00"
  })
});
const goal = await createResponse.json();
const goalId = goal.id;

// Pause goal
const pauseResponse = await fetch(`${baseUrl}/goals/${goalId}/pause/`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` }
});
const paused = await pauseResponse.json();
console.log(`Status: ${paused.status}`);
```

---

## Postman Collection

```json
{
  "info": {
    "name": "Goals API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Create Goal",
      "request": {
        "method": "POST",
        "header": ["Authorization: Bearer {{token}}"],
        "url": "{{base_url}}/api/v1/goals/",
        "body": {
          "mode": "raw",
          "raw": "{\"name\": \"Emergency Fund\", \"target_amount\": \"500000.00\"}"
        }
      }
    },
    {
      "name": "List Goals",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/v1/goals/"
      }
    },
    {
      "name": "Pause Goal",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/v1/goals/{{goal_id}}/pause/"
      }
    },
    {
      "name": "Resume Goal",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/v1/goals/{{goal_id}}/resume/"
      }
    }
  ]
}
```

---

## File Structure

```
core_apps/goals/
├── models.py                # Goal model
├── serializers.py           # DRF serializers
├── permissions.py           # IsOwner permission
├── views.py                 # GoalViewSet
├── urls.py                  # URL router
├── tests_serializers.py     # Serializer tests
├── tests_viewset.py         # ViewSet tests (60+)
├── admin.py
├── apps.py
├── migrations/
└── __init__.py
```

---

## Test Coverage Summary

| Test Class | Tests | Coverage |
|-----------|-------|----------|
| GoalViewSetTestCase | 60+ | All endpoints, permissions, validation |

---

**Status:** ✅ Complete & Production Ready  
**Last Updated:** January 29, 2026  
**Test Count:** 60+ test cases  
**Documentation:** Full reference available
