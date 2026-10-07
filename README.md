# CrisisAware - Disaster Response & Volunteer Management System

CrisisAware is a Python + Flask web application designed for disaster preparedness, real-time weather alerts, interactive emergency mapping, and NGO volunteer recruitment workflows with administrator-approved NGO onboarding and Gmail SMTP notifications. Deployment target is Vercel.

---

## 🚀 Features

- **Nearby Weather Alerts**: Fetches real-time weather advisories from Open-Meteo (with local caching and distance-based filtering) combined with regional disaster alerts from the emergency database.
- **Interactive Emergency Map**: Leaflet.js-powered map displaying nearby hospitals, pharmacies, emergency shelters/schools (via OpenStreetMap Overpass API with reliable fallbacks), custom user location pins, and turn-by-turn routing directions.
- **Volunteer Management System**: Volunteer application form with client-side & server-side validation.
- **NGO Application & Approval Workflow**: Public NGO registration stores a **pending** application (no login is created). A single administrator reviews applications at `/admin/dashboard`, and on approval the system creates the NGO record + login account, generates a unique login ID and a secure temporary password (via Python `secrets`), and emails the credentials. Rejection requires a reason. Administrators can resend credentials without creating duplicate accounts.
- **NGO Role-Based Dashboard**: Dedicated portal protected by strict server-side authentication and role authorization (`user_type == 'ngo'`), allowing coordinators to review, Accept, Reject, and Contact only their own NGO's volunteers.
- **Gmail SMTP Notifications**: Real transactional email via Python `smtplib`/`email` (no extra dependencies) for application-received, approval (with login ID, temporary password and login URL), rejection, credential-resend, and admin new-application notifications. Credentials are read only from environment variables and never exposed in source or frontend. If SMTP is not configured, emails are skipped gracefully and the workflow still functions.
- **Emergency Helplines Directory**: Database-backed emergency contact directory accessible on the resources page and via REST API.
- **AI Safety Assistant**: Optional Gemini AI chatbot providing practical disaster preparedness advice with graceful fallback when unconfigured.
- **Security & Password Hashing**: Werkzeug-powered password hashing (`scrypt`/`pbkdf2`), parameterized SQL queries, and secure session management.

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
Configure `.env`:
```env
SECRET_KEY=your_secure_random_secret_key
FLASK_DEBUG=True
ALERT_RADIUS_KM=50
DATABASE=floodguard.db
GEMINI_API_KEY=your_gemini_api_key_optional

# Exactly one administrator (created on startup if missing; password is hashed)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-admin-password

# Gmail SMTP (MAIL_PASSWORD must be a Google App Password, not your normal password)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_gmail_address@gmail.com
MAIL_PASSWORD=your_gmail_app_password
MAIL_DEFAULT_SENDER=your_gmail_address@gmail.com
```

### 5. Run the Local Server
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## 🌐 Production & Vercel Deployment

### Serverless Storage & Database Notes
- **Vercel Serverless Architecture**: Vercel functions execute in an ephemeral filesystem environment. For local demo/development, the SQLite database is automatically copied to `/tmp/floodguard.db` for write operations.
- **Production Database**: For permanent data persistence across container recycles, configure a hosted PostgreSQL database (e.g. Supabase, Neon, or Vercel Postgres) via `DATABASE_URL`.

### Deploying to Vercel
1. Push your repository to GitHub (ensure `.env` is listed in `.gitignore`):
   ```bash
   git add .
   git commit -m "Production deployment release"
   git push origin main
   ```
2. In [Vercel.com](https://vercel.com), click **Add New Project** and import the repository.
3. Configure Environment Variables in the Vercel dashboard (`SECRET_KEY`, `FLASK_DEBUG=False`, `ALERT_RADIUS_KM`, `GEMINI_API_KEY`, `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and the `MAIL_*` SMTP variables). Never commit real secrets to the repo.
4. Click **Deploy**. Vercel will build using `api/index.py` and `@vercel/python`.

---

## 🧪 Automated Testing

Execute the test suite covering authentication, authorization, volunteer workflows, Gmail URL generation, and API endpoints:
```bash
python test_crisis_aware.py
```

---

## 🛡️ Security & Privacy
- **No Hard-Coded Credentials**: All secrets and API keys are loaded strictly from environment variables.
- **Password Protection**: Passwords are never stored in plaintext; all user credentials use modern cryptographic hashing.
- **Transactional Email via SMTP**: NGO application/approval/rejection/resend emails are sent through Gmail SMTP using a Google App Password loaded from environment variables. Credentials are never hard-coded, logged, or exposed to the frontend, and email failures never block the underlying workflow.
- **Server-Side Authorization**: Every admin and NGO route re-checks the session role on the server (`admin_required` / `ngo_required`); hiding buttons is not relied upon for security. NGOs can only access their own data.
