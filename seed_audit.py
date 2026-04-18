import os
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rapidresq_backend.settings')
django.setup()

from core.models import Venue, StaffMember, OfficialResponder, CustomUser

def seed_audit():
    try:
        with transaction.atomic():
            # 1. Hotel Admin (Venue)
            v, created = Venue.objects.get_or_create(
                unique_venue_id='hotel_admin',
                defaults={'hotel_name': 'Audit HQ Hotel', 'address': '123 Tech Ave'}
            )
            v.set_admin_password('RapidResQ@Hotel123')
            v.save()

            # Create Admin User for Venue
            admin_user, created = CustomUser.objects.get_or_create(
                username='hotel_admin_user',
                defaults={'role': 'Admin', 'facility': v}
            )
            if created:
                admin_user.set_password('RapidResQ@Hotel123')
                admin_user.save()

            # 2. Police Station (Official Responder)
            police_user, created = CustomUser.objects.get_or_create(
                username='city_police_user',
                defaults={'role': 'FirstResponder'}
            )
            if created:
                police_user.set_password('RapidResQ@Police123')
                police_user.save()
            
            OfficialResponder.objects.update_or_create(
                official_id='city_police',
                defaults={'name': 'City Police Unit', 'password': 'RapidResQ@Police123', 'department': 'POLICE', 'user': police_user}
            )

            # 3. Hospital (Official Responder - MEDICAL)
            medical_user, created = CustomUser.objects.get_or_create(
                username='emergency_med_user',
                defaults={'role': 'FirstResponder'}
            )
            if created:
                medical_user.set_password('RapidResQ@Med123')
                medical_user.save()

            OfficialResponder.objects.update_or_create(
                official_id='emergency_med',
                defaults={'name': 'Emergency Medical Hub', 'password': 'RapidResQ@Med123', 'department': 'MEDICAL', 'user': medical_user}
            )

            # 4. Staff Member (Linked to Audit HQ)
            staff_user, created = CustomUser.objects.get_or_create(
                username='security_staff_user',
                defaults={'role': 'Staff', 'facility': v}
            )
            if created:
                staff_user.set_password('RapidResQ@Staff123')
                staff_user.save()

            StaffMember.objects.update_or_create(
                staff_id='security_staff_1',
                defaults={'name': 'Audit Security 1', 'password': 'RapidResQ@Staff123', 'venue': v, 'is_available': True, 'user': staff_user}
            )

            print("Audit Test Accounts created successfully.")
    except Exception as e:
        print(f"Error seeding data: {e}")

if __name__ == '__main__':
    seed_audit()
