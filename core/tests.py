from django.test import TestCase

class UserAuthenticationTest(TestCase):
    def test_user_registration(self):
        response = self.client.post('/register/', {'username': 'testuser', 'password': 'securepass'})
        self.assertEqual(response.status_code, 200)


# Create your tests here.
