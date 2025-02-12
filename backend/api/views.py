import json

from api.models import AppUser, ChatRoom, Friendship, Message
from api.serializers import (ChatRoomSerializer, FriendshipSerializer,
                             MessageSerializer, UserSerializer)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.contrib.auth import authenticate
from django.db.models import Q
from django.shortcuts import HttpResponse, get_object_or_404, render
from django.views.decorators.http import require_POST
from rest_framework import generics, status  # returns status codes 200, 404
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import \
    Token  # creates a token for the user
from rest_framework.decorators import (api_view, authentication_classes,
                                       permission_classes)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# from rest_framework_simplejwt.authentication import JWTAuthentication
# from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

# Create your views here.


@api_view(["POST"])
def test(request):
    data = request.data
    return Response({"working": str(data)}, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user.save()  # saves any changes
        # user.set_password(request.data["password"])  # sets password properly, hashes
        token = Token.objects.create(user=user)
        return Response(
            {"token": token.key, "user_data": serializer.data},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def login(request):
    try:
        username = request.data["username"]
        password = request.data["password"]
    except Exception as e:
        return Response(
            {"status": "error", "message": "Username or password not provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = get_object_or_404(AppUser, username=username)
    valid_password = user.check_password(password)

    # check for public key, if no, create one
    # do jwt

    if valid_password:
        token, _ = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(instance=user)
        return Response(
            {"token": token.key, "user": serializer.data}, status=status.HTTP_200_OK
        )
    else:  # auth failed
        return Response(
            {"Error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
def set_public(request):
    try:
        user_id = request.user.id
        public_pem = request.data["public_key"]
    except Exception as e:
        return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(AppUser, id=user_id)

    user.public_key = public_pem
    user.save()

    return Response("success", status=status.HTTP_200_OK)


@api_view(["POST"])
def get_public(request):
    try:
        user_id = request.user.id
        # ONLY IF  user is in users, friend list or pending for extra sec
        user = get_object_or_404(AppUser, username=request.data.get("get_username"))
        users_public_key = user.public_key
        return Response(
            {"public_key": str(users_public_key)}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def chatroom_exists(user1, user2):
    chatroom = ChatRoom.objects.filter(
        Q(user1=user1, user2=user2) | Q(user1=user2, user2=user1)
    ).first()
    if chatroom:
        return chatroom.id
    else:
        return None


@api_view(["POST"])
def handleChat(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    user2 = get_object_or_404(AppUser, id=request.data["user_to_message"])

    chatroom_id = chatroom_exists(loggedInUser, user2)
    if chatroom_id:
        return Response({"chatroom_id": chatroom_id}, status=status.HTTP_200_OK)
    else:
        chatroom = ChatRoom.objects.create(user1=loggedInUser, user2=user2)
        return Response({"chatroom_id": chatroom.id}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def get_messages_from_db(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    chatroom = get_object_or_404(ChatRoom, id=request.data.get("chatroom_id"))
    all_messages = Message.objects.filter(chat_room=chatroom)

    serializer = MessageSerializer(instance=all_messages, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_pending_friends(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    pending_friends = Friendship.objects.filter(to_user=loggedInUser, status="pending")
    serializer = FriendshipSerializer(instance=pending_friends, many=True)
    print(pending_friends, loggedInUser.username)
    return Response(serializer.data, status=status.HTTP_200_OK)


def users_are_friends(user1, user2):
    return Friendship.objects.filter(
        (Q(from_user=user1) & Q(to_user=user2))
        | (Q(from_user=user2) & Q(to_user=user1)),
        status="accepted",
    ).exists()


@api_view(["POST"])
def send_friend_request(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    send_request_to = get_object_or_404(
        AppUser, username=request.data.get("send_request_to")
    )

    if loggedInUser == send_friend_request:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if Friendship.objects.filter(
        from_user=loggedInUser, to_user=send_request_to, status="pending"
    ).exists():
        return Response(
            {"detail": "Friend request already sent"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if Friendship.objects.filter(
        from_user=loggedInUser, to_user=send_request_to, status="rejected"
    ).exists() or users_are_friends(loggedInUser, send_request_to):
        return Response(
            {"detail": "Either already friends or rejected"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    else:
        Friendship.objects.create(from_user=loggedInUser, to_user=send_request_to)
        return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
def accept_friend_request(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    user_to_accept = get_object_or_404(AppUser, username=request.data["user_to_accept"])

    friendship_id = Friendship.objects.filter(
        from_user=user_to_accept, to_user=loggedInUser
    ).values("id")

    if friendship_id.exists():
        friendship_object = get_object_or_404(Friendship, id=friendship_id[0].get("id"))
        friendship_object.status = "accepted"
        friendship_object.save()
        return Response(status=status.HTTP_200_OK)

    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_friends(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)

    accepted_friends = Friendship.objects.filter(
        Q(to_user=loggedInUser, status="accepted")
        | Q(from_user=loggedInUser, status="accepted")
    )
    serializer = FriendshipSerializer(instance=accepted_friends, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def reject_friend_request(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    user_to_reject = get_object_or_404(AppUser, username=request.data["user_to_reject"])

    friendship_id = Friendship.objects.filter(
        from_user=user_to_reject, to_user=loggedInUser
    ).values("id")

    if friendship_id.exists():
        friendship_object = get_object_or_404(Friendship, id=friendship_id[0].get("id"))
        friendship_object.status = "rejected"
        friendship_object.save()
        return Response(status=status.HTTP_200_OK)

    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def verify_token(request):
    return Response(status=status.HTTP_200_OK)


# returns room of 2 users or creates one
def find_or_create_chatroom(user1_input, user2_input):
    chatroom = ChatRoom.objects.filter(
        Q(user1=user1_input, user2=user2_input)
        | Q(user2=user1_input, user1=user2_input)
    ).first()

    if chatroom:
        return chatroom.id
    else:
        chatroom = ChatRoom.objects.create(user1=user1_input, user2=user2_input)
        return chatroom.id


@api_view(["POST"])
def handle_chatroom(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    user2 = get_object_or_404(AppUser, username=request.data.get("user_to_chat"))

    chatroom_id = find_or_create_chatroom(loggedInUser, user2)

    return Response({"chatroom_id": chatroom_id}, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_chatrooms(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)

    chatrooms = ChatRoom.objects.filter(Q(user1=loggedInUser) | Q(user2=loggedInUser))
    serializer = ChatRoomSerializer(chatrooms, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@require_POST
@api_view(["POST"])
def set_SK(request):
    try:
        loggedInUser = get_object_or_404(AppUser, id=request.user.id)
        # since the user who is hitting this api endpoint is the one who is accepting the friend_request so they would be the to_user
        user_2 = get_object_or_404(AppUser, username=request.data.get("from_user"))
        friendship_object = get_object_or_404(
            Friendship, id=request.data.get("friend_object").get("id")
        )
        friendship_object.from_user_SK = request.data.get("friend_SK")
        friendship_object.to_user_SK = request.data.get("current_user_SK")
        friendship_object.save()
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    print(request.data)
    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
def get_user_SK(request):
    try:
        loggedInUser = get_object_or_404(AppUser, id=request.user.id)
        user_2 = get_object_or_404(
            AppUser, username=request.data.get("friend_username")
        )
        friend_object = Friendship.objects.filter(
            Q(from_user=user_2.id, to_user=loggedInUser.id)
            | Q(from_user=loggedInUser.id, to_user=user_2.id)
        ).first()

        # we are trying to get the id of the other person that is not us in the firend group
        if friend_object:
            if friend_object.from_user.id == loggedInUser.id:
                sk = friend_object.from_user_SK
            elif friend_object.to_user.id == loggedInUser.id:
                sk = friend_object.to_user_SK

            print(sk)
            return Response({"sk": sk}, status=status.HTTP_200_OK)
        else:
            print("here")
            return Response(status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        print(request.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def get_users_last_online(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    user_to_get = get_object_or_404(AppUser, username=request.data.get("user_to_get"))
    chatroom_object = get_object_or_404(ChatRoom, id=request.data.get("chatroom_id"))

    if not chatroom_object:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if chatroom_object.user1 == loggedInUser:
        # we need to get user2
        return Response(
            {"last_online": chatroom_object.user2_last_online},
            status=status.HTTP_200_OK,
        )
    elif chatroom_object.user2 == loggedInUser:
        # we need to get user1
        return Response(
            {"last_online": chatroom_object.user1_last_online},
            status=status.HTTP_200_OK,
        )

    return Response(status=status.HTTP_400_BAD_REQUEST)


import os

from django.core.files.base import ContentFile


@api_view(["POST"])
def upload_file(request):
    loggedInUser = get_object_or_404(AppUser, id=request.user.id)
    chatroom_object = get_object_or_404(ChatRoom, id=request.data.get("chatroom_id"))

    # check if user is in that chatroom first !!! and that they are friends
    if not (
        chatroom_object.user1 == loggedInUser or chatroom_object.user2 == loggedInUser
    ):
        return Response(
            {"detail": "User not in chatroom"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not chatroom_object:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    try:
        file_to_upload = request.FILES["file"]

        # hides file name but keeps extension
        _, file_extension = os.path.splitext(file_to_upload.name)
        newfile_name = f"file.{file_extension}"

        file_content = file_to_upload.read()
        file_to_upload = ContentFile(file_content, name=newfile_name)

        signature_data = request.data.get("signature")
        iv_data = request.data.get("iv")

        data = {
            "chat_room": chatroom_object.id,
            "sender": loggedInUser.id,
            "senderUsername": loggedInUser.username,
            "fileData": file_to_upload,
            "isFile": True,
            "signature": signature_data,
            "iv": iv_data,
        }
        seralizer = MessageSerializer(data=data)
        if seralizer.is_valid():
            seralizer.save()
            return Response(status=status.HTTP_201_CREATED)

        print(seralizer.errors)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)
