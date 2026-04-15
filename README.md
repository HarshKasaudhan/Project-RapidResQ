# 🚀 RapidResQ: Next-Gen Emergency Infrastructure

**RapidResQ** is a high-performance, AI-driven emergency response ecosystem designed for the modern era. By combining Generative AI, real-time telemetrics, and Zero-Network Survival logic, it provides an unbreakable safety net for institutional environments like hotels, hospitals, and corporate campuses.

---

## 🛡️ Key Features

### 🎙️ AI-Powered Voice Triage
Utilizes **Gemini AI** for neural analysis of emergency voice transcripts. It categorizes incidents by severity and type (Fire, Medical, Security) in real-time, supporting English, Hindi, and Hinglish.

### 📶 Zero-Network Survival Mode
**Our USP.** If the internet fails, RapidResQ switches to a **Local ResQ Mode**. It uses browser caching to display emergency exit maps and triggers a **Physical Beacon** (strobe light and high-pitch alarm) on the mobile device to assist rescuers in locating victims.

### 📍 Tactical Command Center
A unified dashboard for admins and responders with:
* **Live GPS Tracking:** Real-time staff positions via WebSockets.
* **Smart Proximity Routing:** Automatically identifies and alerts the 3 nearest responders to an SOS location.
* **Role-Based Access:** Isolated portals for Venue Admins, Police Stations, and Hospitals.

### 📱 Responsive PWA
A "Mobile-First" interface with a zero-latency SOS button, integrated maps, and a 3-second fail-safe countdown.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Django (Python 3.11+) |
| **Real-time** | Django Channels, WebSockets, Redis |
| **Artificial Intelligence** | Gemini 3 Flash API |
| **Database** | PostgreSQL / Supabase |
| **Frontend** | Tailwind CSS, JavaScript (Vanilla), Leaflet.js |
| **Caching/Offline** | Service Workers (PWA), LocalStorage |

---

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/RapidResQ-Emergency-Infrastructure.git
cd RapidResQ-Emergency-Infrastructure
2. Setup Virtual Environment
Bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Environment Variables
Create a .env file and add your credentials:

Code snippet
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=your_db_url
SECRET_KEY=your_django_secret_key
5. Run Migrations & Start Server
Bash
python manage.py migrate
python manage.py runserver

👨‍💻 Developed By
Harsh Kasaudhan, Deepak Verma, Ankur Singh | B.Tech Computer Science | SRMCEM

🏆 Recognitions
Project Submissions: Google Solution Challenge 2026.

Team: Phantom X
