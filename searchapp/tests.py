from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from posts.models import Post, Hashtag


class SearchViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            email='test@example.com'
        )
        self.user.profile.email_verified = True
        self.user.save()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        self.post = Post.objects.create(author=self.user, content='Test post content')
        hashtag = Hashtag.objects.create(name='testtag')
        self.post.hashtags.add(hashtag)

    def test_search_empty_query(self):
        response = self.client.get(reverse('searchapp:search'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نتائج')

    def test_search_posts(self):
        response = self.client.get(
            reverse('searchapp:search'),
            {'q': 'Test post', 'type': 'posts'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)

    def test_search_users(self):
        response = self.client.get(
            reverse('searchapp:search'),
            {'q': 'testuser', 'type': 'users'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)

    def test_advanced_search(self):
        response = self.client.get(
            reverse('searchapp:advanced_search'),
            {'q': 'Test'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)

    def test_advanced_search_with_date_range(self):
        response = self.client.get(
            reverse('searchapp:advanced_search'),
            {'q': 'Test', 'date_from': '2024-01-01', 'date_to': '2030-12-31'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)

    def test_search_no_results(self):
        response = self.client.get(
            reverse('searchapp:search'),
            {'q': 'nonexistentcontent'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)

    def test_advanced_search_no_results(self):
        response = self.client.get(
            reverse('searchapp:advanced_search'),
            {'q': 'nonexistent', 'author': 'nobody'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)
