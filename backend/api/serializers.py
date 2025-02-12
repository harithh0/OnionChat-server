import os

from api.models import AppUser, ChatRoom, Friendship, Message
from django.contrib.auth.hashers import make_password
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    # the data that will be returned
    class Meta:
        model = AppUser
        fields = [
            "id",
            "username",
            "password",
            "public_key",
        ]
        # will not include the password when returning "serializer.data"
        extra_kwargs = {
            "password": {"write_only": True},
            "public_key": {"required": False},
        }

    def validate_username(self, value):
        if "@" in value:
            raise serializers.ValidationError("Username cannot contain '@' character")
        if len(value) < 6:
            raise serializers.ValidationError(
                "Username must be at least 6 characters long"
            )
        if AppUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        if " " in value:
            raise serializers.ValidationError("Username cannot contain spaces")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )
        elif len(value) > 255:
            raise serializers.ValidationError(
                "Password must cannot be greater than 255 characters long"
            )
        return make_password(value)  # sets password properly, hashes

    def validate(self, data):
        if data["password"] == data.get("username"):
            raise serializers.ValidationError("Password cannot match username")
        return data


class ChatRoomSerializer(serializers.ModelSerializer):
    username_1 = serializers.SerializerMethodField()
    username_2 = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "user1",
            "user2",
            "username_1",
            "username_2",
            "last_message_time",
            "numOfMessages",
        ]

        # sets the username fields

    def get_username_1(self, obj):
        return obj.user1.username if obj.user1 else None

    def get_username_2(self, obj):
        return obj.user2.username if obj.user2 else None


class MessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Message
        fields = [
            "id",
            "chat_room",
            "sender",
            "senderUsername",
            "content",
            "fileData",
            "isFile",
            "fileName",
            "signature",
            "iv",
            "timestamp",
        ]


class FriendshipSerializer(serializers.ModelSerializer):
    from_user_name = serializers.SerializerMethodField()
    to_user_name = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = [
            "id",
            "from_user",
            "to_user",
            "from_user_name",
            "to_user_name",
            "status",
            "created_at",
        ]

    # sets the username fields
    def get_from_user_name(self, obj):
        return obj.from_user.username if obj.from_user else None

    def get_to_user_name(self, obj):
        return obj.to_user.username if obj.to_user else None
