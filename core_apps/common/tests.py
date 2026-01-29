from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    def test_health_endpoint_returns_ok(self):
        url = reverse("common:health")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
