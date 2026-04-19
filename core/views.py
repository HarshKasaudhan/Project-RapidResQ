import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.db import transaction, connection
from rest_framework import viewsets

from core.models import CustomUser, Venue, EmergencyIncident, HelpDeskMessage, EmergencyAlert, StaffMember, OfficialResponder, Feedback
from core.serializers import CustomUserSerializer, VenueSerializer, EmergencyIncidentSerializer, HelpDeskMessageSerializer, FeedbackSerializer

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer

class EmergencyIncidentViewSet(viewsets.ModelViewSet):
    queryset = EmergencyIncident.objects.all()
    serializer_class = EmergencyIncidentSerializer

class HelpDeskMessageViewSet(viewsets.ModelViewSet):
    queryset = HelpDeskMessage.objects.all()
    serializer_class = HelpDeskMessageSerializer

class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer

def offline_safety_guide(request):
    return render(request, 'core/safety_guide.html')

def command_dashboard(request):
    # RBAC: Strictly only allow authenticated Venue Admins
    venue_id = request.session.get('venue_id')
    is_staff = request.session.get('staff_id')
    
    if not venue_id or is_staff:
        # If it's a staff member or unauthorized user, force them to login
        return redirect('venue_login')
    
    venue = get_object_or_404(Venue, id=venue_id)
    alerts = EmergencyAlert.objects.filter(venue=venue).order_by('-created_at')[:20]
    # Fetch available staff for this venue
    staff = StaffMember.objects.filter(venue=venue, is_available=True)
    
    # Pass staff data as JSON for the JS distance calculator
    staff_data = []
    for s in staff:
        staff_data.append({
            'name': s.name,
            'lat': s.current_lat,
            'lng': s.current_lng,
            'id': s.staff_id
        })

    context = {
        'venue': venue,
        'alerts': alerts,
        'staff_json': json.dumps(staff_data)
    }
    return render(request, 'core/dashboard.html', context)

def guest_app(request):
    return render(request, 'core/mobile_app.html')

def home_hub(request):
    return render(request, 'core/home.html')

def about_view(request):
    return render(request, 'core/about.html')

def contact_view(request):
    return render(request, 'core/contact.html')

def features_view(request):
    return render(request, 'core/features.html')

def services_view(request):
    return render(request, 'core/services.html')

def safety_drills_view(request):
    return render(request, 'core/safety_drills.html')

def feedback_view(request):
    return render(request, 'core/feedback.html')

def response_portal(request, role):
    # RBAC: Only allow Official Responders with matching department role
    responder_id = request.session.get('responder_id')
    if not responder_id:
        messages.error(request, "Authentication Required for Official Portals")
        return redirect('responder_login')
    
    try:
        responder = OfficialResponder.objects.get(id=responder_id)
        if responder.department != role.upper():
            messages.error(request, f"Permission Denied: You are not authorized for the {role.upper()} portal")
            return redirect('response_portal', role=responder.department.lower())
    except OfficialResponder.DoesNotExist:
        request.session.flush()
        return redirect('responder_login')

    # Strict filtering by hazard type
    hazard_map = {
        'POLICE': 'Security',
        'MEDICAL': 'Medical',
        'FIRE': 'Fire'
    }
    target_hazard = hazard_map.get(role.upper(), 'General')
    
    alerts_history = EmergencyAlert.objects.filter(category__icontains=target_hazard).order_by('-created_at')[:20]
    context = {
        'role': role.upper(),
        'alerts_history': alerts_history,
        'responder': responder
    }
    return render(request, 'core/portal.html', context)

def responder_login(request):
    if request.method == 'POST':
        official_id = request.POST.get('official_id')
        password = request.POST.get('password')
        try:
            responder = OfficialResponder.objects.get(official_id=official_id)
            user = authenticate(username=responder.user.username, password=password)
            if user:
                login(request, user)
                request.session['responder_id'] = responder.id
                return redirect('response_portal', role=responder.department.lower())
            else:
                messages.error(request, "Invalid Password")
        except OfficialResponder.DoesNotExist:
            messages.error(request, "Invalid Official ID")
    return render(request, 'core/staff_login.html', {'login_type': 'Official Responder'})

def register_responder(request):
    """
    Temporary view to register responders.
    Usage: /register-responder/?id=POLICE01&pass=pass123&dept=POLICE&name=Officer Smith
    """
    rid = request.GET.get('id')
    pwd = request.GET.get('pass')
    dept = request.GET.get('dept')
    name = request.GET.get('name', 'Official Unit')
    if not all([rid, pwd, dept]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        with transaction.atomic():
            user, created_user = CustomUser.objects.get_or_create(
                username=rid,
                defaults={'role': 'FirstResponder'}
            )
            if created_user:
                user.set_password(pwd)
                user.save()

            responder, created = OfficialResponder.objects.get_or_create(
                official_id=rid,
                defaults={'name': name, 'password': pwd, 'department': dept.upper(), 'user': user}
            )
            return JsonResponse({'status': 'Created' if created else 'Exists', 'official_id': rid, 'department': dept})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def venue_login(request):
    if request.method == 'POST':
        venue_id_input = request.POST.get('unique_venue_id')
        password = request.POST.get('password')
        try:
            venue = Venue.objects.get(unique_venue_id=venue_id_input)
            admin_user = CustomUser.objects.filter(facility=venue, role='Admin').first()
            if admin_user:
                user = authenticate(username=admin_user.username, password=password)
                if user:
                    login(request, user)
                    request.session['venue_id'] = venue.id
                    return redirect('dashboard')
            
            if venue.check_admin_password(password):
                request.session['venue_id'] = venue.id
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid Password")
        except Venue.DoesNotExist:
            messages.error(request, "Venue ID not found")
    return render(request, 'core/staff_login.html', {'login_type': 'Venue Admin'})

def venue_signup(request):
    if request.method == 'POST':
        hotel_name = request.POST.get('hotel_name')
        address = request.POST.get('address')
        username = request.POST.get('username')
        password = request.POST.get('password')
        venue_id_input = request.POST.get('unique_venue_id')

        if not venue_id_input:
            venue_id_input = f"VENUE-{uuid.uuid4().hex[:6].upper()}"

        try:
            with transaction.atomic():
                venue = Venue.objects.create(
                    hotel_name=hotel_name,
                    address=address,
                    unique_venue_id=venue_id_input
                )
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    role='Admin',
                    facility=venue
                )
                messages.success(request, f"Venue created successfully! Your Venue ID is: {venue_id_input}")
                return redirect('venue_login')
        except Exception as e:
            messages.error(request, f"Error creating venue: {str(e)}")

    return render(request, 'core/venue_signup.html')

def responder_signup(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        official_id = request.POST.get('official_id')
        password = request.POST.get('password')
        department = request.POST.get('department')
        username = request.POST.get('username', official_id)

        try:
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    role='FirstResponder'
                )
                OfficialResponder.objects.create(
                    user=user,
                    name=name,
                    official_id=official_id,
                    password=password, # Legacy compatibility
                    department=department
                )
                messages.success(request, "Responder account created. Please login.")
                return redirect('responder_login')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'core/responder_signup.html', {
        'departments': OfficialResponder.DEPT_CHOICES
    })

def staff_signup(request):
    venues = Venue.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')
        venue_id = request.POST.get('venue_id')
        username = request.POST.get('username', staff_id)

        if not venue_id:
            messages.error(request, "Please select a facility.")
        else:
            venue = get_object_or_404(Venue, id=venue_id)
            try:
                with transaction.atomic():
                    user = CustomUser.objects.create_user(
                        username=username,
                        password=password,
                        role='Staff',
                        facility=venue
                    )
                    StaffMember.objects.create(
                        user=user,
                        name=name,
                        staff_id=staff_id,
                        password=password,
                        venue=venue
                    )
                    messages.success(request, "Staff account created. Please login.")
                    return redirect('staff_login')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            
    return render(request, 'core/staff_signup.html', {'venues': venues})

def staff_login(request):
    if request.method == 'POST':
        venue_id_input = request.POST.get('venue_id')
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('staff_passcode')
        try:
            venue = Venue.objects.get(unique_venue_id=venue_id_input)
            staff = StaffMember.objects.get(venue=venue, staff_id=staff_id)
            user = authenticate(username=staff.user.username, password=password)
            if user:
                login(request, user)
                request.session['staff_id'] = staff.id
                request.session['venue_id'] = venue.id
                return redirect('staff_portal')
            else:
                messages.error(request, "Invalid Password")
        except (Venue.DoesNotExist, StaffMember.DoesNotExist):
            messages.error(request, "Invalid Venue ID or Staff ID")
    return render(request, 'core/staff_login.html', {'login_type': 'Staff Unit'})


def register_venue(request):
    """
    Temporary view to register a venue since we have no admin panel for it yet.
    Usage: GET /register-venue/?id=ADMIN24&name=GrandSafe&pass=admin123
    """
    vid = request.GET.get('id', 'ADMIN24')
    name = request.GET.get('name', 'RapidResQ Hotel')
    pwd = request.GET.get('pass', 'admin123')
    
    try:
        with transaction.atomic():
            venue, created = Venue.objects.get_or_create(
                unique_venue_id=vid,
                defaults={'hotel_name': name, 'address': 'Default Address'}
            )
            if created or not venue.admin_password:
                venue.set_admin_password(pwd)
                venue.save()

            admin_user, created_user = CustomUser.objects.get_or_create(
                username=vid,
                defaults={'role': 'Admin', 'facility': venue}
            )
            if created_user:
                admin_user.set_password(pwd)
                admin_user.save()
                
            status = "Created" if created else "Already Exists"
            return JsonResponse({
                'status': status,
                'venue_id': vid,
                'hotel_name': name,
                'message': f'Use this ID ({vid}) and password ({pwd}) to login.'
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def staff_portal(request):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('staff_login')
    
    try:
        staff = StaffMember.objects.get(id=staff_id)
    except StaffMember.DoesNotExist:
        request.session.flush()
        return redirect('staff_login')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if 'is_available' in data:
                staff.is_available = data['is_available']
            if 'lat' in data and 'lng' in data:
                staff.current_lat = float(data['lat'])
                staff.current_lng = float(data['lng'])
            staff.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    context = {
        'staff': staff,
        'venue': staff.venue
    }
    return render(request, 'core/staff_portal.html', context)

def db_health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return HttpResponse("SUCCESS: PostgreSQL Database is fully connected and operational.")
    except Exception as e:
        return HttpResponse(f"FAILURE: Database connection failed. Error: {str(e)}", status=500)
