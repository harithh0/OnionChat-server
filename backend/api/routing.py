from django.urls import path

from . import consumers  # your WebSocket consumer

url_patterns = [path("ws/chat/<int:roomNum>/", consumers.ChatConsumer.as_asgi())]
