from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from rest_framework.authtoken.models import Token


class TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels 2
    """

    def __init__(self, inner):
        # Store the ASGI application we were passed
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Look up user from query string (you can also use headers)
        token_name = parse_qs(scope["query_string"].decode("utf8")).get("token")
        if not token_name:
            scope["user"] = AnonymousUser()
        else:
            # Use a sync_to_async function to interact with the ORM
            scope["user"] = await self.get_user(token_name[0])
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token_name):
        try:
            token = Token.objects.get(key=token_name)
            return token.user
        except Token.DoesNotExist:
            return AnonymousUser()
