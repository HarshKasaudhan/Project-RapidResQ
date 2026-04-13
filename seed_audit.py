import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rapidresq_backend.settings')
django.setup()

from core.models import Venue, StaffMember, OfficialResponder

def seed_audit():
    # 1. Hotel Admin (Venue)
    v, created = Venue.objects.get_or_create(
        unique_venue_id='hotel_admin',
        defaults={'hotel_name': 'Audit HQ Hotel', 'address': '123 Tech Ave'}
    )
    v.set_admin_password('RapidResQ@Hotel123')
    v.save()

    # 2. Police Station (Official Responder)
    OfficialResponder.objects.update_or_create(
        official_id='city_police',
        defaults={'name': 'City Police Unit', 'password': 'RapidResQ@Police123', 'department': 'POLICE'}
    )

    # 3. Hospital (Official Responder - MEDICAL)
    OfficialResponder.objects.update_or_create(
        official_id='emergency_med',
        defaults={'name': 'Emergency Medical Hub', 'password': 'RapidResQ@Med123', 'department': 'MEDICAL'}
    )

    # 4. Staff Member (Linked to Audit HQ)
    StaffMember.objects.update_or_create(
        staff_id='security_staff_1',
        defaults={'name': 'Audit Security 1', 'password': 'RapidResQ@Staff123', 'venue': v, 'is_available': True}
    )

    print("Audit Test Accounts created successfully.")

if __name__ == '__main__':
    seed_audit()
