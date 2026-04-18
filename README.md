# 🚨 RapidResQ: Context-Aware Emergency Response Ecosystem

![Status: MVP Live](https://img.shields.io/badge/Status-MVP_Live-brightgreen)
![Platform: PWA](https://img.shields.io/badge/Platform-PWA_Ready-blue)
![AI: Gemini 1.5](https://img.shields.io/badge/AI-Gemini_1.5_Flash-orange)
![Google Solution Challenge](https://img.shields.io/badge/Google-Solution_Challenge_2026-blueviolet)

**RapidResQ** is not just an SOS button; it's a complete B2B2C emergency infrastructure. Designed to prevent stampedes, bridge communication gaps during internet outages, and provide real-time tactical data to responders using WebSockets and AI.

🔗 **[Live Demo URL]** | 📹 **[YouTube Pitch Video]**

---

## 🛑 The Problem
During an emergency (fire, medical, security) in high-density venues (campuses, malls):
1. **Network Congestion:** Panic leads to jammed networks, failing standard SOS calls.
2. **Mass Panic:** Venue-wide alarms cause stampedes, which are often more fatal than the hazard itself.
3. **Information Void:** Responders lack context (Who needs help? What kind of help? Where exactly?).

## 💡 The RapidResQ Solution
RapidResQ acts as a resilient, closed-loop rescue engine that works offline, prioritizes alerts using AI, and manages crowds dynamically.

---

## 🌟 Hero Features (The 3 Pillars)

### 1. Resilient Infrastructure (Never Fails)
* 📡 **Offline SOS Sync (DTN):** Built as a Progressive Web App (PWA). If the internet fails, the Service Worker (`sw.js`) caches the SOS trigger locally and auto-syncs to the command center the millisecond connectivity returns.
* 📖 **Pre-Cached Safety Guides:** Critical evacuation and first-aid manuals are accessible completely offline.

### 2. Context-Aware AI (Smart Response)
* 🧠 **Hinglish AI Triage Engine:** Powered by **Google Gemini 1.5 Flash**. It parses panicked, multi-lingual voice/text inputs (e.g., "Saans lene mein dikkat hai") into strict JSON (Severity, Hazard Type, Actionable Guidance).
* 🎙️ **Voice-to-Text Telemetry:** Users can report emergencies hands-free using the native Web Speech API, perfectly suited for crisis situations.

### 3. Tactical Crowd & Rescue Management
* 🗺️ **Predictive Crowd Heatmap:** Real-time visualization using `leaflet-heat.js`. Command centers can see high-density zones to prevent stampedes before they occur.
* 🎯 **Dynamic Geo-Fenced Alerts:** Uses the **Haversine Formula** on the client side. Only users within a 100-meter "Blast Radius" receive massive Evacuation Alerts. Others receive a "Safe Zone" notification to keep pathways clear.
* 🤝 **Closed-Loop Bluetooth Handshake:** Uses Web Bluetooth API for proximity verification. Once a responder reaches a victim, their devices handshake to automatically mark the incident as "Resolved" on the dashboard.

---

## 🏗️ Under The Hood (Architecture)
* **Bi-Directional Real-Time Engine:** Built on Django Channels (WebSockets) and Daphne. No page refreshes—everything from heatmaps to chat is strictly real-time.
* **Multi-Venue Scalability:** The database is natively designed to handle isolated data streams from multiple venues simultaneously (B2B Ready).
* **Multi-Tier RBAC:** Distinct, secure portals for Victims (Mobile PWA), Ground Rescuers (Staff App), and Dispatchers (Command Center).

---

## 💻 Tech Stack
* **Frontend:** HTML5, CSS3, Vanilla JS, PWA (Service Workers, IndexedDB)
* **Backend:** Python, Django, Django REST Framework, Django Channels (WebSockets)
* **Database:** PostgreSQL (via Supabase), Redis (for Channel layers)
* **AI & APIs:** Google Gemini API, Web Speech API, Web Bluetooth API, Geolocation API
* **Deployment:** Render (Daphne ASGI Server)

---

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/rapidresq.git](https://github.com/yourusername/rapidresq.git)
   cd rapidresq
2. **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/Scripts/activate  # On Windows
3. **Install dependencies:**
    ```Bash
    pip install -r requirements.txt
4. **Environment Variables: Create a .env file in the root directory and add:**
    ```Code snippet
    GEMINI_API_KEY=your_google_gemini_key
    DATABASE_URL=your_supabase_url
5. **Run Migrations & Server:**
    ```Bash
    python manage.py migrate
    daphne -b 0.0.0.0 -p 8000 rapidresq_backend.asgi:application
