import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Message, Conversation, Notification
from core.services import NotificationService

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_username = self.scope['url_route']['kwargs']['username']
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Get or create conversation
        self.other_user = await self.get_user(self.other_username)
        self.conversation = await self.get_or_create_conversation(self.user, self.other_user)
        
        # Join room group
        self.room_group_name = f'chat_{self.conversation.id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mark messages as read
        await self.mark_messages_as_read()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        
        # Save message to database
        message = await self.save_message(message_content)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'sender_id': message.sender.id,
                    'created_at': message.created_at.isoformat(),
                }
            }
        )
        
        # Create notification
        await self.create_notification(message)
    
    async def chat_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
    
    @database_sync_to_async
    def get_user(self, username):
        return User.objects.get(username=username)
    
    @database_sync_to_async
    def get_or_create_conversation(self, user1, user2):
        return Conversation.get_or_create_conversation(user1, user2)
    
    @database_sync_to_async
    def save_message(self, content):
        message = Message.objects.create(
            sender=self.user,
            recipient=self.other_user,
            content=content,
            conversation=self.conversation
        )
        
        self.conversation.last_message = message
        self.conversation.save()
        
        return message
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        Message.objects.filter(
            conversation=self.conversation,
            recipient=self.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    @database_sync_to_async
    def create_notification(self, message):
        NotificationService.create_message_notification(
            actor=self.user,
            recipient=self.other_user,
            message=message
        )


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.room_group_name = f'notifications_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def send_notification(self, event):
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'notification': notification
        }))