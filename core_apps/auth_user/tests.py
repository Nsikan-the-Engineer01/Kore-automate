from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthEndpointsTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("auth:register")
        self.login_url = reverse("auth:login")
        self.token_refresh_url = reverse("auth:token_refresh")
        self.me_url = reverse("auth:me")
        self.logout_url = reverse("auth:logout")

        self.user_email = "user@example.com"
        self.user_password = "StrongPassw0rd!"
        self.user = User.objects.create_user(
            username=self.user_email,
            email=self.user_email,
            password=self.user_password,
        )

    def test_register_creates_user(self):
        payload = {
            "email": "newuser@example.com",
            "password": "AnotherStr0ngPass!",
            "confirm_password": "AnotherStr0ngPass!",
        }

        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], payload["email"])
        self.assertTrue(
            User.objects.filter(email__iexact=payload["email"]).exists()
        )

    def test_login_returns_tokens(self):
        payload = {"email": self.user_email, "password": self.user_password}
        response = self.client.post(self.login_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])

    def test_token_refresh_returns_new_access(self):
        # First log in to get a refresh token
        login_response = self.client.post(
            self.login_url,
            {"email": self.user_email, "password": self.user_password},
            format="json",
        )
        refresh = login_response.data["data"]["refresh"]

        response = self.client.post(
            self.token_refresh_url, {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])

    def test_me_returns_authenticated_user_profile(self):
        # Authenticate with access token
        login_response = self.client.post(
            self.login_url,
            {"email": self.user_email, "password": self.user_password},
            format="json",
        )
        access = login_response.data["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], self.user_email)

    def test_logout_blacklists_refresh_or_instructs_client(self):
        # Obtain a refresh token first
        login_response = self.client.post(
            self.login_url,
            {"email": self.user_email, "password": self.user_password},
            format="json",
        )
        refresh = login_response.data["data"]["refresh"]

        response = self.client.post(
            self.logout_url, {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("detail", response.data["data"])

