# # app.py
# from flask import Flask, render_template, request, jsonify, session, redirect, url_for
# import sqlite3
# import json
# import requests
# from datetime import datetime
# import google.generativeai as genai
# import os
# from dotenv import load_dotenv

# load_dotenv()

# app = Flask(__name__)
# app.secret_key = os.urandom(24)
# app.config['DATABASE'] = 'floodguard.db'

# # Initialize Gemini AI
# GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# if GEMINI_API_KEY:
#     genai.configure(api_key=GEMINI_API_KEY)

# # Database initialization
# def init_db():
#     conn = sqlite3.connect(app.config['DATABASE'])
#     c = conn.cursor()
    
#     # Create users table
#     c.execute('''CREATE TABLE IF NOT EXISTS users
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
#                  username TEXT UNIQUE NOT NULL,
#                  password TEXT NOT NULL,
#                  email TEXT NOT NULL,
#                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
#     # Create volunteers table
#     c.execute('''CREATE TABLE IF NOT EXISTS volunteers
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
#                  name TEXT NOT NULL,
#                  email TEXT NOT NULL,
#                  phone TEXT NOT NULL,
#                  location TEXT NOT NULL,
#                  skills TEXT NOT NULL,
#                  availability TEXT NOT NULL,
#                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
#     # Create alerts table
#     c.execute('''CREATE TABLE IF NOT EXISTS alerts
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
#                  type TEXT NOT NULL,
#                  location TEXT NOT NULL,
#                  severity TEXT NOT NULL,
#                  description TEXT NOT NULL,
#                  latitude REAL NOT NULL,
#                  longitude REAL NOT NULL,
#                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
#     conn.commit()
#     conn.close()

# init_db()

# # Database helper function
# def get_db():
#     conn = sqlite3.connect(app.config['DATABASE'])
#     conn.row_factory = sqlite3.Row
#     return conn

# # Routes
# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/map')
# def map():
#     return render_template('map.html')

# @app.route('/alerts')
# def alerts():
#     db = get_db()
#     alerts = db.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
#     db.close()
#     return render_template('alerts.html', alerts=alerts)

# @app.route('/volunteer', methods=['GET', 'POST'])
# def volunteer():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         phone = request.form['phone']
#         location = request.form['location']
#         skills = request.form['skills']
#         availability = request.form['availability']
        
#         db = get_db()
#         db.execute('INSERT INTO volunteers (name, email, phone, location, skills, availability) VALUES (?, ?, ?, ?, ?, ?)',
#                   (name, email, phone, location, skills, availability))
#         db.commit()
#         db.close()
        
#         return render_template('volunteer.html', success=True)
    
#     return render_template('volunteer.html')

# @app.route('/resources')
# def resources():
#     return render_template('resources.html')

# @app.route('/chatbot', methods=['GET', 'POST'])
# def chatbot():
#     if request.method == 'POST':
#         if not GEMINI_API_KEY:
#             return jsonify({'response': 'Error: Gemini API key not configured'})
        
#         user_message = request.json['message']
        
#         try:
#             model = genai.GenerativeModel('gemini-2.5-flash')
#             response = model.generate_content(f"You are a helpful assistant for FloodGuard India, a disaster management platform. Provide helpful information about flood preparedness, safety measures, and disaster management. User query: {user_message}")
#             return jsonify({'response': response.text})
#         except Exception as e:
#             return jsonify({'response': f'Sorry, I encountered an error: {str(e)}'})
    
#     return render_template('chatbot.html')

# # API endpoints
# @app.route('/api/nearby-places')
# def nearby_places():
#     lat = request.args.get('lat', type=float)
#     lon = request.args.get('lon', type=float)
#     radius = request.args.get('radius', default=5000, type=int)
#     place_type = request.args.get('type', default='hospital')
    
#     # Overpass API query for nearby places
#     overpass_url = "http://overpass-api.de/api/interpreter"
#     overpass_query = f"""
#     [out:json];
#     (
#       node["amenity"="{place_type}"](around:{radius},{lat},{lon});
#       way["amenity"="{place_type}"](around:{radius},{lat},{lon});
#       relation["amenity"="{place_type}"](around:{radius},{lat},{lon});
#     );
#     out center;
#     """
    
#     try:
#         response = requests.get(overpass_url, params={'data': overpass_query})
#         data = response.json()
#         return jsonify(data)
#     except Exception as e:
#         return jsonify({'error': str(e)})

# @app.route('/api/alert', methods=['POST'])
# def create_alert():
#     data = request.json
#     db = get_db()
#     db.execute('INSERT INTO alerts (type, location, severity, description, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)',
#               (data['type'], data['location'], data['severity'], data['description'], data['latitude'], data['longitude']))
#     db.commit()
#     db.close()
#     return jsonify({'status': 'success'})

# if __name__ == '__main__':
#     app.run(debug=True)




# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3
import json
import requests
import math
import time
from datetime import datetime
from urllib.parse import quote
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(24)
app.config['DATABASE'] = os.getenv('DATABASE', 'floodguard.db')

ALERT_RADIUS_KM = float(os.getenv('ALERT_RADIUS_KM', 50))
WEATHER_ALERTS_CACHE = {}

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

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
    cache_key = (round(user_lat, 2), round(user_lon, 2), float(radius_km))
    now = time.time()
    if cache_key in WEATHER_ALERTS_CACHE:
        cached_time, cached_data = WEATHER_ALERTS_CACHE[cache_key]
        if now - cached_time < 600:  # 10 minute cache TTL
            return cached_data

    alerts_list = []
    
    # 1. Open-Meteo Severe Weather & Forecast API
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={user_lat}&longitude={user_lon}&current=weather_code,temperature_2m,wind_speed_10m,relative_humidity_2m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max&timezone=auto"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get('current', {})
            daily = data.get('daily', {})
            weather_code = current.get('weather_code', 0)
            wind_speed = current.get('wind_speed_10m', 0)
            precip = daily.get('precipitation_sum', [0])[0] if daily.get('precipitation_sum') else 0
            
            # WMO Weather Codes: 95,96,99 = Thunderstorm; 80,81,82 = Rain showers; 65 = Heavy rain; 75 = Heavy snow
            if weather_code in [95, 96, 99]:
                alerts_list.append({
                    'id': 'om-thunderstorm',
                    'type': 'Thunderstorm & Lightning Warning',
                    'severity': 'severe',
                    'location': f"Sector ({round(user_lat,2)}, {round(user_lon,2)})",
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'description': f'Active thunderstorm reported in your area with gusty winds ({wind_speed} km/h). Take shelter indoors.',
                    'start_time': current.get('time', datetime.now().strftime('%Y-%m-%d %H:%M')),
                    'end_time': 'Until weather system clears',
                    'source': 'Open-Meteo Severe Weather Warning',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            elif precip > 30 or weather_code in [65, 82]:
                alerts_list.append({
                    'id': 'om-heavy-rain',
                    'type': 'Heavy Rain & Waterlogging Advisory',
                    'severity': 'warning',
                    'location': f"District near ({round(user_lat,2)}, {round(user_lon,2)})",
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'description': f'Heavy rainfall expected ({precip} mm precipitation). High likelihood of local waterlogging in low-lying areas.',
                    'start_time': current.get('time', datetime.now().strftime('%Y-%m-%d %H:%M')),
                    'end_time': 'Next 12 Hours',
                    'source': 'Open-Meteo & IMD Advisory Feed',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            elif wind_speed > 45:
                alerts_list.append({
                    'id': 'om-high-wind',
                    'type': 'High Wind Advisory',
                    'severity': 'warning',
                    'location': f"Region near ({round(user_lat,2)}, {round(user_lon,2)})",
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'description': f'Gale force winds detected ({wind_speed} km/h). Drive carefully and avoid loose outdoor structures.',
                    'start_time': current.get('time', datetime.now().strftime('%Y-%m-%d %H:%M')),
                    'end_time': 'Next 6 Hours',
                    'source': 'Open-Meteo Wind Alert',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    except Exception as e:
        print(f"Note: Could not query Open-Meteo live alerts: {e}")

    # 2. Query SQLite database emergency alerts
    try:
        conn = sqlite3.connect('floodguard.db')
        conn.row_factory = sqlite3.Row
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

    # Filter out alerts beyond radius_km
    filtered_alerts = [a for a in alerts_list if a['distance_km'] <= radius_km]

    # Sort alerts by: 1) Severity rank 2) Distance (closest first) 3) Updated timestamp
    filtered_alerts.sort(key=lambda x: (
        SEVERITY_ORDER.get(str(x.get('severity', '')).lower(), 99),
        x.get('distance_km', 0),
        x.get('updated_at', '')
    ))

    WEATHER_ALERTS_CACHE[cache_key] = (now, filtered_alerts)
    return filtered_alerts

# Initialize Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_db_path():
    db_path = os.getenv('DATABASE', 'floodguard.db')
    if os.getenv('VERCEL') and not os.isabs(db_path):
        tmp_db = os.path.join('/tmp', os.path.basename(db_path))
        if not os.path.exists(tmp_db) and os.path.exists(db_path):
            import shutil
            shutil.copyfile(db_path, tmp_db)
        return tmp_db
    return db_path

# Database initialization
def init_db():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 email TEXT NOT NULL,
                 user_type TEXT DEFAULT 'user',
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create NGOs table
    c.execute('''CREATE TABLE IF NOT EXISTS ngos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 email TEXT NOT NULL,
                 phone TEXT NOT NULL,
                 address TEXT NOT NULL,
                 areas_of_operation TEXT NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create volunteers table
    c.execute('''CREATE TABLE IF NOT EXISTS volunteers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 email TEXT NOT NULL,
                 phone TEXT NOT NULL,
                 location TEXT NOT NULL,
                 skills TEXT NOT NULL,
                 availability TEXT NOT NULL,
                 ngo_id INTEGER,
                 status TEXT DEFAULT 'pending',
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (ngo_id) REFERENCES ngos (id))''')
    
    # Create alerts table
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 type TEXT NOT NULL,
                 location TEXT NOT NULL,
                 severity TEXT NOT NULL,
                 description TEXT NOT NULL,
                 latitude REAL NOT NULL,
                 longitude REAL NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Insert sample alerts if table is empty
    c.execute('SELECT COUNT(*) FROM alerts')
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO alerts (type, location, severity, description, latitude, longitude)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  ('flood', 'Kochi, Kerala', 'warning', 'Heavy rainfall warning issued for coastal districts.', 9.9312, 76.2673))
        c.execute('''INSERT INTO alerts (type, location, severity, description, latitude, longitude)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  ('flood', 'Guwahati, Assam', 'critical', 'River Brahmaputra water level crossed danger level.', 26.1445, 91.7362))
        c.execute('''INSERT INTO alerts (type, location, severity, description, latitude, longitude)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  ('cyclone', 'Bhubaneswar, Odisha', 'info', 'Cyclone watch alert for northern coastal belt.', 20.2961, 85.8245))

    # Insert sample NGOs
    c.execute('''INSERT OR IGNORE INTO ngos (name, email, phone, address, areas_of_operation) 
                 VALUES (?, ?, ?, ?, ?)''', 
              ('Disaster Response Team India', 'drti@example.com', '9876543210', 
               'Mumbai, Maharashtra', 'Mumbai, Pune, Thane'))
    
    c.execute('''INSERT OR IGNORE INTO ngos (name, email, phone, address, areas_of_operation) 
                 VALUES (?, ?, ?, ?, ?)''', 
              ('Flood Relief Foundation', 'frf@example.com', '8765432109', 
               'Kolkata, West Bengal', 'Kolkata, Howrah, Hooghly'))
    
    conn.commit()
    conn.close()

init_db()

# Database helper function
def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map():
    return render_template('map.html')

# @app.route('/alerts')
# def alerts():
#     db = get_db()
#     alerts = db.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
#     db.close()
#     return render_template('alerts.html', alerts=alerts)

# @app.route('/volunteer', methods=['GET', 'POST'])
# def volunteer():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         phone = request.form['phone']
#         location = request.form['location']
#         skills = request.form['skills']
#         availability = request.form['availability']
#         ngo_id = request.form.get('ngo_id', 1)  # Default to first NGO
        
#         db = get_db()
#         db.execute('INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
#                   (name, email, phone, location, skills, availability, ngo_id))
#         db.commit()
#         db.close()
        
        # flash('Your volunteer application has been submitted successfully! The NGO will contact you soon.', 'success')
        # return redirect(url_for('volunteer'))
    
#     db = get_db()
#     ngos = db.execute('SELECT * FROM ngos').fetchall()
#     db.close()
    
#     return render_template('volunteer.html', ngos=ngos)


# @app.route('/alerts')
# def alerts():
#     alerts = db.get_all_alerts()
#     return render_template('alerts.html', alerts=alerts)

@app.route('/alerts')
def alerts():
    conn = get_db()
    alerts = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('alerts.html', alerts=alerts)


@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        location = request.form['location']
        skills = request.form['skills']
        availability = request.form['availability']
        ngo_id = request.form.get('ngo_id', 1)  # Default to first NGO

        conn = get_db()
        conn.execute('INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (name, email, phone, location, skills, availability, ngo_id))
        conn.commit()
        conn.close()

        flash('Volunteer application submitted successfully!', 'success')
        return redirect(url_for('volunteer'))

    conn = get_db()
    ngos = conn.execute('SELECT * FROM ngos').fetchall()
    conn.close()
    
    return render_template('volunteer.html', ngos=ngos)



# @app.route('/volunteer', methods=['GET', 'POST'])
# def volunteer():
#     if request.method == 'POST':
#         # Get form data
#         name = request.form['name']
#         email = request.form['email']
#         # ... other fields
        
#         # Save to database
#         success = db.create_volunteer(name, email, phone, location, skills, availability, ngo_id)
# @app.route('/volunteer', methods=['GET', 'POST'])
# def volunteer():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         phone = request.form['phone']
#         location = request.form['location']
#         skills = request.form['skills']
#         availability = request.form['availability']
#         ngo_id = request.form.get('ngo_id', 1)  # Default to first NGO
        
#         db = get_db()
#         db.execute('INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
#                   (name, email, phone, location, skills, availability, ngo_id))
#         db.commit()
#         db.close()
#         success = db.create_volunteer(name, email, phone, location, skills, availability, ngo_id)

        
#         if success:
#             flash('Application submitted successfully!', 'success')
#             return redirect(url_for('volunteer'))
#         else:
#             flash('Error submitting application. Please try again.', 'danger')
    
#     ngos = db.get_all_ngos()
#     return render_template('volunteer.html', ngos=ngos)

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        if not GEMINI_API_KEY:
            return jsonify({'response': 'Error: Gemini API key not configured'})
        
        user_message = request.json['message']
        
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(f"You are a helpful assistant for CrisisAware India, a disaster management platform. Provide helpful information about Disaster preparedness, safety measures, and disaster management. User query: {user_message}")
            return jsonify({'response': response.text})
        except Exception as e:
            return jsonify({'response': f'Sorry, I encountered an error: {str(e)}'})
    
    return render_template('chatbot.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                         (username, password)).fetchone()
        db.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_type'] = user['user_type']
            flash('Login successful!', 'success')
            
            if user['user_type'] == 'ngo':
                return redirect(url_for('ngo_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        user_type = request.form['user_type']
        
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, email, user_type) VALUES (?, ?, ?, ?)',
                      (username, password, email, user_type))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'danger')
        finally:
            db.close()
    
    return render_template('register.html')

@app.route('/ngo/dashboard')
def ngo_dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard', 'danger')
        return redirect(url_for('login'))
    
    db = get_db()
    volunteers = db.execute('''SELECT v.*, n.name as ngo_name 
                             FROM volunteers v 
                             LEFT JOIN ngos n ON v.ngo_id = n.id 
                             ORDER BY v.created_at DESC''').fetchall()
    db.close()
    
    return render_template('ngo_dashboard.html', volunteers=volunteers)

def generate_gmail_compose_url(to_email, subject, body):
    """Generate a Gmail compose URL with pre-filled fields.
    Uses urllib.parse.quote for safe URL encoding.
    No SMTP, no credentials, no automatic sending.
    The admin must manually click Send inside Gmail."""
    return (
        'https://mail.google.com/mail/?view=cm&fs=1'
        '&to=' + quote(to_email, safe='@')
        + '&su=' + quote(subject, safe='')
        + '&body=' + quote(body, safe='')
    )

def build_accept_email(volunteer, ngo_info):
    """Build the acceptance email subject and body."""
    ngo_name = ngo_info['name'] if (ngo_info and ngo_info.get('name')) else "CrisisAware Response Team"
    subject = f"Application Accepted - {ngo_name}"
    body = (f"Dear {volunteer['name']},\n\n"
            f"We are pleased to inform you that your application has been accepted.\n\n"
            f"We will provide you with further information regarding the next steps.\n\n"
            f"Regards,\n{ngo_name}")
    return subject, body

def build_reject_email(volunteer, ngo_info, reason=None):
    """Build the rejection email subject and body."""
    ngo_name = ngo_info['name'] if (ngo_info and ngo_info.get('name')) else "CrisisAware Response Team"
    subject = f"Application Status - {ngo_name}"
    body = (f"Dear {volunteer['name']},\n\n"
            f"Thank you for your interest and for taking the time to submit your application.\n\n"
            f"After reviewing your application, we regret to inform you that "
            f"we are unable to proceed with your application at this time.\n")
    if reason:
        body += f"\nReason: {reason}\n"
    body += (f"\nWe appreciate your interest and wish you the best.\n\n"
             f"Regards,\n{ngo_name}")
    return subject, body


@app.route('/volunteer/accept/<int:id>', methods=['POST'])
def accept_volunteer(id):
    if 'user_id' not in session:
        flash('Please login to perform this action', 'danger')
        return redirect(url_for('login'))
    
    try:
        db = get_db()
        volunteer = db.execute('SELECT * FROM volunteers WHERE id = ?', (id,)).fetchone()
        if not volunteer:
            flash('Unable to complete this action. Volunteer application not found.', 'danger')
            db.close()
            return redirect(url_for('ngo_dashboard'))

        ngo_info = None
        if volunteer['ngo_id']:
            ngo_info = db.execute('SELECT * FROM ngos WHERE id = ?', (volunteer['ngo_id'],)).fetchone()

        db.execute("UPDATE volunteers SET status = 'Accepted' WHERE id = ?", (id,))
        db.commit()
        db.close()

        subject, body = build_accept_email(volunteer, ngo_info)
        gmail_url = generate_gmail_compose_url(volunteer['email'], subject, body)
        session['open_gmail_url'] = gmail_url
        flash('Application status set to Accepted. Email draft opened in Gmail — please review and click Send.', 'success')
    except Exception as e:
        print(f"Error in accept_volunteer: {e}")
        flash('Unable to complete this action. Please try again.', 'danger')

    return redirect(url_for('ngo_dashboard'))

@app.route('/volunteer/reject/<int:id>', methods=['POST'])
def reject_volunteer(id):
    if 'user_id' not in session:
        flash('Please login to perform this action', 'danger')
        return redirect(url_for('login'))
    
    try:
        reason = request.form.get('reason', '').strip()
        db = get_db()
        volunteer = db.execute('SELECT * FROM volunteers WHERE id = ?', (id,)).fetchone()
        if not volunteer:
            flash('Unable to complete this action. Volunteer application not found.', 'danger')
            db.close()
            return redirect(url_for('ngo_dashboard'))

        ngo_info = None
        if volunteer['ngo_id']:
            ngo_info = db.execute('SELECT * FROM ngos WHERE id = ?', (volunteer['ngo_id'],)).fetchone()

        db.execute("UPDATE volunteers SET status = 'Rejected' WHERE id = ?", (id,))
        db.commit()
        db.close()

        subject, body = build_reject_email(volunteer, ngo_info, reason=reason)
        gmail_url = generate_gmail_compose_url(volunteer['email'], subject, body)
        session['open_gmail_url'] = gmail_url
        flash('Application status set to Rejected. Email draft opened in Gmail — please review and click Send.', 'warning')
    except Exception as e:
        print(f"Error in reject_volunteer: {e}")
        flash('Unable to complete this action. Please try again.', 'danger')

    return redirect(url_for('ngo_dashboard'))

@app.route('/volunteer/contact/<int:id>', methods=['POST'])
def contact_volunteer(id):
    if 'user_id' not in session:
        flash('Please login to perform this action', 'danger')
        return redirect(url_for('login'))
    
    try:
        custom_subject = request.form.get('subject', '').strip() or "Regarding your volunteer application"
        custom_msg = request.form.get('message', '').strip() or "We are reaching out to discuss your volunteer application."
        db = get_db()
        volunteer = db.execute('SELECT * FROM volunteers WHERE id = ?', (id,)).fetchone()
        if not volunteer:
            flash('Unable to complete this action. Volunteer application not found.', 'danger')
            db.close()
            return redirect(url_for('ngo_dashboard'))

        ngo_info = None
        if volunteer['ngo_id']:
            ngo_info = db.execute('SELECT * FROM ngos WHERE id = ?', (volunteer['ngo_id'],)).fetchone()
        db.close()

        ngo_name = ngo_info['name'] if (ngo_info and ngo_info.get('name')) else "CrisisAware Response Team"
        body = (f"Dear {volunteer['name']},\n\n"
                f"{custom_msg}\n\n"
                f"Regards,\n{ngo_name}")

        gmail_url = generate_gmail_compose_url(volunteer['email'], custom_subject, body)
        session['open_gmail_url'] = gmail_url
        flash('Email draft opened in Gmail. Please review and click Send.', 'info')
    except Exception as e:
        print(f"Error in contact_volunteer: {e}")
        flash('Unable to complete this action. Please try again.', 'danger')

    return redirect(url_for('ngo_dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# API endpoints
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

        alerts = fetch_live_weather_alerts(lat, lon, radius)
        return jsonify({
            'status': 'success',
            'user_lat': lat,
            'user_lon': lon,
            'radius_km': radius,
            'count': len(alerts),
            'alerts': alerts
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to process nearby weather alerts: {str(e)}'
        }), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts_api():
    db = get_db()
    alerts = db.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
    db.close()
    alerts_list = []
    for alert in alerts:
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

@app.route('/api/nearby-places')
def nearby_places():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', default=5000, type=int)
    place_type = request.args.get('type', default='hospital')
    
    # Overpass API query for nearby places
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="{place_type}"](around:{radius},{lat},{lon});
      way["amenity"="{place_type}"](around:{radius},{lat},{lon});
      relation["amenity"="{place_type}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/alert', methods=['POST'])
def create_alert():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO alerts (type, location, severity, description, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)',
              (data['type'], data['location'], data['severity'], data['description'], data['latitude'], data['longitude']))
    db.commit()
    db.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(debug=is_debug)



