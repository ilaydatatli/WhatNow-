from django.test import TestCase
from django.urls import reverse

from .models import User

PASSWORD = "kahve-fincani-42"


def signup_data(**overrides):
    data = {
        "username": "ayse_1",
        "email": "Ayse@Example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class AuthFlowTests(TestCase):
    def test_signup_logs_in_and_lowercases_email(self):
        response = self.client.post(reverse("accounts:signup"), signup_data())
        self.assertRedirects(response, "/")
        user = User.objects.get(username="ayse_1")
        self.assertEqual(user.email, "ayse@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_logout_then_login_with_email(self):
        self.client.post(reverse("accounts:signup"), signup_data())
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

        response = self.client.post(
            reverse("accounts:login"), {"username": "AYSE@example.com", "password": PASSWORD}
        )
        self.assertRedirects(response, "/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_or_username_rejected(self):
        User.objects.create_user(username="ayse_1", email="ayse@example.com", password=PASSWORD)

        response = self.client.post(reverse("accounts:signup"), signup_data(username="baska"))
        self.assertContains(response, "Bu e-posta adresiyle zaten bir hesap var.")

        response = self.client.post(
            reverse("accounts:signup"), signup_data(username="AYSE_1", email="yeni@example.com")
        )
        self.assertContains(response, "Bu kullanıcı adı zaten alınmış.")
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_username_rejected(self):
        for username in ("ab", "a" * 21, "ayşe", "with space"):
            response = self.client.post(reverse("accounts:signup"), signup_data(username=username))
            self.assertEqual(response.status_code, 200, username)
        self.assertEqual(User.objects.count(), 0)

    def test_navbar_shows_username(self):
        self.client.post(reverse("accounts:signup"), signup_data())
        response = self.client.get("/")
        self.assertContains(response, "ayse_1")
        self.assertContains(response, "Çıkış yap")
