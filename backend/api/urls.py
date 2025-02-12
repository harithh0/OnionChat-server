from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path("test/", views.test, name="test"),
    re_path("register/", views.register, name="register"),
    re_path("login/", views.login, name="login"),
    re_path("set_public/", views.set_public, name="set_public"),
    re_path("get_public/", views.get_public, name="get_public"),
    re_path("handleChat/", views.handleChat, name="handleChat"),
    re_path(
        "get_pending_friends/", views.get_pending_friends, name="get_pending_friends"
    ),
    re_path(
        "send_friend_request/", views.send_friend_request, name="send_friend_request"
    ),
    re_path(
        "accept_friend_request/",
        views.accept_friend_request,
        name="accept_friend_request",
    ),
    re_path("get_friends/", views.get_friends, name="get_friends"),
    re_path(
        "reject_friend_request/",
        views.reject_friend_request,
        name="reject_friend_request",
    ),
    re_path("verify_token", views.verify_token, name="verify_token"),
    re_path(
        "handle_chatroom",
        views.handle_chatroom,
        name="handle_chatroom",
    ),
    re_path("get_chatrooms", views.get_chatrooms, name="get_chatrooms"),
    re_path(
        "get_messages_from_db", views.get_messages_from_db, name="get_messages_from_db"
    ),
    re_path("set_SK", views.set_SK, name="set_SK"),
    re_path("get_user_SK", views.get_user_SK, name="get_user_SK"),
    re_path(
        "get_users_last_online",
        views.get_users_last_online,
        name="get_users_last_online",
    ),
    re_path("upload_file", views.upload_file, name="upload_file"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
