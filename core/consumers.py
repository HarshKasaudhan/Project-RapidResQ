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
    try:
        incident = EmergencyIncident.objects.get(id=incident_id)
        
        # Resolve sender
        sender = None
        if isinstance(sender_id, int) or (isinstance(sender_id, str) and sender_id.isdigit()):
            try:
                sender = CustomUser.objects.get(id=sender_id)
            except CustomUser.DoesNotExist:
                pass
        elif sender_id == 'ai_assistant':
            # Handle AI Assistant identification - optionally fetch a specific AI user
            try:
                sender = CustomUser.objects.filter(username='ai_assistant').first()
            except: pass

        msg = HelpDeskMessage.objects.create(
            incident=incident,
            sender=sender, # Can be None for Guest/Anonymous
            message=message
        )
        return msg
    except Exception as e:
        print(f"Error in save_message: {e}")
        return None

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
    elif 'DISASTER' in cat: incident_type = 'NaturalDisaster'
    # 'Security' covers both general security and women safety in our models
    
    return EmergencyIncident.objects.create(
        venue=venue,
        type=incident_type,
        status='Active',
        latitude=lat,
        longitude=lng
    )

@database_sync_to_async
def resolve_incident_in_db(incident_id):
    try:
        from core.models import EmergencyIncident
        incident = EmergencyIncident.objects.get(id=incident_id)
        incident.status = 'Resolved'
        incident.save()
        return True
    except Exception:
        return False

class HelpDeskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.incident_id = self.scope['url_route']['kwargs']['incident_id']
        self.group_name = f'incident_chat_{self.incident_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # ADD TO GLOBAL MASS EVACUATION GROUP
        await self.channel_layer.group_add(
            'mass_evacuation',
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            'mass_evacuation',
            self.channel_name
        )

    async def receive(self, text_data):
        # ... (rest of receive remains same) ...
        try:
            try:
                text_data_json = json.loads(text_data)
            except json.JSONDecodeError:
                print("ERROR: Malformed WebSocket data received in HelpDeskConsumer.")
                return

            sender_id = text_data_json.get('sender_id', 'user')
            message = text_data_json.get('message', '')

            if not message: return

            # Save user message
            await save_message(self.incident_id, sender_id, message)

            # Broadcast user message to group
            chat_data = {
                'type': 'chat_message',
                'message': message,
                'sender_id': sender_id,
                'incident_id': self.incident_id
            }
            
            await self.channel_layer.group_send(
                self.group_name,
                chat_data
            )

            # BROADCAST TO GLOBAL COMMAND DASHBOARD
            await self.channel_layer.group_send(
                'command_dashboard',
                {
                    'type': 'command_chat_sync',
                    'data': chat_data
                }
            )

            # If user sends message, trigger Gemini for real-time guidance
            if sender_id == 'user':
                ai_data = await analyze_with_gemini(message)
                ai_msg = ai_data.get('safety_guide', 'Emergency responders are on the way.')
                
                # Save AI response
                await save_message(self.incident_id, 'ai_assistant', ai_msg)
                
                ai_broadcast_data = {
                    'type': 'chat_message',
                    'message': ai_msg,
                    'sender_id': 'ai_assistant',
                    'is_ai': True,
                    'incident_id': self.incident_id
                }

                # Broadcast AI message
                await self.channel_layer.group_send(
                    self.group_name,
                    ai_broadcast_data
                )

                # SYNC AI TO COMMAND DASHBOARD
                await self.channel_layer.group_send(
                    'command_dashboard',
                    {
                        'type': 'command_chat_sync',
                        'data': ai_broadcast_data
                    }
                )
        except Exception as e:
            print(f"WS Error (HelpDesk): {e}")
            await self.send(text_data=json.dumps({
                'error': str(e),
                'message': 'System busy, using standard protocols.'
            }))

    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        is_ai = event.get('is_ai', False)

        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'is_ai': is_ai
        }))

    # GLOBAL EVACUATION HANDLER
    async def evacuation_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'global_evacuation',
            'message': event['message']
        }))

@sync_to_async
def analyze_with_gemini(transcript):
    print(f"\n[DEBUG] --- SOS CRISIS MAPPER (Gemini AI) ---")
    print(f"[DEBUG] Transcribed Text: '{transcript}'")

    prompt = f"""
    You are an elite Emergency Dispatch AI. Your job is to analyze raw, panicked user input (often in Hindi, Hinglish, or English) and strictly categorize it into predefined emergency cases.
    
    Transcript: "{transcript}"

    PREDEFINED CASES & CATEGORIES (Choose EXACTLY ONE mapping):
    1. "MEDICAL_CASE" -> category: "⚕️ MEDICAL" (Heart attack, injury, breathing issues, chot lagna, khoon)
    2. "FIRE_CASE" -> category: "🔥 FIRE" (Smoke, short circuit, fire, aag, dhua)
    3. "SECURITY_CASE" -> category: "🛡️ SECURITY" (Fight, theft, gunshots, ladai, chori)
    4. "WOMEN_SAFETY_CASE" -> category: "🛡️ WOMEN SAFETY" (Harassment, stalking, feeling unsafe)
    5. "GENERAL_CASE" -> category: "🚨 GENERAL" (Earthquake, lift trapped, unclassified panic, bhukamp)

    INSTRUCTIONS:
    1. Analyze the transcript and assign the exact case_type and matching category.
    2. Assess severity: "LOW", "MEDIUM", "HIGH", or "CRITICAL".
    3. Extract location if mentioned in the transcript, otherwise return "Unknown".
    4. safety_guide: Provide 1-2 actionable, life-saving steps in easy HINGLISH for the victim's screen.
    5. voice_message: Provide a short, calm English summary for voice synthesis.
    
    CRITICAL: You MUST return ONLY a valid JSON object matching the exact schema below. Do NOT wrap it in ```json tags. Do NOT add any extra text.

    {{
        "case_type": "MEDICAL_CASE",
        "category": "⚕️ MEDICAL",
        "severity": "CRITICAL",
        "location": "Room 302",
        "is_emergency": true,
        "safety_guide": "Khoon behne wali jagah par ek saaf kapda zor se dabakar rakhein. Hilne ki koshish na karein.",
        "voice_message": "Medical team dispatched. Please stay calm.",
        "estimated_arrival": "3-5 mins",
        "should_listen": true
    }}
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        ai_data = json.loads(response.text)
        print(f"[DEBUG] Gemini Result: {ai_data.get('case_type')} | ETA: {ai_data.get('estimated_arrival')}")
        return ai_data
    except Exception as e:
        print(f"[ERROR] Gemini AI Triage failed: {e}")
        # Fallback to Basic Mock Logic if API fails
        t = transcript.lower()
        case_type = "GENERAL_CASE"
        category = "🚨 GENERAL"
        instruction = "Emergency dispatched. Help is on the way."
        
        if any(k in t for k in ["fire", "smoke", "aag", "dhua"]):
            case_type = "FIRE_CASE"
            category = "🔥 FIRE"
            instruction = "Fire protocol initiated. Follow the cyan route and stay low."
        elif any(k in t for k in ["pain", "accident", "blood", "breathing", "chot", "khoon", "heart"]):
            case_type = "MEDICAL_CASE"
            category = "⚕️ MEDICAL"
            instruction = "Medical alert active. What specific help do you need?"
        elif any(k in t for k in ["attack", "fight", "thief", "help", "chori", "ladai"]):
            case_type = "SECURITY_CASE"
            category = "🛡️ SECURITY"
            instruction = "Police and Security are on the way. Find a safe spot."

        return {
            "case_type": case_type,
            "category": category,
            "severity": "CRITICAL",
            "location": "Unknown",
            "is_emergency": True,
            "safety_guide": instruction,
            "voice_message": instruction,
            "estimated_arrival": "5-7 mins",
            "should_listen": case_type == "MEDICAL_CASE"
        }
class GlobalAlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        self.venue_id = params.get('venue_id', [''])[0]
        self.role = params.get('role', [''])[0]
        
        # Determine Primary Group membership
        if self.role == 'ADMIN':
            self.group_name = 'command_dashboard'
        elif self.role == 'POLICE':
            self.group_name = 'police_alerts'
        elif self.role == 'MEDICAL':
            self.group_name = 'medical_alerts'
        elif self.role == 'FIRE':
            self.group_name = 'fire_alerts'
        elif self.venue_id:
            self.group_name = f'venue_{self.venue_id}'
        else:
            self.group_name = 'command_dashboard'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        # ADD TO GLOBAL MASS EVACUATION GROUP
        await self.channel_layer.group_add('mass_evacuation', self.channel_name)
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_discard('mass_evacuation', self.channel_name)

    async def receive(self, text_data):
        try:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                print("ERROR: Malformed WebSocket data received.")
                return

            # --- NEW: MASS EVACUATION BROADCAST (Brahmastra) ---
            if data.get('type') == 'global_evacuation':
                await self.channel_layer.group_send(
                    'mass_evacuation',
                    {
                        'type': 'evacuation_broadcast',
                        'message': data.get('message', 'CRITICAL DANGER: EVACUATE PREMISES IMMEDIATELY.')
                    }
                )
                return

            # Handle Staff Movement Updates
            if data.get('type') == 'staff_location':
                try:
                    # Notify Venue Admins and Staff
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
                    # Also notify command_dashboard
                    await self.channel_layer.group_send(
                        'command_dashboard',
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

            # --- NEW: Admin Multi-Unit Co-Dispatch Routing ---
            if data.get('type') == 'dispatch_help':
                incident_id = data.get('incident_id')
                hazard_type = data.get('hazard_type', 'General')
                venue_id = data.get('venue_id')
                
                target_groups = ['police_alerts'] # Default: Police only
                
                if 'Medical' in hazard_type:
                    target_groups.append('medical_alerts')
                elif 'Fire' in hazard_type:
                    target_groups.append('fire_alerts')
                
                # Broadcoast to selected authority groups
                for group in target_groups:
                    await self.channel_layer.group_send(
                        group,
                        {
                            'type': 'global_emergency_alert',
                            'message': f"DISPATCH REQUEST: {hazard_type}",
                            'location': data.get('location', 'Venue Location'),
                            'alert_type': hazard_type,
                            'incident_id': incident_id,
                            'severity': 'HIGH'
                        }
                    )
                
                # Notify command_dashboard for UI sync
                await self.channel_layer.group_send(
                    'command_dashboard',
                    {
                        'type': 'incident_status_update',
                        'incident_id': incident_id,
                        'status': 'Dispatched',
                        'staff_name': 'Admin'
                    }
                )
                return

            # --- NEW: Staff -> Command Tactical Chat ---
            if data.get('type') == 'staff_command_chat':
                await self.channel_layer.group_send(
                    'command_dashboard',
                    {
                        'type': 'staff_chat_broadcast',
                        'message': data['message'],
                        'staff_name': data['staff_name'],
                        'staff_id': data['staff_id']
                    }
                )
                return

            # --- NEW: Responder Arrived (On-Scene) ---
            if data.get('type') == 'incident_resolving':
                incident_id = data.get('incident_id')
                # Notify Command Dashboard
                await self.channel_layer.group_send(
                    'command_dashboard',
                    {
                        'type': 'incident_status_update',
                        'incident_id': incident_id,
                        'status': 'On-Scene',
                        'staff_name': data.get('staff_name')
                    }
                )
                # Notify Victim Room
                await self.channel_layer.group_send(
                    f'incident_chat_{incident_id}',
                    {
                        'type': 'chat_message',
                        'message': "RESPONDER ON-SCENE. Stay where you are.",
                        'sender_id': 'staff_arrival',
                        'is_authority': True
                    }
                )
                return

            # --- NEW: Authority Dispatch with ETA ---
            if data.get('type') == 'authority_dispatch':
                incident_id = data.get('incident_id')
                eta = data.get('eta')
                role = data.get('role')
                
                # Notify Victim Room
                await self.channel_layer.group_send(
                    f'incident_chat_{incident_id}',
                    {
                        'type': 'chat_message',
                        'message': f"HELP IS EN ROUTE - ETA: {eta} mins",
                        'sender_id': f'{role.lower()}_dispatch',
                        'is_authority': True
                    }
                )
                
                # Notify Command Dashboard
                await self.channel_layer.group_send(
                    'command_dashboard',
                    {
                        'type': 'authority_dispatch_broadcast',
                        'incident_id': incident_id,
                        'eta': eta,
                        'role': role
                    }
                )
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
                        'lat': lat,
                        'lng': lng,
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
            elif data.get('type') == 'rescue_verified':
                incident_id = data.get('incident_id')
                if await resolve_incident_in_db(incident_id):
                    # Notify Admin Dashboard & Staff
                    await self.channel_layer.group_send(
                        'command_dashboard',
                        {
                            'type': 'incident_resolution_broadcast',
                            'incident_id': incident_id
                        }
                    )
                    if venue_obj:
                        await self.channel_layer.group_send(
                            f"venue_{venue_obj.id}",
                            {
                                'type': 'incident_resolution_broadcast',
                                'incident_id': incident_id
                            }
                        )
                return
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
                # Role-Specific Broadcast
                target_groups = ["command_dashboard"] # Admin always sees all
                if venue_obj:
                    target_groups.append(f"venue_{venue_obj.id}")
                
                # Indian Context Initial Routing
                target_groups.append('police_alerts')
                if 'MEDICAL' in alert_type.upper():
                    target_groups.append("medical_alerts")
                elif 'FIRE' in alert_type.upper():
                    target_groups.append("fire_alerts")

                for group in target_groups:
                    await self.channel_layer.group_send(
                        group,
                        {
                            'type': 'global_emergency_alert',
                            'message': message,
                            'location': location,
                            'alert_type': alert_type,
                            'incident_id': incident.id if 'incident' in locals() else None,
                            'severity': severity
                        }
                    )
        except Exception as e:
            print(f"WS Error (Global): {e}")
            await self.send(text_data=json.dumps({
                'error': str(e),
                'message': 'System busy, using standard protocols.'
            }))

    async def global_emergency_alert(self, event):
        await self.send(text_data=json.dumps({
            'type': 'emergency_confirmed', # Map to standard frontend handler
            'alert': {
                'message': event['message'],
                'location': event['location'],
                'type': event.get('alert_type', 'GENERAL'),
                'incident_id': event.get('incident_id'),
                'severity': event.get('severity')
            },
            'category': event.get('alert_type'),
            'incident_id': event.get('incident_id'),
            'severity': event.get('severity')
        }))

    async def command_chat_sync(self, event):
        await self.send(text_data=json.dumps({
            'type': 'command_chat_sync',
            'data': event['data']
        }))

    async def incident_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'incident_status_update',
            'incident_id': event['incident_id'],
            'status': event['status'],
            'staff_name': event['staff_name']
        }))

    async def staff_chat_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'staff_chat',
            'message': event['message'],
            'staff_name': event['staff_name'],
            'staff_id': event['staff_id']
        }))

    async def authority_dispatch_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'authority_dispatch',
            'incident_id': event['incident_id'],
            'eta': event['eta'],
            'role': event['role']
        }))

    async def incident_resolution_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'incident_resolved',
            'incident_id': event['incident_id']
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

    async def evacuation_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'global_evacuation',
            'message': event['message']
        }))
