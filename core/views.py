from rest_framework import viewsets
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
import json
from core.models import CustomUser, Venue, EmergencyIncident, HelpDeskMessage, EmergencyAlert, StaffMember, OfficialResponder
from core.serializers import CustomUserSerializer, VenueSerializer, EmergencyIncidentSerializer, HelpDeskMessageSerializer

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

    alerts_history = EmergencyAlert.objects.all().order_by('-created_at')[:20]
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
            responder = OfficialResponder.objects.get(official_id=official_id, password=password)
            request.session['responder_id'] = responder.id
            return redirect('response_portal', role=responder.department.lower())
        except OfficialResponder.DoesNotExist:
            return render(request, 'core/staff_login.html', {
                'error': 'Invalid Official ID or Password',
                'login_type': 'Official Responder'
            })
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
    responder, created = OfficialResponder.objects.get_or_create(
        official_id=rid,
        defaults={'name': name, 'password': pwd, 'department': dept.upper()}
    )
    return JsonResponse({'status': 'Created' if created else 'Exists', 'official_id': rid, 'department': dept})

def venue_login(request):
    if request.method == 'POST':
        venue_id_input = request.POST.get('unique_venue_id')
        password = request.POST.get('password')
        print(f"DEBUG: Venue Admin Login Attempt - ID: {venue_id_input}")
        try:
            venue = Venue.objects.get(unique_venue_id=venue_id_input)
            print(f"DEBUG: Venue Found: {venue.hotel_name}")
            if venue.check_admin_password(password):
                print("DEBUG: Password Correct")
                request.session['venue_id'] = venue.id
                return redirect('dashboard')
            else:
                print("DEBUG: Password Incorrect")
                messages.error(request, "Invalid Password")
        except Venue.DoesNotExist:
            print(f"DEBUG: Venue ID NOT FOUND: {venue_id_input}")
            messages.error(request, "Venue ID not found")
    return render(request, 'core/staff_login.html', {'login_type': 'Venue Admin'})

def staff_signup(request):
    venues = Venue.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')
        venue_id = request.POST.get('venue_id')
        
        venue = get_object_or_404(Venue, id=venue_id)
        if StaffMember.objects.filter(staff_id=staff_id).exists():
            messages.error(request, "Staff ID already exists")
        else:
            StaffMember.objects.create(
                name=name,
                staff_id=staff_id,
                password=password, # Use hashing in production
                venue=venue
            )
            messages.success(request, "Account created. Please login.")
            return redirect('staff_login')
            
    return render(request, 'core/staff_signup.html', {'venues': venues})

def staff_login(request):
    if request.method == 'POST':
        venue_id_input = request.POST.get('venue_id')
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('staff_passcode')
        
        print(f"DEBUG: Attempting Staff Login - VenueID: {venue_id_input}, StaffID: {staff_id}")
        
        try:
            # Check if venue exists first
            venue = Venue.objects.get(unique_venue_id=venue_id_input)
            print(f"DEBUG: Found Venue: {venue.hotel_name}")
            
            staff = StaffMember.objects.get(venue=venue, staff_id=staff_id, password=password)
            print(f"DEBUG: Found Staff Member: {staff.name}")
            
            request.session['staff_id'] = staff.id
            request.session['venue_id'] = venue.id
            return redirect('staff_portal')
        except Venue.DoesNotExist:
            print(f"DEBUG: Venue Not Found: {venue_id_input}")
            return render(request, 'core/staff_login.html', {'error': f'Invalid Venue ID: {venue_id_input}'})
        except StaffMember.DoesNotExist:
            print(f"DEBUG: Staff Member Not Found or Invalid Password for ID: {staff_id}")
            return render(request, 'core/staff_login.html', {'error': 'Invalid Staff ID or Passcode'})
            
    return render(request, 'core/staff_login.html')

def register_venue(request):
    """
    Temporary view to register a venue since we have no admin panel for it yet.
    Usage: GET /register-venue/?id=ADMIN24&name=GrandSafe&pass=admin123
    """
    vid = request.GET.get('id', 'ADMIN24')
    name = request.GET.get('name', 'RapidResQ Hotel')
    pwd = request.GET.get('pass', 'admin123')
    
    venue, created = Venue.objects.get_or_create(
        unique_venue_id=vid,
        defaults={'hotel_name': name, 'address': 'Default Address'}
    )
    if created or not venue.admin_password:
        venue.set_admin_password(pwd)
        venue.save()
        status = "Created"
    else:
        status = "Already Exists"
        
    return JsonResponse({
        'status': status,
        'venue_id': vid,
        'hotel_name': name,
        'message': f'Use this ID ({vid}) and password ({pwd}) to login.'
    })

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
    return render(request, 'core/staff_app.html', context)
