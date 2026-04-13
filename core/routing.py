from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<int:incident_id>/', consumers.HelpDeskConsumer.as_asgi()),
    path('ws/alerts/', consumers.GlobalAlertConsumer.as_asgi()),
]
