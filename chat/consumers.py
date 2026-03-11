import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Message
from core.services import NotificationService

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("=" * 60)
        print("🔌 WEBSOCKET CONNECTION ATTEMPT")
        
        self.other_username = self.scope['url_route']['kwargs']['username']
        self.user = self.scope['user']
        
        print(f"📝 Path: {self.scope['path']}")
        print(f"👤 User: {self.user}")
        print(f"🔑 Authenticated: {self.user.is_authenticated}")
        print(f"🎯 Target user: {self.other_username}")
        
        # Check authentication
        if not self.user.is_authenticated:
            print("❌ User not authenticated, closing connection")
            await self.close(code=4401)  # 4401 = Unauthorized
            return
        
        # Check if the other user exists
        other_user = await self.get_user(self.other_username)
        if not other_user:
            print(f"❌ User '{self.other_username}' does not exist")
            await self.close(code=4404)  # 4404 = Not Found
            return
        
        # Create room name from both usernames (sorted to be unique)
        usernames = sorted([self.user.username, self.other_username])
        self.room_group_name = f'chat_{usernames[0]}_{usernames[1]}'
        
        print(f"✅ Room group: {self.room_group_name}")
        
        # Join room group
        try:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            print(f"✅ Joined room group: {self.room_group_name}")
        except Exception as e:
            print(f"❌ Failed to join room group: {e}")
            await self.close()
            return
        
        # Accept the connection
        await self.accept()
        print("✅ WebSocket connection accepted")
        
        # Mark previous messages as read
        try:
            await self.mark_messages_as_read()
            print("✅ Marked messages as read")
        except Exception as e:
            print(f"⚠️ Failed to mark messages as read: {e}")
        
        print("=" * 60)
    
    async def disconnect(self, close_code):
        print(f"🔌 WebSocket disconnected with code: {close_code}")
        
        # Leave room group
        if hasattr(self, 'room_group_name'):
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                print(f"✅ Left room group: {self.room_group_name}")
            except Exception as e:
                print(f"❌ Failed to leave room group: {e}")
    
    async def receive(self, text_data):
        print(f"📨 Received message: {text_data}")
        
        try:
            text_data_json = json.loads(text_data)
            message_content = text_data_json.get('message', '')
            
            if not message_content:
                print("⚠️ Empty message received")
                return
            
            print(f"💬 Message content: {message_content}")
            
            # Get other user
            other_user = await self.get_user(self.other_username)
            if not other_user:
                print(f"❌ Other user '{self.other_username}' not found")
                return
            
            # Save message to database
            message = await self.save_message(other_user, message_content)
            print(f"✅ Message saved (ID: {message.id})")
            
            # Prepare message data
            message_data = {
                'id': message.id,
                'content': message.content,
                'sender': message.sender.username,
                'sender_id': message.sender.id,
                'created_at': message.created_at.isoformat(),
            }
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
            print(f"✅ Message sent to group: {self.room_group_name}")
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON received")
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    async def chat_message(self, event):
        message = event['message']
        print(f"📤 Sending message to WebSocket: {message}")
        
        # Send message to WebSocket
        try:
            await self.send(text_data=json.dumps({
                'message': message
            }))
            print("✅ Message sent to WebSocket client")
        except Exception as e:
            print(f"❌ Failed to send message to client: {e}")
    
    @database_sync_to_async
    def get_user(self, username):
        try:
            user = User.objects.get(username=username)
            print(f"✅ Found user: {user.username}")
            return user
        except User.DoesNotExist:
            print(f"❌ User not found: {username}")
            return None
    
    @database_sync_to_async
    def save_message(self, recipient, content):
        try:
            message = Message.objects.create(
                sender=self.user,
                recipient=recipient,
                content=content
            )
            print(f"✅ Message saved: {message.id}")
            return message
        except Exception as e:
            print(f"❌ Failed to save message: {e}")
            raise
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        try:
            other_user = User.objects.get(username=self.other_username)
            updated = Message.objects.filter(
                sender=other_user,
                recipient=self.user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            print(f"✅ Marked {updated} messages as read")
            return updated
        except User.DoesNotExist:
            print(f"❌ Cannot mark messages as read: user {self.other_username} not found")
            return 0
        except Exception as e:
            print(f"❌ Failed to mark messages as read: {e}")
            return 0


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("=" * 60)
        print("🔔 NOTIFICATION WEBSOCKET CONNECTION ATTEMPT")
        
        self.user = self.scope['user']
        
        print(f"👤 User: {self.user}")
        print(f"🔑 Authenticated: {self.user.is_authenticated}")
        
        if not self.user.is_authenticated:
            print("❌ User not authenticated, closing connection")
            await self.close(code=4401)
            return
        
        self.room_group_name = f'notifications_{self.user.id}'
        print(f"✅ Notification room: {self.room_group_name}")
        
        try:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            print(f"✅ Joined notification group")
        except Exception as e:
            print(f"❌ Failed to join notification group: {e}")
            await self.close()
            return
        
        await self.accept()
        print("✅ Notification WebSocket accepted")
        print("=" * 60)
    
    async def disconnect(self, close_code):
        print(f"🔔 Notification WebSocket disconnected with code: {close_code}")
        
        if hasattr(self, 'room_group_name'):
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                print(f"✅ Left notification group")
            except Exception as e:
                print(f"❌ Failed to leave notification group: {e}")
    
    async def receive(self, text_data):
        print(f"📨 Notification received: {text_data}")
        # You can handle notification-specific messages here if needed
        pass
    
    async def send_notification(self, event):
        notification = event['notification']
        print(f"📤 Sending notification to WebSocket: {notification}")
        
        try:
            await self.send(text_data=json.dumps({
                'notification': notification
            }))
            print("✅ Notification sent to client")
        except Exception as e:
            print(f"❌ Failed to send notification: {e}")