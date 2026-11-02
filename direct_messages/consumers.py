import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

from posts.utils import contains_profanity

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return

        # WebSocket rate limiting per user (Atomic)
        rate_key = f'ws_chat_rate_{self.user.id}'
        try:
            current = cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, 60)
            current = 1

        if current > 10:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()
        if not message_content:
            return

        if len(message_content) > 5000:
            await self.send(text_data=json.dumps({'error': 'Message too long'}))
            return

        if contains_profanity(message_content):
            await self.send(text_data=json.dumps({'error': 'Message contains inappropriate language'}))
            return

        # Per-message rate limiting per user (Atomic)
        msg_rate_key = f'ws_chat_msg_rate_{self.user.id}'
        try:
            current = cache.incr(msg_rate_key)
        except ValueError:
            cache.set(msg_rate_key, 1, 60)
            current = 1
        if current > 30:
            await self.send(text_data=json.dumps({'error': 'Message rate limit exceeded'}))
            return

        conversation = await database_sync_to_async(Conversation.objects.get)(id=self.conversation_id)
        is_participant = await database_sync_to_async(
            lambda: conversation.participants.filter(id=self.user.id).exists()
        )()
        if not is_participant:
            await self.send(text_data=json.dumps({'error': 'Not a participant'}))
            return

        message = await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user,
            content=message_content,
        )

        other_users = await database_sync_to_async(
            lambda: list(conversation.participants.exclude(id=self.user.id).values_list('id', flat=True))
        )()

        for other_id in other_users:
            await self.channel_layer.group_send(
                f'user_{other_id}',
                {
                    'type': 'chat_notification',
                    'conversation_id': self.conversation_id,
                    'sender': self.user.username,
                    'message': message_content,
                }
            )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'sender': self.user.username,
                'sender_id': self.user.id,
                'timestamp': message.timestamp.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp'],
        }))

    async def chat_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_notification',
            'conversation_id': event['conversation_id'],
            'sender': event['sender'],
            'message': event['message'],
        }))
