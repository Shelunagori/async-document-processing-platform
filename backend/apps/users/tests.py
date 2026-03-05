from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserAuthAPITests(APITestCase):
    def test_register_creates_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "StrongPass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_token_issue_and_me_endpoint(self):
        user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123",
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        me_response = self.client.get(reverse("me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["username"], user.username)
