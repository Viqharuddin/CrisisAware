# CrisisAware - Disaster Response & Volunteer Management System

CrisisAware is a Python Flask web application providing real-time emergency weather alerts, interactive mapping for emergency facilities, and an NGO volunteer management workflow with pre-filled Gmail notification integration.

---

## 🚀 Features

- **Nearby Weather Alerts**: Displays active emergency alerts within a customizable radius using the Open-Meteo & NWS API.
- **Interactive Emergency Map**: Real-time Leaflet map displaying nearby hospitals, pharmacies, emergency shelters, and custom user pins with routing/directions.
- **Volunteer Management System**: Dedicated NGO dashboard allowing organizers to review, Accept, Reject, or Contact volunteer applicants.
- **Gmail Compose Integration**: Pre-fills recipient, subject, and body in Gmail (`https://mail.google.com/mail/?view=cm&fs=1...`) for safe manual review without exposing SMTP credentials.
- **User Authentication**: Secure password-hashed login system for users and NGO emergency response administrators.

---

## 💻 Local Setup & Development

### 1. Prerequisites
- Python 3.8+
- Git

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone <your-repository-url>
cd crisisAware
python -m venv venv
```

Activate the virtual environment:
- **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
- **Linux / macOS**: `source venv/bin/activate`

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and set your configuration variables:
```env
SECRET_KEY=a_strong_random_secret_key_here
FLASK_DEBUG=True
ALERT_RADIUS_KM=50
DATABASE=floodguard.db
GEMINI_API_KEY=optional_gemini_api_key
```

### 5. Run the Local Server
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🌐 Production Deployment Guides

### Option A: Vercel Deployment (Serverless)

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Configure Vercel deployment"
   git push origin main
   ```
2. Log in to [Vercel.com](https://vercel.com) and click **Add New** → **Project**.
3. Import your GitHub repository.
4. Framework Preset: **Other** (Vercel automatically detects `vercel.json`).
5. Configure Environment Variables under **Environment Variables**:
   - `SECRET_KEY`: `<your-random-secret-key>`
   - `FLASK_DEBUG`: `False`
   - `ALERT_RADIUS_KM`: `50`
   - `DATABASE`: `floodguard.db`
6. Click **Deploy**. Vercel will deploy the application and provide a URL (e.g. `https://crisis-aware.vercel.app`).

### Option B: Render Deployment (WSGI Service)

1. Connect your repository on [Render.com](https://render.com/).
2. Select **New Web Service**.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Add Environment Variables (`SECRET_KEY`, `FLASK_DEBUG`, etc.).
6. Deploy to receive your public Render URL (`https://crisis-aware.onrender.com`).

---

## 🧪 Testing Live Deployment

After deployment, test the following key paths:
1. **Homepage**: `https://<your-app>.vercel.app/`
2. **Interactive Map**: `https://<your-app>.vercel.app/map`
3. **Weather Alerts**: `https://<your-app>.vercel.app/alerts`
4. **NGO Login**: Log in with authorized credentials at `/login`.
5. **Dashboard & Gmail Compose**: Navigate to `/ngo/dashboard`, click **Accept**, **Reject**, or **Contact** to verify that a pre-filled Gmail draft opens in a new tab.

---

## 🛡️ Security & Privacy
- Secrets and API credentials are kept out of source code and loaded strictly via environment variables.
- Passwords are securely hashed before database storage.
- No automatic SMTP sending occurs; all outbound applicant emails require human review in Gmail.
