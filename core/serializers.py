from rest_framework import serializers
from core.models import CustomUser, Venue, EmergencyIncident, HelpDeskMessage, Feedback

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class EmergencyIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyIncident
        fields = '__all__'

class HelpDeskMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDeskMessage
        fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'
