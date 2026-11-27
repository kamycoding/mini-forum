from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.registration_url = reverse("registration")
        self.login_url = reverse("login")
        self.data = {
            "username": "demo_reader",
            "email": "reader@example.com",
            "password": "Tapestry!Seahorse89",
            "repeated_password": "Tapestry!Seahorse89",
        }

    def assert_invalid_registration(self, field, **changes):
        count = User.objects.count()
        response = self.client.post(
            self.registration_url, {**self.data, **changes}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(field, response.data)
        self.assertEqual(User.objects.count(), count)

    def test_registration_creates_account(self):
        response = self.client.post(self.registration_url, {
            **self.data, "is_staff": True, "is_superuser": True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username=self.data["username"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(response.data, {
            "id": user.pk,
            "username": self.data["username"],
            "email": self.data["email"],
        })

    def test_password_is_hashed(self):
        self.client.post(self.registration_url, self.data)
        user = User.objects.get(username=self.data["username"])
        self.assertNotEqual(user.password, self.data["password"])
        self.assertTrue(user.check_password(self.data["password"]))

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username=self.data["username"])
        self.assert_invalid_registration("username")

    def test_normalized_duplicate_username_is_rejected(self):
        """Reject a spelling that normalizes to an existing username."""
        User.objects.create_user(username="reader")
        self.assert_invalid_registration("username", username="ｒｅａｄｅｒ")

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="first_reader", email="Reader@example.com"
        )
        self.assert_invalid_registration("email")

    def test_invalid_email_is_rejected(self):
        self.assert_invalid_registration("email", email="invalid-email")

    def test_email_is_required(self):
        self.data.pop("email")
        self.assert_invalid_registration("email")

    def test_mismatched_passwords_are_rejected(self):
        self.assert_invalid_registration(
            "repeated_password", repeated_password="different"
        )

    def test_weak_password_is_rejected(self):
        self.assert_invalid_registration(
            "password", password="12345678", repeated_password="12345678"
        )

    def test_login_returns_token(self):
        self.client.post(self.registration_url, self.data)
        credentials = {key: self.data[key] for key in ("username", "password")}
        response = self.client.post(self.login_url, credentials)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = Token.objects.get(user__username=self.data["username"])
        self.assertEqual(response.data, {"token": token.key})
        repeated_login = self.client.post(self.login_url, credentials)
        self.assertEqual(repeated_login.data, response.data)

    def test_invalid_login_is_rejected(self):
        User.objects.create_user(
            username=self.data["username"], password=self.data["password"]
        )
        response = self.client.post(self.login_url, {
            "username": self.data["username"],
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertFalse(Token.objects.exists())
