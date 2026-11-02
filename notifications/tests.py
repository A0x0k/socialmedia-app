from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Notification
from .utils import send_notification


class NotificationModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')

    def test_notification_creation(self):
        notification = Notification.objects.create(
            user=self.user,
            message='Test notification',
            notification_type='general'
        )
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.message, 'Test notification')
        self.assertFalse(notification.is_read)

    def test_notification_defaults(self):
        notification = Notification.objects.create(
            user=self.user,
            message='Test notification'
        )
        self.assertEqual(notification.notification_type, 'general')
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)

    def test_notification_str(self):
        notification = Notification.objects.create(
            user=self.user,
            message='Test notification message'
        )
        self.assertIn('testuser', str(notification))
        self.assertIn('Test notification', str(notification))

    def test_notification_ordering(self):
        n1 = Notification.objects.create(user=self.user, message='First')
        n2 = Notification.objects.create(user=self.user, message='Second')
        notifications = Notification.objects.all()
        self.assertEqual(notifications[0], n2)
        self.assertEqual(notifications[1], n1)


class NotificationUtilTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')

    def test_send_notification_creates_record(self):
        notification = send_notification(
            self.user,
            'Test notification message',
            'general'
        )
        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notification.user, self.user)

    def test_send_notification_with_related_user(self):
        notification = send_notification(
            self.user,
            'Follow notification',
            'follow',
            related_user=self.other_user
        )
        self.assertEqual(notification.related_user, self.other_user)
        self.assertEqual(notification.notification_type, 'follow')


class NotificationViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.user.profile.email_verified = True
        self.user.save()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        Notification.objects.create(user=self.user, message='Test notif 1')
        Notification.objects.create(user=self.user, message='Test notif 2', is_read=True)

    def test_notification_list_view(self):
        response = self.client.get(reverse('notifications:notification_list'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test notif 1')

    def test_mark_notification_read(self):
        notification = Notification.objects.filter(user=self.user, is_read=False).first()
        response = self.client.post(
            reverse('notifications:mark_read', args=[notification.id]), secure=True
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_unread_count(self):
        response = self.client.get(reverse('notifications:unread_count'), secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
