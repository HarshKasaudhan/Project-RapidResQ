import json
import os
from urllib.parse import parse_qs
import google.generativeai as genai
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from core.models import HelpDeskMessage, EmergencyIncident, CustomUser, EmergencyAlert, Venue

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

@database_sync_to_async
def save_message(incident_id, sender_id, message):
    incident = EmergencyIncident.objects.get(id=incident_id)
    sender = CustomUser.objects.get(id=sender_id)
    msg = HelpDeskMessage.objects.create(
        incident=incident,
        sender=sender,
        message=message
    )
    return msg

@database_sync_to_async
def save_alert(category, severity, location, description, venue=None):
    return EmergencyAlert.objects.create(
        category=category,
        severity=severity,
        location=location,
        description=description,
        venue=venue
    )

@database_sync_to_async
def get_venue_by_id(venue_id):
    try:
        return Venue.objects.get(id=venue_id)
    except:
        return Venue.objects.first()

@database_sync_to_async
def save_incident(venue, category, lat, lng):
    # Map category to TYPE_CHOICES
    incident_type = 'Security'
    cat = category.upper()
    if 'FIRE' in cat: incident_type = 'Fire'
    elif 'MEDICAL' in cat: incident_type = 'Medical'
    
    return EmergencyIncident.objects.create(
        venue=venue,
        type=incident_type,
        status='Active',
        latitude=lat,
        longitude=lng
    )

class HelpDeskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.incident_id = self.scope['url_route']['kwargs']['incident_id']
        self.group_name = f'incident_chat_{self.incident_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        sender_id = text_data_json['sender_id']
        message = text_data_json['message']

        msg = await save_message(self.incident_id, sender_id, message)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': sender_id
            }
        )

    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']

        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id
        }))

@sync_to_async
def analyze_with_gemini(transcript):
    t = transcript.lower()
    
    print(f"\n[DEBUG] --- SOS CRISIS MAPPER ---")
    print(f"[DEBUG] Transcribed Text: '{transcript}'")

    # Task 2: Master Crisis_Mapper Logic
    case_type = "GENERAL_CASE"
    voice_instruction = "Emergency dispatched. Help is on the way."
    estimated_arrival = "5-7 mins"
    category = "🚨 GENERAL"
    should_listen = False

    if any(k in t for k in ["fire", "smoke"]):
        case_type = "FIRE_CASE"
        category = "🔥 FIRE"
        voice_instruction = "Fire protocol initiated. Follow the cyan route and stay low."
        estimated_arrival = "3-5 mins"
    elif any(k in t for k in ["pain", "accident", "blood", "breathing"]):
        case_type = "MEDICAL_CASE"
        category = "⚕️ MEDICAL"
        voice_instruction = "Medical alert active. What specific help do you need?"
        estimated_arrival = "4-6 mins"
        should_listen = True
    elif any(k in t for k in ["attack", "fight", "thief", "help"]):
        case_type = "SECURITY_CASE"
        category = "🛡️ SECURITY"
        voice_instruction = "Police and Security are on the way. Find a safe spot."
        estimated_arrival = "2-4 mins"
    elif any(k in t for k in ["safe", "scared", "following"]):
        case_type = "WOMEN_SAFETY_CASE"
        category = "🛡️ WOMEN SAFETY"
        voice_instruction = "RapidResQ Security is monitoring your live location. Stay in a visible area."
        estimated_arrival = "2-3 mins"
    
    print(f"[DEBUG] Result: {case_type} | ETA: {estimated_arrival}")
    
    return {
        "case_type": case_type,
        "category": category,
        "severity": "CRITICAL",
        "location": "Unknown",
        "is_emergency": True,
        "safety_guide": voice_instruction,
        "voice_message": voice_instruction,
        "estimated_arrival": estimated_arrival,
        "should_listen": should_listen
    }

class GlobalAlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        self.venue_id = params.get('venue_id', [''])[0]
        self.role = params.get('role', [''])[0]
        
        # Determine Primary Group membership
        if self.role == 'POLICE':
            self.group_name = 'global_alerts'
        elif self.role == 'MEDICAL':
            self.group_name = 'medical_alerts'
        elif self.venue_id:
            self.group_name = f'venue_{self.venue_id}'
        else:
            self.group_name = 'global_alerts'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            print("ERROR: Malformed WebSocket data received.")
            return

        # Handle Staff Movement Updates
        if data.get('type') == 'staff_location':
            try:
                await self.channel_layer.group_send(
                    f"venue_{data['venue_id']}",
                    {
                        'type': 'staff_movement',
                        'staff_id': data['staff_id'],
                        'lat': data['lat'],
                        'lng': data['lng'],
                        'name': data['name']
                    }
                )
            except KeyError as e:
                print(f"ERROR: Missing staff telemetry key: {e}")
            return

        # Handle SOS Alerts
        try:
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            params = parse_qs(query_string)
            venue_id_context = params.get('venue_id', [''])[0]
            venue_obj = await get_venue_by_id(venue_id_context)
        except Exception as e:
            print(f"ERROR: Failed to resolve venue context: {e}")
            venue_obj = None

        if data.get('type') == 'raw_voice_transcript':
            transcript = data.get('transcript', 'No transcript provided.')
            frontend_location = data.get('location', 'Unknown')
            try:
                ai_data = await analyze_with_gemini(transcript)
                message = f"[{ai_data['severity']}] {ai_data['category']}"
                ai_location = ai_data.get('location', 'Unknown')
                location = f"{frontend_location} | Room: {ai_location}" if ai_location.lower() != 'unknown' else frontend_location
                
                # Extract lat/lng for incident creation
                lat, lng = 0.0, 0.0
                try:
                    if "Lat:" in frontend_location:
                        parts = frontend_location.split(',')
                        lat = float(parts[0].split(':')[1].strip())
                        lng = float(parts[1].split(':')[1].strip())
                except: pass

                incident = await save_incident(venue_obj, ai_data['category'], lat, lng)

                await self.send(text_data=json.dumps({
                    'type': 'emergency_confirmed',
                    'category': ai_data['category'],
                    'case_type': ai_data.get('case_type', 'GENERAL_CASE'),
                    'severity': ai_data['severity'],
                    'safety_guide': ai_data['safety_guide'],
                    'voice_message': ai_data.get('voice_message', ''),
                    'estimated_arrival': ai_data.get('estimated_arrival', 'Calculating...'),
                    'incident_id': incident.id,
                    'should_listen': ai_data.get('should_listen', False),
                    'show_map': True
                }))

                alert_type = ai_data['category']
                severity = ai_data['severity']
                description = transcript
            except Exception as e:
                print(f"ERROR: Gemini AI Triage failed: {e}")
                message = "[CRITICAL] 🚨 GENERAL EMERGENCY"
                location = frontend_location
                alert_type = "🚨 GENERAL"
                severity = "CRITICAL"
                description = transcript
        else:
            message = data.get('message', 'CRITICAL ALERT')
            location = data.get('location', 'UNKNOWN')
            alert_type = data.get('type', 'GENERAL')
            severity = "CRITICAL"
            description = message
            
        try:
            await save_alert(category=alert_type, severity=severity, location=location, description=description, venue=venue_obj)
        except Exception as e:
            print(f"ERROR: Failed to commit alert to database: {e}")

        if alert_type != 'audit_log':
            # ... broadcast logic ...
            # Role-Specific Broadcast
            target_groups = ["global_alerts"] # Police always see all
            if venue_obj:
                target_groups.append(f"venue_{venue_obj.id}")
            if 'MEDICAL' in alert_type:
                target_groups.append("medical_alerts")

            for group in target_groups:
                await self.channel_layer.group_send(
                    group,
                    {
                        'type': 'global_emergency_alert',
                        'message': message,
                        'location': location,
                        'alert_type': alert_type
                    }
                )

    async def global_emergency_alert(self, event):
        await self.send(text_data=json.dumps({
            'alert': {
                'message': event['message'],
                'location': event['location'],
                'type': event.get('alert_type', 'GENERAL')
            }
        }))

    async def staff_movement(self, event):
        await self.send(text_data=json.dumps({
            'staff_update': {
                'id': event['staff_id'],
                'lat': event['lat'],
                'lng': event['lng'],
                'name': event['name']
            }
        }))
