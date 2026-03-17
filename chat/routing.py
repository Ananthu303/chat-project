from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/users/$", consumers.UserStatusConsumer.as_asgi()),
    re_path(r"ws/chat/(?P<uid>[\w-]+)/$", consumers.ChatConsumer.as_asgi()),
]