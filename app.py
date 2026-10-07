import os
import math
import time
import json
import sqlite3
import shutil
import secrets
from functools import wraps
from datetime import datetime
from urllib.parse import quote
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import email_service

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(24)
app.config['DATABASE'] = os.getenv('DATABASE', 'floodguard.db')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

ALERT_RADIUS_KM = float(os.getenv('ALERT_RADIUS_KM', 50))
WEATHER_ALERTS_CACHE = {}

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if genai and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini configuration note: {e}")


def get_db_path():
    """Centralized database path resolver with Vercel serverless /tmp support.

    A DATABASE_URL of the form ``sqlite:///path`` overrides the file location so
    persistent production storage can be pointed elsewhere later. Non-SQLite
    URLs are intentionally ignored here (they would require a real DB adapter);
    the app keeps using local SQLite so development never breaks.
    """
    database_url = os.getenv('DATABASE_URL', '').strip()
    if database_url.startswith('sqlite:///'):
        return database_url[len('sqlite:///'):]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_name = os.getenv('DATABASE', 'floodguard.db')

    if os.path.isabs(db_name):
        return db_name

    source_db = os.path.join(base_dir, db_name)

    if os.getenv('VERCEL'):
        tmp_db = os.path.join('/tmp', os.path.basename(db_name))
        if not os.path.exists(tmp_db) and os.path.exists(source_db):
            try:
                shutil.copyfile(source_db, tmp_db)
            except Exception as e:
                print(f"Warning copying DB to /tmp on Vercel: {e}")
        return tmp_db

    return source_db


def get_db():
    """Create and return a database connection with Row factory."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def _table_columns(cursor, table):
    return {row[1] for row in cursor.execute(f'PRAGMA table_info({table})')}


def _add_column(cursor, table, column, definition):
    if column not in _table_columns(cursor, table):
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


def _demo_seed_enabled():
    """Demo NGOs/alerts are seeded only for local development and tests.

    They are skipped on Vercel (production) or when SEED_DEMO_DATA is false so
    that fake organizations never appear in production data.
    """
    if os.getenv('VERCEL'):
        return False
    return os.getenv('SEED_DEMO_DATA', 'true').strip().lower() not in ('0', 'false', 'no', 'off')


def ensure_single_admin(conn):
    """Create or keep exactly one admin account from environment variables."""
    c = conn.cursor()
    admin_username = os.getenv('ADMIN_USERNAME', '').strip()
    admin_email = os.getenv('ADMIN_EMAIL', '').strip()
    admin_password = os.getenv('ADMIN_PASSWORD', '')

    keep_id = None
    if admin_username:
        env_user = c.execute('SELECT * FROM users WHERE username = ?', (admin_username,)).fetchone()
        if env_user:
            keep_id = env_user['id']
            c.execute(
                '''UPDATE users
                   SET user_type = 'admin', is_active = 1, login_id = COALESCE(NULLIF(login_id, ''), username)
                   WHERE id = ?''',
                (keep_id,)
            )
            if admin_email:
                c.execute('UPDATE users SET email = ? WHERE id = ?', (admin_email, keep_id))

    if keep_id is None:
        first_admin = c.execute(
            "SELECT id FROM users WHERE user_type = 'admin' ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if first_admin:
            keep_id = first_admin['id']

    if keep_id is None and admin_username and admin_password:
        hashed = generate_password_hash(admin_password)
        c.execute(
            '''INSERT INTO users (username, password, email, user_type, login_id, is_active, must_change_password)
               VALUES (?, ?, ?, 'admin', ?, 1, 0)''',
            (admin_username, hashed, admin_email or admin_username, admin_username)
        )
        keep_id = c.lastrowid

    if keep_id is not None:
        c.execute(
            "UPDATE users SET user_type = 'user' WHERE user_type = 'admin' AND id != ?",
            (keep_id,)
        )


def init_db():
    """Initialize database tables and seed default records idempotently."""
    try:
        conn = get_db()
        c = conn.cursor()

        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            user_type TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # NGOs table with UNIQUE name constraint
        c.execute('''CREATE TABLE IF NOT EXISTS ngos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            areas_of_operation TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS ngo_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_name TEXT NOT NULL,
            registration_no TEXT NOT NULL,
            contact_person TEXT NOT NULL,
            designation TEXT,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            pincode TEXT,
            areas_of_operation TEXT NOT NULL,
            description TEXT NOT NULL,
            website TEXT,
            status TEXT DEFAULT 'pending',
            rejection_reason TEXT,
            ngo_id INTEGER,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            FOREIGN KEY (ngo_id) REFERENCES ngos (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')

        # Volunteers table
        c.execute('''CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            skills TEXT NOT NULL,
            availability TEXT NOT NULL,
            ngo_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ngo_id) REFERENCES ngos (id)
        )''')

        # Alerts table
        c.execute('''CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            location TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Emergency Contacts table with UNIQUE name constraint
        c.execute('''CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            type TEXT NOT NULL,
            location TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Schema upgrades for existing databases
        _add_column(c, 'users', 'ngo_id', 'INTEGER')
        _add_column(c, 'users', 'login_id', 'TEXT')
        _add_column(c, 'users', 'must_change_password', 'INTEGER DEFAULT 0')
        _add_column(c, 'users', 'is_active', 'INTEGER DEFAULT 1')
        _add_column(c, 'ngos', 'registration_no', 'TEXT')
        _add_column(c, 'ngos', 'contact_person', 'TEXT')
        _add_column(c, 'ngos', 'city', 'TEXT')
        _add_column(c, 'ngos', 'state', 'TEXT')
        _add_column(c, 'ngos', 'description', 'TEXT')
        _add_column(c, 'ngos', 'website', 'TEXT')
        _add_column(c, 'ngos', 'status', "TEXT DEFAULT 'active'")
        _add_column(c, 'ngos', 'application_id', 'INTEGER')
        _add_column(c, 'ngos', 'user_id', 'INTEGER')
        _add_column(c, 'ngos', 'pincode', 'TEXT')
        _add_column(c, 'ngos', 'designation', 'TEXT')
        _add_column(c, 'ngo_applications', 'pincode', 'TEXT')
        _add_column(c, 'ngo_applications', 'designation', 'TEXT')

        c.execute("UPDATE users SET login_id = username WHERE login_id IS NULL OR login_id = ''")
        c.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
        c.execute("UPDATE users SET must_change_password = 0 WHERE must_change_password IS NULL")
        c.execute("UPDATE ngos SET status = 'active' WHERE status IS NULL OR status = ''")

        # Ensure unique indexes and cleanup any legacy duplicate records
        try:
            c.execute('DELETE FROM ngos WHERE rowid NOT IN (SELECT min(rowid) FROM ngos GROUP BY name)')
            c.execute('DELETE FROM emergency_contacts WHERE rowid NOT IN (SELECT min(rowid) FROM emergency_contacts GROUP BY name)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_ngos_name ON ngos(name)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_emergency_contacts_name ON emergency_contacts(name)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_login_id ON users(login_id)')
        except Exception as idx_err:
            print(f"Index creation note: {idx_err}")

        # Seed demo NGOs idempotently (local/tests only — never in production)
        if _demo_seed_enabled():
            sample_ngos = [
                ('Disaster Response Team India', 'drti@example.com', '9876543210', 'Mumbai, Maharashtra', 'Mumbai, Pune, Thane'),
                ('Flood Relief Foundation', 'frf@example.com', '8765432109', 'Kolkata, West Bengal', 'Kolkata, Howrah, Hooghly'),
                ('Coastal Rescue Organization', 'cro@example.com', '7654321098', 'Chennai, Tamil Nadu', 'Chennai, Pondicherry, Cuddalore'),
                ('Mountain Safety Network', 'msn@example.com', '6543210987', 'Dehradun, Uttarakhand', 'Dehradun, Rishikesh, Haridwar')
            ]
            for ngo in sample_ngos:
                c.execute('''INSERT OR IGNORE INTO ngos (name, email, phone, address, areas_of_operation)
                             VALUES (?, ?, ?, ?, ?)''', ngo)

        # Seed Emergency Contacts idempotently
        sample_contacts = [
            ('National Disaster Response Force', '1070', 'emergency', 'Nationwide'),
            ('National Emergency Helpline', '112', 'emergency', 'Nationwide'),
            ('Flood Control Room', '011-2389-2342', 'flood_control', 'Delhi / Regional'),
            ('Coastal Emergency Assistance', '044-2345-6789', 'coastal_emergency', 'Tamil Nadu / Coastal'),
            ('Mountain Rescue Network', '0135-2345-678', 'mountain_rescue', 'Uttarakhand / Hilly Regions'),
            ('Cyclone Warning Center', '033-2456-7890', 'cyclone_warning', 'Odisha & West Bengal')
        ]
        for contact in sample_contacts:
            c.execute('''INSERT OR IGNORE INTO emergency_contacts (name, phone, type, location)
                         VALUES (?, ?, ?, ?)''', contact)

        # Seed demo alerts only for local/tests, and only when the table is empty
        c.execute('SELECT COUNT(*) FROM alerts')
        if _demo_seed_enabled() and c.fetchone()[0] == 0:
            sample_alerts = [
                ('flood', 'Kochi, Kerala', 'warning', 'Heavy rainfall warning issued for coastal districts.', 9.9312, 76.2673),
                ('flood', 'Guwahati, Assam', 'critical', 'River Brahmaputra water level crossed danger level.', 26.1445, 91.7362),
                ('cyclone', 'Bhubaneswar, Odisha', 'info', 'Cyclone watch alert for northern coastal belt.', 20.2961, 85.8245),
                ('landslide', 'Shimla, Himachal Pradesh', 'warning', 'Heavy rainfall may cause localized landslides in hilly terrain.', 31.1048, 77.1734)
            ]
            for alert in sample_alerts:
                c.execute('''INSERT INTO alerts (type, location, severity, description, latitude, longitude)
                             VALUES (?, ?, ?, ?, ?, ?)''', alert)

        ensure_single_admin(conn)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")


try:
    init_db()
except Exception as e:
    print(f"Unhandled init_db exception: {e}")


@app.before_request
def enforce_password_change():
    if not session.get('must_change_password'):
        return None
    if request.endpoint in ('change_password', 'logout', 'static', None):
        return None
    if request.path.startswith('/static/'):
        return None
    return redirect(url_for('change_password'))


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance in kilometers between two geographic points."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def valid_coordinates(lat, lon):
    """Return True when lat/lon are real numbers within valid geographic ranges."""
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


SEVERITY_ORDER = {
    'extreme': 1,
    'critical': 2,
    'severe': 3,
    'warning': 4,
    'high': 4,
    'moderate': 5,
    'minor': 6,
    'advisory': 7,
    'info': 8,
    'green': 9,
    'safe': 9
}


def fetch_live_weather_alerts(user_lat, user_lon, radius_km=ALERT_RADIUS_KM):
    """Fetch live weather advisories from Open-Meteo and combine with local emergency database alerts."""
    cache_key = (round(user_lat, 2), round(user_lon, 2), float(radius_km))
    now = time.time()
    if cache_key in WEATHER_ALERTS_CACHE:
        cached_time, cached_data = WEATHER_ALERTS_CACHE[cache_key]
        if now - cached_time < 600:  # 10 minute cache TTL
            return cached_data

    alerts_list = []

    # 1. Open-Meteo Severe Weather & Forecast API
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={user_lat}&longitude={user_lon}&"
            f"current=weather_code,temperature_2m,wind_speed_10m,relative_humidity_2m&"
            f"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max&"
            f"timezone=auto"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get('current', {})
            daily = data.get('daily', {})
            weather_code = current.get('weather_code', 0)
            wind_speed = current.get('wind_speed_10m', 0)
            precip = daily.get('precipitation_sum', [0])[0] if daily.get('precipitation_sum') else 0

            # WMO Weather Codes: 95, 96, 99 = Thunderstorm; 65, 82 = Heavy Rain
            if weather_code in [95, 96, 99]:
                alerts_list.append({
                    'id': 'om-thunderstorm',
                    'type': 'Thunderstorm & Lightning Warning',
                    'severity': 'severe',
                    'location': f"Sector ({round(user_lat, 2)}, {round(user_lon, 2)})",
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'description': f'Active thunderstorm reported in your area with gusty winds ({wind_speed} km/h). Take shelter indoors.',
                    'start_time': current.get('time', datetime.now().strftime('%Y-%m-%d %H:%M')),
                    'end_time': 'Until weather system clears',
                    'source': 'Open-Meteo Severe Weather Alert',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            elif precip > 30 or weather_code in [65, 82]:
                alerts_list.append({
                    'id': 'om-heavy-rain',
                    'type': 'Heavy Rain & Waterlogging Advisory',
                    'severity': 'warning',
                    'location': f"District near ({round(user_lat, 2)}, {round(user_lon, 2)})",
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'description': f'Heavy rainfall expected ({precip} mm precipitation). High likelihood of local waterlogging in low-lying areas.',
                    'start_time': current.get('time', datetime.now().strftime('%Y-%m-%d %H:%M')),
                    'end_time': 'Next 12 Hours',
                    'source': 'Open-Meteo Severe Weather Alert',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            elif wind_speed > 45:
                alerts_list.append({
                    'id': 'om-high-wind',
                    'type': 'High Wind Advisory',
                    'severity': 'warning',
                    'location': f"Region near ({round(user_lat, 2)}, {round(user_lon, 2)})",
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'description': f'Gale force winds detected ({wind_speed} km/h). Drive carefully and avoid loose outdoor structures.',
                    'start_time': current.get('time', datetime.now().strftime('%Y-%m-%d %H:%M')),
                    'end_time': 'Next 6 Hours',
                    'source': 'Open-Meteo Severe Weather Alert',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    except Exception as e:
        print(f"Note: Could not query Open-Meteo live alerts: {e}")

    # 2. Query Database Emergency Alerts
    try:
        conn = get_db()
        c = conn.cursor()
        db_alerts = c.execute('SELECT * FROM alerts').fetchall()
        conn.close()
        for alert in db_alerts:
            a_lat = alert['latitude']
            a_lon = alert['longitude']
            dist = haversine_distance(user_lat, user_lon, a_lat, a_lon)
            if dist <= radius_km:
                alerts_list.append({
                    'id': f"db-{alert['id']}",
                    'type': str(alert['type']).capitalize() + ' Alert',
                    'severity': alert['severity'],
                    'location': alert['location'],
                    'latitude': a_lat,
                    'longitude': a_lon,
                    'description': alert['description'],
                    'start_time': str(alert['created_at']),
                    'end_time': 'Active until revoked',
                    'source': 'National Emergency Response Network',
                    'updated_at': str(alert['created_at'])
                })
    except Exception as e:
        print(f"Note: Error querying database alerts: {e}")

    # Calculate distance for each alert
    for alert in alerts_list:
        a_lat = alert.get('latitude', user_lat)
        a_lon = alert.get('longitude', user_lon)
        alert['distance_km'] = round(haversine_distance(user_lat, user_lon, a_lat, a_lon), 1)

    filtered_alerts = [a for a in alerts_list if a['distance_km'] <= radius_km]

    # Sort alerts: Severity rank -> Distance (closest first) -> Updated time
    filtered_alerts.sort(key=lambda x: (
        SEVERITY_ORDER.get(str(x.get('severity', '')).lower(), 99),
        x.get('distance_km', 0),
        x.get('updated_at', '')
    ))

    WEATHER_ALERTS_CACHE[cache_key] = (now, filtered_alerts)
    return filtered_alerts


def generate_gmail_compose_url(to_email, subject, body):
    """Generate a Gmail compose URL with pre-filled fields.
    Uses urllib.parse.quote for safe URL encoding.
    No SMTP, no credentials, no automatic sending."""
    return (
        'https://mail.google.com/mail/?view=cm&fs=1'
        '&to=' + quote(str(to_email), safe='@')
        + '&su=' + quote(str(subject), safe='')
        + '&body=' + quote(str(body), safe='')
    )


def get_row_value(row, key, default=None):
    """Safely retrieve a value from a sqlite3.Row object without using .get()."""
    if row is None:
        return default
    try:
        if key in row.keys():
            return row[key] if row[key] is not None else default
    except Exception:
        pass
    return default


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
        if session.get('user_type') != 'admin':
            flash('Access denied. Administrator privileges are required.', 'danger')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def ngo_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access the dashboard', 'danger')
            return redirect(url_for('login'))
        if session.get('user_type') != 'ngo':
            flash('Access denied. NGO privileges are required to access the dashboard.', 'danger')
            return redirect(url_for('index'))
        if not session.get('ngo_id'):
            flash('This NGO account is not linked to an approved organization.', 'danger')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def generate_ngo_login_id(conn):
    for _ in range(30):
        login_id = 'NGO-' + secrets.token_hex(3).upper()
        taken = conn.execute(
            'SELECT 1 FROM users WHERE username = ? OR login_id = ?',
            (login_id, login_id)
        ).fetchone()
        if not taken:
            return login_id
    return 'NGO-' + secrets.token_hex(8).upper()


def generate_temp_password():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(12))


def establish_session(user):
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['user_type'] = user['user_type']
    session['ngo_id'] = get_row_value(user, 'ngo_id')
    session['must_change_password'] = int(get_row_value(user, 'must_change_password', 0) or 0)


def post_login_redirect(user):
    if int(get_row_value(user, 'must_change_password', 0) or 0):
        return redirect(url_for('change_password'))
    if user['user_type'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    if user['user_type'] == 'ngo':
        return redirect(url_for('ngo_dashboard'))
    return redirect(url_for('index'))


def get_ngo_owned_volunteer(conn, volunteer_id, ngo_id):
    return conn.execute(
        'SELECT * FROM volunteers WHERE id = ? AND ngo_id = ?',
        (volunteer_id, ngo_id)
    ).fetchone()


def build_accept_email(volunteer, ngo_info):
    """Build acceptance email subject and body safely."""
    ngo_name = get_row_value(ngo_info, 'name', "CrisisAware Response Team")
    volunteer_name = get_row_value(volunteer, 'name', 'Volunteer')
    subject = f"Application Accepted - {ngo_name}"
    body = (f"Dear {volunteer_name},\n\n"
            f"We are pleased to inform you that your application to volunteer with {ngo_name} has been accepted.\n\n"
            f"We will provide you with further information regarding next steps.\n\n"
            f"Regards,\n{ngo_name}")
    return subject, body


def build_reject_email(volunteer, ngo_info, reason=None):
    """Build rejection email subject and body safely."""
    ngo_name = get_row_value(ngo_info, 'name', "CrisisAware Response Team")
    volunteer_name = get_row_value(volunteer, 'name', 'Volunteer')
    subject = f"Application Status - {ngo_name}"
    body = (f"Dear {volunteer_name},\n\n"
            f"Thank you for your interest and for taking the time to submit your volunteer application with {ngo_name}.\n\n"
            f"After reviewing your application, we regret to inform you that we are unable to proceed with your application at this time.\n")
    if reason:
        body += f"\nReason: {reason}\n"
    body += f"\nWe appreciate your willingness to support emergency response and wish you the best.\n\nRegards,\n{ngo_name}"
    return subject, body


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/map')
def map():
    return render_template('map.html')


@app.route('/alerts')
def alerts():
    conn = get_db()
    alerts_data = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('alerts.html', alerts=alerts_data)


@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    conn = get_db()
    ngos = conn.execute(
        "SELECT * FROM ngos WHERE COALESCE(status, 'active') = 'active' ORDER BY name"
    ).fetchall()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        skills = request.form.get('skills', '').strip()
        availability = request.form.get('availability', '').strip()
        ngo_id = request.form.get('ngo_id', '').strip()

        if not name or not email or not phone or not ngo_id:
            conn.close()
            flash('Please fill out all required fields, including the NGO you want to join.', 'danger')
            return redirect(url_for('volunteer'))

        ngo_row = conn.execute(
            "SELECT id FROM ngos WHERE id = ? AND COALESCE(status, 'active') = 'active'",
            (ngo_id,)
        ).fetchone()
        if not ngo_row:
            conn.close()
            flash('Please select a valid approved NGO.', 'danger')
            return redirect(url_for('volunteer'))

        conn.execute(
            'INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (name, email, phone, location, skills, availability, ngo_id)
        )
        conn.commit()
        conn.close()

        flash('Volunteer application submitted successfully!', 'success')
        return redirect(url_for('volunteer'))

    conn.close()
    return render_template('volunteer.html', ngos=ngos)


@app.route('/resources')
def resources():
    conn = get_db()
    contacts = conn.execute('SELECT * FROM emergency_contacts ORDER BY id ASC').fetchall()
    conn.close()
    return render_template('resources.html', contacts=contacts)


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        if not genai or not GEMINI_API_KEY:
            return jsonify({
                'response': 'CrisisAware AI Assistant is in standby mode (Gemini API key is not configured). For immediate emergency assistance, call the National Emergency Helpline at 112.'
            })

        data = request.get_json(silent=True) or {}
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'response': 'Please enter a question or emergency topic.'})
        if len(user_message) > 2000:
            return jsonify({'response': 'Your message is too long. Please keep it under 2000 characters so I can help quickly.'})

        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(
                f"You are an AI assistant for CrisisAware India, a comprehensive disaster management platform. "
                f"Provide concise, practical, and clear advice regarding disaster preparedness, safety measures, "
                f"evacuation guidelines, and flood/cyclone safety. User query: {user_message}"
            )
            return jsonify({'response': response.text})
        except Exception as e:
            return jsonify({
                'response': f'Emergency guidance service is temporarily busy. General advice: If facing immediate flooding or severe storm, move to higher ground and call 112. (Notice: {str(e)})'
            })

    return render_template('chatbot.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Dedicated administrator login. Only role=admin accounts may authenticate here."""
    if session.get('user_id') and session.get('user_type') == 'admin':
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR login_id = ?',
            (username, username)
        ).fetchone()

        pw_matches = False
        if user:
            stored_pw = user['password']
            if stored_pw.startswith('pbkdf2:') or stored_pw.startswith('scrypt:'):
                pw_matches = check_password_hash(stored_pw, password)
            elif stored_pw == password:
                pw_matches = True
                conn.execute('UPDATE users SET password = ? WHERE id = ?',
                             (generate_password_hash(password), user['id']))
                conn.commit()
                user = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()

        if pw_matches and user['user_type'] == 'admin' and int(get_row_value(user, 'is_active', 1) or 1) == 1:
            establish_session(user)
            conn.close()
            flash('Admin login successful!', 'success')
            return post_login_redirect(user)

        conn.close()
        flash('Invalid administrator credentials.', 'danger')

    return render_template('admin_login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR login_id = ?',
            (username, username)
        ).fetchone()

        if user:
            stored_pw = user['password']
            pw_matches = False

            if stored_pw.startswith('pbkdf2:') or stored_pw.startswith('scrypt:'):
                pw_matches = check_password_hash(stored_pw, password)
            else:
                if stored_pw == password:
                    pw_matches = True
                    new_hash = generate_password_hash(password)
                    conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_hash, user['id']))
                    conn.commit()
                    user = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()

            if pw_matches:
                if int(get_row_value(user, 'is_active', 1) or 1) != 1:
                    conn.close()
                    flash('This account is inactive. Contact the administrator.', 'danger')
                    return render_template('login.html')

                establish_session(user)
                conn.close()
                flash('Login successful!', 'success')
                return post_login_redirect(user)

        conn.close()
        flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        requested_type = request.form.get('user_type', 'user').strip().lower()

        if requested_type in ('ngo', 'admin'):
            flash('NGO accounts are created only after administrator approval. Please submit an NGO application.', 'info')
            return redirect(url_for('ngo_register'))

        if not username or not password or not email:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute(
                '''INSERT INTO users (username, password, email, user_type, login_id, is_active, must_change_password)
                   VALUES (?, ?, ?, 'user', ?, 1, 0)''',
                (username, hashed_password, email, username)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different username.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/ngo/register', methods=['GET', 'POST'])
def ngo_register():
    if request.method == 'POST':
        org_name = request.form.get('org_name', '').strip()
        registration_no = request.form.get('registration_no', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        designation = request.form.get('designation', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        pincode = request.form.get('pincode', '').strip()
        areas_of_operation = request.form.get('areas_of_operation', '').strip()
        description = request.form.get('description', '').strip()
        website = request.form.get('website', '').strip()

        required = {
            'Organization name': org_name,
            'Registration number': registration_no,
            'Contact person': contact_person,
            'Designation': designation,
            'Email': email,
            'Phone': phone,
            'Address': address,
            'City': city,
            'State': state,
            'Pincode': pincode,
            'Areas of operation': areas_of_operation,
            'Description': description,
        }
        missing = [label for label, value in required.items() if not value]
        if missing:
            flash('Please complete all required NGO details: ' + ', '.join(missing) + '.', 'danger')
            return render_template('ngo_register.html')

        if not pincode.isdigit() or len(pincode) != 6:
            flash('Pincode must be exactly 6 digits.', 'danger')
            return render_template('ngo_register.html')

        if not phone.isdigit() or len(phone) != 10:
            flash('Phone number must be exactly 10 digits.', 'danger')
            return render_template('ngo_register.html')

        conn = get_db()
        duplicate = conn.execute(
            '''SELECT id FROM ngo_applications
               WHERE status IN ('pending', 'approved')
                 AND (LOWER(email) = LOWER(?) OR LOWER(org_name) = LOWER(?))''',
            (email, org_name)
        ).fetchone()
        if duplicate:
            conn.close()
            flash('An application for this organization or email is already pending or approved.', 'danger')
            return render_template('ngo_register.html')

        name_taken = conn.execute('SELECT id FROM ngos WHERE LOWER(name) = LOWER(?)', (org_name,)).fetchone()
        if name_taken:
            conn.close()
            flash('An NGO with this name is already registered.', 'danger')
            return render_template('ngo_register.html')

        conn.execute(
            '''INSERT INTO ngo_applications (
                    org_name, registration_no, contact_person, designation, email, phone, address, city, state,
                    pincode, areas_of_operation, description, website, status
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')''',
            (org_name, registration_no, contact_person, designation, email, phone, address, city, state,
             pincode, areas_of_operation, description, website or None)
        )
        conn.commit()
        conn.close()

        emailed = email_service.send_application_received(email, org_name, contact_person)
        admin_email = os.getenv('ADMIN_EMAIL', '').strip()
        if admin_email:
            email_service.send_admin_new_application(admin_email, org_name, contact_person, email)
        if emailed:
            flash('Application submitted and awaiting admin approval. A confirmation email has been sent to you.', 'success')
        else:
            flash('Application submitted and awaiting admin approval. (Confirmation email could not be sent yet, but your application is stored.)', 'warning')
        return redirect(url_for('ngo_register'))

    return render_template('ngo_register.html')


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        if not current_password or not new_password:
            flash('Please fill out all password fields.', 'danger')
            return render_template('change_password.html')
        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('change_password.html')
        if len(new_password) < 8:
            flash('New password must be at least 8 characters.', 'danger')
            return render_template('change_password.html')

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or not check_password_hash(user['password'], current_password):
            conn.close()
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html')

        conn.execute(
            'UPDATE users SET password = ?, must_change_password = 0 WHERE id = ?',
            (generate_password_hash(new_password), user['id'])
        )
        conn.commit()
        conn.close()
        session['must_change_password'] = 0
        flash('Password updated successfully.', 'success')
        user_type = session.get('user_type')
        if user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        if user_type == 'ngo':
            return redirect(url_for('ngo_dashboard'))
        return redirect(url_for('index'))

    return render_template('change_password.html')


@app.route('/ngo/dashboard')
@ngo_required
def ngo_dashboard():
    ngo_id = session.get('ngo_id')
    conn = get_db()
    volunteers = conn.execute('''
        SELECT v.*, n.name as ngo_name
        FROM volunteers v
        LEFT JOIN ngos n ON v.ngo_id = n.id
        WHERE v.ngo_id = ?
        ORDER BY v.created_at DESC
    ''', (ngo_id,)).fetchall()
    ngo = conn.execute('SELECT * FROM ngos WHERE id = ?', (ngo_id,)).fetchone()
    conn.close()

    return render_template('ngo_dashboard.html', volunteers=volunteers, ngo=ngo)


@app.route('/volunteer/accept/<int:id>', methods=['POST'])
@ngo_required
def accept_volunteer(id):
    try:
        conn = get_db()
        volunteer_row = get_ngo_owned_volunteer(conn, id, session.get('ngo_id'))
        if not volunteer_row:
            flash('Unable to complete this action. Volunteer application not found.', 'danger')
            conn.close()
            return redirect(url_for('ngo_dashboard'))

        ngo_info = conn.execute('SELECT * FROM ngos WHERE id = ?', (volunteer_row['ngo_id'],)).fetchone()
        conn.execute("UPDATE volunteers SET status = 'Accepted' WHERE id = ?", (id,))
        conn.commit()
        conn.close()

        subject, body = build_accept_email(volunteer_row, ngo_info)
        gmail_url = generate_gmail_compose_url(volunteer_row['email'], subject, body)
        session['open_gmail_url'] = gmail_url
        flash('Application status set to Accepted. Email draft opened in Gmail — please review and click Send.', 'success')
    except Exception as e:
        print(f"Error in accept_volunteer: {e}")
        flash('Unable to complete this action. Please try again.', 'danger')

    return redirect(url_for('ngo_dashboard'))


@app.route('/volunteer/reject/<int:id>', methods=['POST'])
@ngo_required
def reject_volunteer(id):
    try:
        reason = request.form.get('reason', '').strip()
        conn = get_db()
        volunteer_row = get_ngo_owned_volunteer(conn, id, session.get('ngo_id'))
        if not volunteer_row:
            flash('Unable to complete this action. Volunteer application not found.', 'danger')
            conn.close()
            return redirect(url_for('ngo_dashboard'))

        ngo_info = conn.execute('SELECT * FROM ngos WHERE id = ?', (volunteer_row['ngo_id'],)).fetchone()
        conn.execute("UPDATE volunteers SET status = 'Rejected' WHERE id = ?", (id,))
        conn.commit()
        conn.close()

        subject, body = build_reject_email(volunteer_row, ngo_info, reason=reason)
        emailed = email_service.send_email(volunteer_row['email'], subject, body)
        if emailed:
            flash('Application status set to Rejected and the volunteer was emailed.', 'warning')
        else:
            flash('Application status set to Rejected, but the email could not be sent. Configure Gmail SMTP (MAIL_*) to deliver it.', 'warning')
    except Exception as e:
        print(f"Error in reject_volunteer: {e}")
        flash('Unable to complete this action. Please try again.', 'danger')

    return redirect(url_for('ngo_dashboard'))


@app.route('/volunteer/contact/<int:id>', methods=['POST'])
@ngo_required
def contact_volunteer(id):
    try:
        custom_subject = request.form.get('subject', '').strip()
        custom_msg = request.form.get('message', '').strip()
        conn = get_db()
        volunteer_row = get_ngo_owned_volunteer(conn, id, session.get('ngo_id'))
        if not volunteer_row:
            flash('Unable to complete this action. Volunteer application not found.', 'danger')
            conn.close()
            return redirect(url_for('ngo_dashboard'))

        ngo_info = conn.execute('SELECT * FROM ngos WHERE id = ?', (volunteer_row['ngo_id'],)).fetchone()
        conn.close()

        ngo_name = get_row_value(ngo_info, 'name', "CrisisAware Response Team")
        volunteer_name = get_row_value(volunteer_row, 'name', 'Volunteer')

        subject = custom_subject or f"Regarding your volunteer application - {ngo_name}"
        body = (f"Dear {volunteer_name},\n\n"
                f"{custom_msg or 'We are reaching out to discuss your volunteer application.'}\n\n"
                f"Regards,\n{ngo_name}")

        emailed = email_service.send_email(volunteer_row['email'], subject, body)
        if emailed:
            flash('Message sent to the volunteer.', 'success')
        else:
            flash('Message could not be sent. Configure Gmail SMTP (MAIL_*) in your environment.', 'danger')
    except Exception as e:
        print(f"Error in contact_volunteer: {e}")
        flash('Unable to complete this action. Please try again.', 'danger')

    return redirect(url_for('ngo_dashboard'))


def _create_or_reset_ngo_login(conn, application, admin_user_id, resend=False):
    """Create NGO org + user on first approval, or rotate password on resend. Returns (login_id, temp_password, created_new_user)."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    temp_password = generate_temp_password()
    hashed = generate_password_hash(temp_password)

    existing_user_id = application['user_id']
    ngo_id = application['ngo_id']

    if existing_user_id:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (existing_user_id,)).fetchone()
        if user:
            conn.execute(
                '''UPDATE users SET password = ?, must_change_password = 1, is_active = 1, user_type = 'ngo',
                   ngo_id = COALESCE(ngo_id, ?) WHERE id = ?''',
                (hashed, ngo_id, user['id'])
            )
            login_id = get_row_value(user, 'login_id') or user['username']
            if resend:
                conn.execute(
                    'UPDATE ngo_applications SET reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                    (now, admin_user_id, application['id'])
                )
            return login_id, temp_password, False

    login_id = generate_ngo_login_id(conn)
    if not ngo_id:
        ngo_cursor = conn.execute(
            '''INSERT INTO ngos (name, email, phone, address, areas_of_operation, registration_no,
                                 contact_person, designation, city, state, pincode, description, website, status, application_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)''',
            (application['org_name'], application['email'], application['phone'], application['address'],
             application['areas_of_operation'], application['registration_no'], application['contact_person'],
             get_row_value(application, 'designation'), application['city'], application['state'],
             get_row_value(application, 'pincode'), application['description'], application['website'],
             application['id'])
        )
        ngo_id = ngo_cursor.lastrowid
    else:
        conn.execute(
            '''UPDATE ngos SET email = ?, phone = ?, address = ?, areas_of_operation = ?, registration_no = ?,
               contact_person = ?, designation = ?, city = ?, state = ?, pincode = ?, description = ?, website = ?,
               status = 'active', application_id = ? WHERE id = ?''',
            (application['email'], application['phone'], application['address'], application['areas_of_operation'],
             application['registration_no'], application['contact_person'], get_row_value(application, 'designation'),
             application['city'], application['state'], get_row_value(application, 'pincode'),
             application['description'], application['website'], application['id'], ngo_id)
        )

    user_cursor = conn.execute(
        '''INSERT INTO users (username, password, email, user_type, ngo_id, login_id, must_change_password, is_active)
           VALUES (?, ?, ?, 'ngo', ?, ?, 1, 1)''',
        (login_id, hashed, application['email'], ngo_id, login_id)
    )
    user_id = user_cursor.lastrowid
    conn.execute('UPDATE ngos SET user_id = ? WHERE id = ?', (user_id, ngo_id))
    conn.execute(
        '''UPDATE ngo_applications
           SET status = 'approved', ngo_id = ?, user_id = ?, reviewed_at = ?, reviewed_by = ?, rejection_reason = NULL
           WHERE id = ?''',
        (ngo_id, user_id, now, admin_user_id, application['id'])
    )
    return login_id, temp_password, True


@app.route('/admin/dashboard')
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    applications = conn.execute(
        'SELECT * FROM ngo_applications ORDER BY created_at DESC'
    ).fetchall()
    ngos = conn.execute('SELECT * FROM ngos ORDER BY name').fetchall()
    admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'").fetchone()[0]
    conn.close()
    return render_template(
        'admin_dashboard.html',
        applications=applications,
        ngos=ngos,
        admin_count=admin_count
    )


@app.route('/admin/applications/<int:app_id>/approve', methods=['POST'])
@admin_required
def admin_approve_application(app_id):
    conn = get_db()
    application = conn.execute('SELECT * FROM ngo_applications WHERE id = ?', (app_id,)).fetchone()
    if not application:
        conn.close()
        flash('Application not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if application['status'] == 'approved' and application['user_id']:
        conn.close()
        flash('This application is already approved. Use Resend credentials if the NGO needs login details again.', 'info')
        return redirect(url_for('admin_dashboard'))

    try:
        login_id, temp_password, _created = _create_or_reset_ngo_login(
            conn, application, session['user_id'], resend=False
        )
        conn.commit()
        application = conn.execute('SELECT * FROM ngo_applications WHERE id = ?', (app_id,)).fetchone()
        conn.close()
    except sqlite3.IntegrityError as exc:
        conn.close()
        flash(f'Could not approve application (duplicate organization or login). {exc}', 'danger')
        return redirect(url_for('admin_dashboard'))

    emailed = email_service.send_application_approved(
        application['email'], application['org_name'], application['contact_person'], login_id, temp_password,
        login_url=url_for('login', _external=True)
    )
    if emailed:
        flash(f'{application["org_name"]} approved. Login ID {login_id} was emailed to {application["email"]}.', 'success')
    else:
        flash(f'{application["org_name"]} approved and login {login_id} created, but the email failed. Use Resend credentials.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/applications/<int:app_id>/reject', methods=['POST'])
@admin_required
def admin_reject_application(app_id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('A rejection reason is required to reject an application.', 'danger')
        return redirect(url_for('admin_dashboard'))
    conn = get_db()
    application = conn.execute('SELECT * FROM ngo_applications WHERE id = ?', (app_id,)).fetchone()
    if not application:
        conn.close()
        flash('Application not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    if application['status'] == 'approved' and application['user_id']:
        conn.close()
        flash('Approved applications cannot be rejected. The NGO account already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        '''UPDATE ngo_applications
           SET status = 'rejected', rejection_reason = ?, reviewed_at = ?, reviewed_by = ?
           WHERE id = ?''',
        (reason or None, now, session['user_id'], app_id)
    )
    conn.commit()
    conn.close()

    emailed = email_service.send_application_rejected(
        application['email'], application['org_name'], application['contact_person'], reason
    )
    if emailed:
        flash(f'{application["org_name"]} was rejected and the applicant was emailed.', 'warning')
    else:
        flash(f'{application["org_name"]} was rejected, but the email could not be sent.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/applications/<int:app_id>/resend', methods=['POST'])
@admin_required
def admin_resend_credentials(app_id):
    conn = get_db()
    application = conn.execute('SELECT * FROM ngo_applications WHERE id = ?', (app_id,)).fetchone()
    if not application:
        conn.close()
        flash('Application not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    if application['status'] != 'approved' or not application['user_id']:
        conn.close()
        flash('Credentials can only be resent for approved NGOs with an existing account.', 'danger')
        return redirect(url_for('admin_dashboard'))

    login_id, temp_password, created_new = _create_or_reset_ngo_login(
        conn, application, session['user_id'], resend=True
    )
    conn.commit()
    conn.close()
    if created_new:
        flash('Unexpected new account creation was blocked; please try approval again.', 'danger')
        return redirect(url_for('admin_dashboard'))

    emailed = email_service.send_credentials_resent(
        application['email'], application['org_name'], application['contact_person'], login_id, temp_password
    )
    if emailed:
        flash(f'New temporary password emailed to {application["email"]} for login {login_id}. No duplicate account was created.', 'success')
    else:
        flash('Password was reset on the existing account, but the email failed. Try resend again after checking SMTP settings.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/nearby-alerts', methods=['GET'])
def get_nearby_alerts():
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius = request.args.get('radius', default=ALERT_RADIUS_KM, type=float)

        if lat is None or lon is None:
            return jsonify({
                'status': 'error',
                'message': 'Latitude (lat) and longitude (lon) parameters are required.'
            }), 400

        if not valid_coordinates(lat, lon):
            return jsonify({
                'status': 'error',
                'message': 'Latitude must be between -90 and 90, longitude between -180 and 180.'
            }), 400

        radius = max(1.0, min(float(radius), 500.0))
        alerts_list = fetch_live_weather_alerts(lat, lon, radius)
        return jsonify({
            'status': 'success',
            'user_lat': lat,
            'user_lon': lon,
            'radius_km': radius,
            'count': len(alerts_list),
            'alerts': alerts_list
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to process nearby weather alerts: {str(e)}'
        }), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts_api():
    try:
        conn = get_db()
        alerts_rows = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
        conn.close()
        alerts_list = []
        for alert in alerts_rows:
            alerts_list.append({
                'id': alert['id'],
                'type': alert['type'],
                'location': alert['location'],
                'severity': alert['severity'],
                'description': alert['description'],
                'latitude': alert['latitude'],
                'longitude': alert['longitude'],
                'created_at': str(alert['created_at'])
            })
        return jsonify(alerts_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/emergency-contacts', methods=['GET'])
def get_emergency_contacts_api():
    try:
        conn = get_db()
        contacts = conn.execute('SELECT * FROM emergency_contacts ORDER BY id ASC').fetchall()
        conn.close()
        result = []
        for c in contacts:
            result.append({
                'id': c['id'],
                'name': c['name'],
                'phone': c['phone'],
                'type': c['type'],
                'location': c['location']
            })
        return jsonify({'status': 'success', 'contacts': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/nearby-places')
def nearby_places():
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius = request.args.get('radius', default=5000, type=int)
        place_type = request.args.get('type', default='hospital')

        if lat is None or lon is None:
            return jsonify({'elements': [], 'status': 'missing_coordinates'}), 400

        if not valid_coordinates(lat, lon):
            return jsonify({'elements': [], 'status': 'invalid_coordinates'}), 400

        # Clamp radius to a sane range (meters) to prevent abusive Overpass queries
        radius = max(100, min(int(radius), 50000))

        # Allowed types
        allowed_types = {'hospital', 'pharmacy', 'school'}
        if place_type not in allowed_types:
            return jsonify({'elements': [], 'status': 'invalid_place_type'}), 400

        # Overpass API query for nearby emergency places
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json][timeout:10];
        (
          node["amenity"="{place_type}"](around:{radius},{lat},{lon});
          way["amenity"="{place_type}"](around:{radius},{lat},{lon});
          relation["amenity"="{place_type}"](around:{radius},{lat},{lon});
        );
        out center;
        """

        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({'elements': [], 'status': f'upstream_error_{response.status_code}'}), 200
    except Exception as e:
        return jsonify({'elements': [], 'error': str(e)}), 200


@app.route('/api/alert', methods=['POST'])
@admin_required
def create_alert():
    try:
        data = request.get_json(silent=True) or {}
        required_fields = ['type', 'location', 'severity', 'description', 'latitude', 'longitude']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing field: {field}'}), 400

        if not valid_coordinates(data['latitude'], data['longitude']):
            return jsonify({'status': 'error', 'message': 'Invalid latitude/longitude.'}), 400

        conn = get_db()
        conn.execute(
            'INSERT INTO alerts (type, location, severity, description, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)',
            (str(data['type'])[:50], str(data['location'])[:120], str(data['severity'])[:20],
             str(data['description'])[:500], float(data['latitude']), float(data['longitude']))
        )
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(debug=is_debug)
