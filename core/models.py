from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('Guest', 'Guest'),
        ('Staff', 'Staff'),
        ('FirstResponder', 'First Responder'),
        ('Admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Guest')
    phone_number = models.CharField(max_length=20, blank=True)
    native_language = models.CharField(max_length=10, default='en')
    facility = models.ForeignKey('Venue', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    def __str__(self):
        return f"{self.username} - {self.role}"

class Venue(models.Model):
    hotel_name = models.CharField(max_length=255)
    unique_venue_id = models.CharField(max_length=50, unique=True)
    admin_password = models.CharField(max_length=128, blank=True) # Optional if using CustomUser
    floor_plan_image = models.URLField(max_length=500, blank=True, null=True)
    address = models.TextField()

    def __str__(self):
        return self.hotel_name

    def set_admin_password(self, raw_password):
        self.admin_password = make_password(raw_password)

    def check_admin_password(self, raw_password):
        return check_password(raw_password, self.admin_password)

class EmergencyIncident(models.Model):
    TYPE_CHOICES = [
        ('Fire', 'Fire'),
        ('Medical', 'Medical'),
        ('Security', 'Security'),
        ('NaturalDisaster', 'Natural Disaster'),
    ]
    STATUS_CHOICES = [
        ('Unverified', 'Unverified'),
        ('Active', 'Active'),
        ('Resolved', 'Resolved'),
    ]
    
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='incidents')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Unverified')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.status}] {self.get_type_display()} at {self.venue.hotel_name}"

class HelpDeskMessage(models.Model):
    incident = models.ForeignKey(EmergencyIncident, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='messages_sent')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} on Incident {self.incident.id}"

class ActionAuditLog(models.Model):
    incident = models.ForeignKey(EmergencyIncident, on_delete=models.CASCADE, related_name='audit_logs')
    action_taken = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log: {self.action_taken} (Incident {self.incident.id})"

class EmergencyAlert(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    category = models.CharField(max_length=50)
    severity = models.CharField(max_length=50)
    location = models.TextField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity}] {self.category} at {self.location}"

class StaffMember(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile', null=True, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='staff_members')
    name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128) # Kept for legacy/simplicity as per request, but user.password is preferred
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.venue.hotel_name})"

class OfficialResponder(models.Model):
    DEPT_CHOICES = [
        ('POLICE', 'Police Department'),
        ('MEDICAL', 'Medical Unit'),
        ('FIRE', 'Fire Rescue'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='responder_profile', null=True, blank=True)
    name = models.CharField(max_length=255)
    official_id = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    department = models.CharField(max_length=20, choices=DEPT_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.department})"

class Feedback(models.Model):
    dispatch_reference_id = models.CharField(max_length=100)
    triage_accuracy = models.IntegerField(default=0)
    detailed_report = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.dispatch_reference_id}"

