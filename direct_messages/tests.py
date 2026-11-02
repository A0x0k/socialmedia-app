from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .models import Conversation, Message


class ConversationModelTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')

    def test_get_or_create_for_users_new(self):
        conversation, created = Conversation.get_or_create_for_users(self.user1, self.user2)
        self.assertTrue(created)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())

    def test_get_or_create_for_users_existing(self):
        conv1, _ = Conversation.get_or_create_for_users(self.user1, self.user2)
        conv2, created = Conversation.get_or_create_for_users(self.user1, self.user2)
        self.assertFalse(created)
        self.assertEqual(conv1.id, conv2.id)

    def test_conversation_str(self):
        conversation, _ = Conversation.get_or_create_for_users(self.user1, self.user2)
        self.assertIn('user1', str(conversation))
        self.assertIn('user2', str(conversation))


class MessageModelTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.conversation, _ = Conversation.get_or_create_for_users(self.user1, self.user2)

    def test_message_creation(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Hello!'
        )
        self.assertEqual(message.content, 'Hello!')
        self.assertEqual(message.sender, self.user1)
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.timestamp)

    def test_message_str(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Test message content'
        )
        self.assertIn('user1', str(message))
        self.assertIn('Test message', str(message))

    def test_message_ordering(self):
        m1 = Message.objects.create(
            conversation=self.conversation, sender=self.user1, content='First'
        )
        m2 = Message.objects.create(
            conversation=self.conversation, sender=self.user1, content='Second'
        )
        messages = Message.objects.all()
        self.assertEqual(messages[0], m1)
        self.assertEqual(messages[1], m2)

    def test_message_clean_empty(self):
        message = Message(
            conversation=self.conversation,
            sender=self.user1,
            content='   '
        )
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_clean_too_long(self):
        message = Message(
            conversation=self.conversation,
            sender=self.user1,
            content='x' * 5001
        )
        with self.assertRaises(ValidationError):
            message.full_clean()


class InboxViewTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1', password='testpass123',
            email='user1@example.com'
        )
        self.user1.profile.email_verified = True
        self.user1.save()
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.client = Client()
        self.client.login(username='user1', password='testpass123')

    def test_inbox_view(self):
        response = self.client.get(reverse('direct_messages:inbox'), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_conversation_detail_view(self):
        Conversation.get_or_create_for_users(self.user1, self.user2)
        response = self.client.get(
            reverse('direct_messages:conversation_detail', args=['user2']), secure=True
        )
        self.assertEqual(response.status_code, 200)

    def test_conversation_detail_send_message(self):
        Conversation.get_or_create_for_users(self.user1, self.user2)
        response = self.client.post(
            reverse('direct_messages:conversation_detail', args=['user2']),
            {'content': 'Test message'},
            secure=True
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Message.objects.filter(conversation__participants=self.user1, content='Test message').exists()
        )
