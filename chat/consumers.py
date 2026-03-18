import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from uuid import UUID


class UserStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "user_status"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        users = await self.get_all_users()
        await self.send(
            text_data=json.dumps(
                {"type": "user_list", "users": users}, default=self.uuid_to_str
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def user_status_update(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "status_update", "data": event["data"]},
                default=self.uuid_to_str,
            )
        )

    @database_sync_to_async
    def get_all_users(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        current_user = self.scope["user"]
        users_qs = (
            User.objects.filter(user_type=User.UserType.USER)
            .exclude(id=current_user.id)
            .values("uid", "username", "is_online")
        )
        return list(users_qs)

    def uuid_to_str(obj):
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.other_user_uid = self.scope["url_route"]["kwargs"]["uid"]
        self.room_name = self.generate_room_name(
            str(self.user.uid), self.other_user_uid
        )
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        chat_history = await self.fetch_chat_history()
        await self.send(
            text_data=json.dumps({"type": "history", "messages": chat_history})
        )
        await self.mark_chat_history_as_read()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type", "message")
        if msg_type == "delete":
            message_id = data.get("message_id")
            if not message_id:
                return

            deleted = await self.delete_message(message_id)
            if deleted:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "delete_event", "message_id": message_id},
                )
            return

        message_text = data.get("message", "").strip()
        if not message_text:
            return

        receiver = await self.get_user_by_uid(self.other_user_uid)
        message = await self.create_chat_message(self.user, receiver, message_text)

        # Broadcast the new message to the chat group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message_event",
                "message_id": message.id,
                "message": message_text,
                "sender_uid": str(self.user.uid),
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
            },
        )

    async def chat_message_event(self, event):
        is_incoming = event["sender_uid"] != str(self.user.uid)

        if is_incoming:
            await self.mark_incoming_message_as_read(event["sender_uid"])
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "read_receipt_event", "read_by_uid": str(self.user.uid)},
            )

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "content": event["message"],
                    "sender_uid": event["sender_uid"],
                    "timestamp": event["timestamp"],
                    "is_read": event["is_read"],
                }
            )
        )

    async def mark_chat_history_as_read(self):
        updated_count = await self.mark_all_messages_read()
        if updated_count:
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "read_receipt_event", "read_by_uid": str(self.user.uid)},
            )

    async def mark_incoming_message_as_read(self, sender_uid):
        await self.mark_message_read(sender_uid)

    async def read_receipt_event(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "read_receipt", "read_by_uid": event["read_by_uid"]}
            )
        )

    async def delete_event(self, event):
        await self.send(
            text_data=json.dumps({"type": "deleted", "message_id": event["message_id"]})
        )

    def generate_room_name(self, uid1: str, uid2: str) -> str:
        return "_".join(sorted([uid1, uid2]))

    @database_sync_to_async
    def get_user_by_uid(self, uid):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.get(uid=uid)

    @database_sync_to_async
    def create_chat_message(self, sender, receiver, content):
        from .models import Message

        return Message.objects.create(sender=sender, receiver=receiver, content=content)

    @database_sync_to_async
    def fetch_chat_history(self):
        from django.contrib.auth import get_user_model
        from .models import Message

        other_user = get_user_model().objects.get(uid=self.other_user_uid)
        messages = (
            Message.objects.select_related("sender", "receiver")
            .filter(
                sender__in=[self.user, other_user],
                receiver__in=[self.user, other_user],
            )
            .order_by("timestamp")
        )

        return [
            {
                "message_id": msg.id,
                "sender_uid": str(msg.sender.uid),
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "is_read": msg.is_read,
            }
            for msg in messages
        ]

    @database_sync_to_async
    def mark_all_messages_read(self):
        from django.contrib.auth import get_user_model
        from .models import Message

        other_user = get_user_model().objects.get(uid=self.other_user_uid)
        updated_count = Message.objects.filter(
            sender=other_user, receiver=self.user, is_read=False
        ).update(is_read=True)
        return updated_count

    @database_sync_to_async
    def mark_message_read(self, sender_uid):
        from django.contrib.auth import get_user_model
        from .models import Message

        sender = get_user_model().objects.get(uid=sender_uid)
        Message.objects.filter(sender=sender, receiver=self.user, is_read=False).update(
            is_read=True
        )

    @database_sync_to_async
    def delete_message(self, message_id):
        from .models import Message

        try:
            message = Message.objects.get(id=message_id, sender=self.user)
            message.delete()
            return True
        except Message.DoesNotExist:
            return False
