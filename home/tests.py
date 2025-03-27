from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

class HomePageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'QA Portal')
        self.assertEqual(response.data['message'], 'Welcome to the Quality Assurance Portal')
