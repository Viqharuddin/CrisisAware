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
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['DATABASE'] = 'floodguard.db'

# Initialize Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Database initialization
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
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
    conn = sqlite3.connect(app.config['DATABASE'])
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
            response = model.generate_content(f"You are a helpful assistant for FloodGuard India, a disaster management platform. Provide helpful information about flood preparedness, safety measures, and disaster management. User query: {user_message}")
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
    if 'user_id' not in session or session.get('user_type') != 'ngo':
        flash('Please login as NGO to access this page', 'danger')
        return redirect(url_for('login'))
    
    db = get_db()
    volunteers = db.execute('''SELECT v.*, n.name as ngo_name 
                             FROM volunteers v 
                             JOIN ngos n ON v.ngo_id = n.id 
                             ORDER BY v.created_at DESC''').fetchall()
    db.close()
    
    return render_template('ngo_dashboard.html', volunteers=volunteers)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# API endpoints
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
    app.run(debug=True)



