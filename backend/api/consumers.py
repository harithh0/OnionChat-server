import asyncio
import json
import time
from datetime import datetime
from urllib.parse import unquote

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

# pretty much like views but for sockets


"""

TODO:
- if user already has a chatting session, it will not create a new one, check if they are in connected users
- check if users are firends, before chatting


"""


class ChatConsumer(AsyncWebsocketConsumer):

    connected_users = (
        set()
    )  # Class variable to store connected users sets cannot contain the same value

    async def connect(self):
        if self.scope["user"].is_authenticated:
            print("user:", self.scope["user"].username, "has joined")
            pass
        else:
            await self.close()

        # adds users ID to the connected user set
        self.connected_users.add(self.scope["user"].id)

        self.room_group_name = f"chat_{self.scope['url_route']['kwargs']['roomNum']}"  # creates varible for that object (user) that connected that stores the room group name

        # another varible the stores the room number from ws../chat/<num>
        self.room_number = self.scope["url_route"]["kwargs"]["roomNum"]

        # creates a specific group with the group_name such as chat_5 etc, so only the users in chat_5 can talk in that group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.channel_layer.group_send(
            self.room_group_name,  # send to only this group
            {
                "type": "user_connected",
                "message_type": "user_joined",
                "joined_user_id": self.scope["user"].id,
                "connected_username": self.scope["user"].username,
                # Send the list of connected users
                "connected_users": list(self.connected_users),
            },
        )

        await self.updateLastTimeOnline()
        await self.accept()

    @database_sync_to_async
    def saveMessageToDB(self, message, message_signature, message_iv):
        from api.models import AppUser, ChatRoom, Message

        chat_room = ChatRoom.objects.get(id=self.room_number)

        # create message object
        Message = Message.objects.create(
            chat_room=chat_room,
            sender=AppUser.objects.get(id=self.scope["user"].id),
            content=message,
            senderUsername=self.scope["user"].username,
            signature=message_signature,
            iv=message_iv,
        )

        chat_room.numOfMessages += 1
        chat_room.save()

    @database_sync_to_async
    def updateLastTimeOnline(self):
        from api.models import AppUser, ChatRoom

        chatroom_object = ChatRoom.objects.get(id=self.room_number)
        current_user = AppUser.objects.get(id=self.scope["user"].id)

        current_time = datetime.now()
        formatted_datetime = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        if chatroom_object.user1 == current_user:
            chatroom_object.user1_last_online = formatted_datetime
        elif chatroom_object.user2 == current_user:
            chatroom_object.user2_last_online = formatted_datetime

        chatroom_object.save()

    @database_sync_to_async
    def get_username(self, user_id):
        from api.models import AppUser, ChatRoom, Message

        return AppUser.objects.get(id=user_id).username

    @database_sync_to_async
    def upload_file(self, data):
        import os

        from api.models import AppUser, ChatRoom, Message
        from api.serializers import MessageSerializer
        from django.core.files.base import ContentFile

        current_user = AppUser.objects.get(id=self.scope["user"].id)
        chatroom_object = ChatRoom.objects.get(id=self.room_number)

        file_to_upload = data.get("file")  # base64 of file

        # hides file name but keeps extension
        _, file_extension = os.path.splitext(data.get("fileName"))
        newfile_name = f"file{file_extension}"

        file_to_upload = ContentFile(file_to_upload, name=newfile_name)

        signature_data = data.get("signature")
        iv_data = data.get("iv")

        to_save = {
            "chat_room": chatroom_object.id,
            "sender": current_user.id,
            "senderUsername": current_user.username,
            "fileData": file_to_upload,
            "isFile": True,
            "signature": signature_data,
            "iv": iv_data,
        }
        seralizer = MessageSerializer(data=to_save)
        if seralizer.is_valid():
            instance = seralizer.save()
            instance.fileName = str(os.path.basename(str(instance.fileData)))
            instance.save()
            # we cannot directly send the file data through websocket (inefficent, so what we will do is upload and save it, then send the url path to the clients, then they can use that to download the file)

            to_save["filePath"] = str(instance.fileData)
            # gets the updated filename after we make the file, as if 2 files have the same name django will add extra characters to make it unique
            to_save["fileName"] = instance.fileName

            # we dont need to send the full file data through the websocket
            to_save.pop("fileData")

            return True, to_save

        return False, {}

    async def receive(self, text_data):
        # takes regualr string dict and turns it into json | Must send DICT OR JSON message format | JSON-formatted string into a Python object
        try:
            text_data_json = json.loads(text_data)
        except Exception as e:
            print(e)
            await self.disconnect(close_code=1011)
            return
        if text_data_json["message_type"] == "user_typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_typing_message",
                    "message_type": "user_typing",
                    "sender_id": self.scope[
                        "user"
                    ].id,  # this refers to the ID fo the user who is sending the message | in the chat_message func, it would refer to the ID of the user who is recieveing the message
                },
            )
        elif text_data_json["message_type"] == "user_stopped_typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_stopped_typing_message",
                    "message_type": "user_stopped_typing",
                    "sender_id": self.scope[
                        "user"
                    ].id,  # this refers to the ID fo the user who is sending the message | in the chat_message func, it would refer to the ID of the user who is recieveing the message
                },
            )
        elif text_data_json["message_type"] == "new_message":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_type": "new_message",
                    "encrypted_message": text_data_json["encrypted_message"],
                    "message_signature": text_data_json["message_signature"],
                    "iv": text_data_json["iv"],
                    "sender_id": self.scope[
                        "user"
                    ].id,  # this refers to the ID fo the user who is sending the message | in the chat_message func, it would refer to the ID of the user who is recieveing the message
                },
            )

            await self.saveMessageToDB(
                text_data_json["encrypted_message"],
                text_data_json["message_signature"],
                text_data_json["iv"],
            )
        elif text_data_json["message_type"] == "new_upload":
            successful_upload, data = await self.upload_file(text_data_json)
            if successful_upload:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "new_upload",
                        "message_type": "new_upload",
                        "encrypted_file_path": data["filePath"],
                        "file_signature": data["signature"],
                        "file_name": data["fileName"],
                        "iv": data["iv"],
                        "sender_id": self.scope[
                            "user"
                        ].id,  # this refers to the ID fo the user who is sending the message | in the chat_message func, it would refer to the ID of the user who is recieveing the message
                    },
                )

    async def disconnect(self, close_code):

        self.connected_users.remove(self.scope["user"].id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "leave_chatroom",
                "message_type": "user_disconnected",
                "disconnected_user_id": self.scope["user"].id,
                "disconnected_username": self.scope["user"].username,
                "connected_users": list(self.connected_users),
            },
        )
        await self.updateLastTimeOnline()

        await self.close(close_code)

    # chatroom handlers:

    async def user_connected(self, data):
        # Handle the user_connected message here
        joined_user_id = data["joined_user_id"]
        connected_username = data["connected_username"]
        connected_users = data["connected_users"]

        # don't send it to the user sending the message | removed because when user connectes and a user is already in chatroom we need to send the connected users list so it can update online/offline status
        # if self.scope["user"].id != joined_user_id: ^^

        # opposite of json.loads | converts python object to json style string
        await self.send(
            text_data=json.dumps(
                {
                    "message_type": "user_joined",
                    "joined_user_id": joined_user_id,
                    "connected_username": connected_username,
                    "connected_users": connected_users,
                }
            )
        )
        # You can add additional logic here, such as notifying other users in the group

    # runs for every user in the room_group_name group when we call group_send and have this as the function ^
    async def chat_message(self, data):
        # Handle the user_connected message here
        encrypted_message = data["encrypted_message"]
        message_signature = data["message_signature"]
        iv = data["iv"]

        sender_id = data["sender_id"]  # this gives the correct sender user ID ^^^^
        print("encrypted message", encrypted_message)
        # don't send it to the user sending the message
        if self.scope["user"].id != sender_id:
            # opposite of json.loads | converts python object to json style string
            await self.send(
                text_data=json.dumps(
                    {
                        "message_type": "new_message",
                        "encrypted_message": encrypted_message,
                        "message_signature": message_signature,
                        "iv": iv,
                    }
                )
            )

    async def new_upload(self, data):
        encrypted_file_path = data["encrypted_file_path"]
        file_name = data["file_name"]
        file_signature = data["file_signature"]
        file_iv = data["iv"]
        senderUsername = await self.get_username(data["sender_id"])
        # this gives the correct sender user ID ^^^^

        await self.send(
            text_data=json.dumps(
                {
                    "message_type": "new_upload",
                    "file_name": file_name,
                    "encrypted_file_path": encrypted_file_path,
                    "file_signature": file_signature,
                    "file_iv": file_iv,
                    "senderUsername": senderUsername,
                }
            )
        )

    async def user_typing_message(self, data):
        sender_id = data["sender_id"]  # this gives the correct sender user ID ^^^^
        if self.scope["user"].id != sender_id:
            # opposite of json.loads | converts python object to json style string
            await self.send(
                text_data=json.dumps(
                    {
                        "message_type": "user_typing_message",
                    }
                )
            )

    async def user_stopped_typing_message(self, data):
        sender_id = data["sender_id"]  # this gives the correct sender user ID ^^^^
        if self.scope["user"].id != sender_id:
            # opposite of json.loads | converts python object to json style string
            await self.send(
                text_data=json.dumps(
                    {
                        "message_type": "user_stopped_typing_message",
                    }
                )
            )

    async def leave_chatroom(self, data):
        disconnected_user_id = data["disconnected_user_id"]
        disconnected_username = data["disconnected_username"]
        connected_users = data["connected_users"]

        # don't send it to the user sending the message
        if self.scope["user"].id != disconnected_user_id:
            # opposite of json.loads | converts python object to json style string
            await self.send(
                text_data=json.dumps(
                    {
                        "message_type": "user_disconnected",
                        "disconnected_user_id": disconnected_user_id,
                        "disconnected_username": disconnected_username,
                        "connected_users": connected_users,
                    }
                )
            )
