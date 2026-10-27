from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.dashboard_url = reverse('accounts:dashboard')

    def test_user_registration(self):
        """Test student registration and initial role assignment."""
        response = self.client.post(self.register_url, {
            'username': 'new_student',
            'first_name': 'New',
            'last_name': 'Student',
            'email': 'new.student@campus.edu',
            'student_id': 'CS-2025-099',
            'phone_number': '+1-555-8888',
            'department': 'Computer Science',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='new_student')
        self.assertEqual(user.role, 'STUDENT')
        self.assertEqual(user.email, 'new.student@campus.edu')
        self.assertTrue(user.check_password('SecurePassword123!'))

    def test_user_authentication_and_redirect(self):
        """Test authentication flow."""
        user = User.objects.create_user(username='testuser', password='Password123!', email='t@campus.edu')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

    def test_unauthenticated_dashboard_redirect(self):
        """Unauthenticated user accessing dashboard is redirected to login."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)
