from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView
from core.views import (
    CustomUserViewSet, VenueViewSet, EmergencyIncidentViewSet, 
    HelpDeskMessageViewSet, FeedbackViewSet, offline_safety_guide, command_dashboard, 
    guest_app, venue_login, staff_signup, staff_login, staff_portal
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'venues', VenueViewSet, basename='venue')
router.register(r'incidents', EmergencyIncidentViewSet, basename='incident')
router.register(r'chat', HelpDeskMessageViewSet, basename='chat')
router.register(r'feedback-api', FeedbackViewSet, basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
    path('guide/', offline_safety_guide, name='offline_safety_guide'),
    path('dashboard/', command_dashboard, name='dashboard'),
    path('app/', guest_app, name='guest_app'),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw.js'),
    
]
