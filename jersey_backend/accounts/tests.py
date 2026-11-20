from django.test import TestCase

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class AuthenticationAPITest(APITestCase):

    def setUp(self):
        self.register_url = "/api/accounts/register/"
        self.login_url = "/api/accounts/login/"
        self.profile_url = "/api/accounts/me/"

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            role="customer"
        )

    def test_user_registration(self):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPassword123",
            "phone": "01700000000"
        }

        response = self.client.post(
            self.register_url,
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertTrue(
            User.objects.filter(
                email="newuser@example.com"
            ).exists()
        )

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            self.register_url,
            {
                "username": "weakpassworduser",
                "email": "weak@example.com",
                "password": "password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_user_login(self):
        data = {
            "email": "test@example.com",
            "password": "TestPassword123"
        }

        response = self.client.post(
            self.login_url,
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_profile_requires_authentication(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_authenticated_user_can_view_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["email"],
            "test@example.com"
        )