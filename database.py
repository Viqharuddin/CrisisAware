# database.py
import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path='floodguard.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Create and return a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = self.get_connection()
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
        
        # Create emergency_contacts table
        c.execute('''CREATE TABLE IF NOT EXISTS emergency_contacts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     phone TEXT NOT NULL,
                     type TEXT NOT NULL,
                     location TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Insert sample NGOs if they don't exist
        self._insert_sample_ngos(c)
        
        # Insert sample emergency contacts
        self._insert_sample_contacts(c)
        
        # Insert sample alerts
        self._insert_sample_alerts(c)
        
        conn.commit()
        conn.close()
    
    def _insert_sample_ngos(self, cursor):
        """Insert sample NGO data"""
        ngos = [
            ('Disaster Response Team India', 'drti@example.com', '9876543210', 
             'Mumbai, Maharashtra', 'Mumbai, Pune, Thane'),
            ('Flood Relief Foundation', 'frf@example.com', '8765432109', 
             'Kolkata, West Bengal', 'Kolkata, Howrah, Hooghly'),
            ('Coastal Rescue Organization', 'cro@example.com', '7654321098',
             'Chennai, Tamil Nadu', 'Chennai, Pondicherry, Cuddalore'),
            ('Mountain Safety Network', 'msn@example.com', '6543210987',
             'Dehradun, Uttarakhand', 'Dehradun, Rishikesh, Haridwar')
        ]
        
        for ngo in ngos:
            cursor.execute('''INSERT OR IGNORE INTO ngos (name, email, phone, address, areas_of_operation) 
                             VALUES (?, ?, ?, ?, ?)''', ngo)
    
    def _insert_sample_contacts(self, cursor):
        """Insert sample emergency contacts"""
        contacts = [
            ('National Disaster Response Force', '1070', 'emergency', 'Nationwide'),
            ('Emergency Helpline', '112', 'emergency', 'Nationwide'),
            ('Flood Control Room', '011-2389-2342', 'flood_control', 'Delhi'),
            ('Coastal Emergency', '044-2345-6789', 'coastal_emergency', 'Tamil Nadu'),
            ('Mountain Rescue', '0135-2345-678', 'mountain_rescue', 'Uttarakhand'),
            ('Cyclone Warning Center', '033-2456-7890', 'cyclone_warning', 'West Bengal')
        ]
        
        for contact in contacts:
            cursor.execute('''INSERT OR IGNORE INTO emergency_contacts (name, phone, type, location) 
                             VALUES (?, ?, ?, ?)''', contact)
    
    def _insert_sample_alerts(self, cursor):
        """Insert sample alert data"""
        alerts = [
            ('flood', 'Kerala, Kochi', 'warning', 
             'Heavy rainfall expected in the next 24 hours', 9.9312, 76.2673),
            ('flood', 'Assam, Guwahati', 'critical', 
             'River water levels rising rapidly', 26.1445, 91.7362),
            ('cyclone', 'Odisha, Bhubaneswar', 'info', 
             'Cyclone watch issued for coastal areas', 20.2961, 85.8245),
            ('landslide', 'Himachal Pradesh, Shimla', 'warning', 
             'Heavy rains may cause landslides in hilly areas', 31.1048, 77.1734)
        ]
        
        for alert in alerts:
            cursor.execute('''INSERT OR IGNORE INTO alerts (type, location, severity, description, latitude, longitude) 
                             VALUES (?, ?, ?, ?, ?, ?)''', alert)
    
    def get_user_by_credentials(self, username, password):
        """Get user by username and password"""
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                           (username, password)).fetchone()
        conn.close()
        return user
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return user
    
    def create_user(self, username, password, email, user_type='user'):
        """Create a new user"""
        conn = self.get_connection()
        try:
            conn.execute('INSERT INTO users (username, password, email, user_type) VALUES (?, ?, ?, ?)',
                        (username, password, email, user_type))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_all_ngos(self):
        """Get all NGOs"""
        conn = self.get_connection()
        ngos = conn.execute('SELECT * FROM ngos ORDER BY name').fetchall()
        conn.close()
        return ngos
    
    def get_ngo_by_id(self, ngo_id):
        """Get NGO by ID"""
        conn = self.get_connection()
        ngo = conn.execute('SELECT * FROM ngos WHERE id = ?', (ngo_id,)).fetchone()
        conn.close()
        return ngo
    
    def create_volunteer(self, name, email, phone, location, skills, availability, ngo_id=None):
        """Create a new volunteer application"""
        conn = self.get_connection()
        try:
            conn.execute('''INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (name, email, phone, location, skills, availability, ngo_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating volunteer: {e}")
            return False
        finally:
            conn.close()
    
    def get_volunteers_by_ngo(self, ngo_id):
        """Get all volunteers for a specific NGO"""
        conn = self.get_connection()
        volunteers = conn.execute('''SELECT v.*, n.name as ngo_name 
                                  FROM volunteers v 
                                  JOIN ngos n ON v.ngo_id = n.id 
                                  WHERE v.ngo_id = ?
                                  ORDER BY v.created_at DESC''', (ngo_id,)).fetchall()
        conn.close()
        return volunteers
    
    def get_all_volunteers(self):
        """Get all volunteers"""
        conn = self.get_connection()
        volunteers = conn.execute('''SELECT v.*, n.name as ngo_name 
                                  FROM volunteers v 
                                  LEFT JOIN ngos n ON v.ngo_id = n.id 
                                  ORDER BY v.created_at DESC''').fetchall()
        conn.close()
        return volunteers
    
    def update_volunteer_status(self, volunteer_id, status):
        """Update volunteer application status"""
        conn = self.get_connection()
        try:
            conn.execute('UPDATE volunteers SET status = ? WHERE id = ?', (status, volunteer_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating volunteer status: {e}")
            return False
        finally:
            conn.close()
    
    def create_alert(self, alert_type, location, severity, description, latitude, longitude):
        """Create a new alert"""
        conn = self.get_connection()
        try:
            conn.execute('''INSERT INTO alerts (type, location, severity, description, latitude, longitude) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                        (alert_type, location, severity, description, latitude, longitude))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating alert: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_alerts(self):
        """Get all alerts"""
        conn = self.get_connection()
        alerts = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
        conn.close()
        return alerts
    
    def get_recent_alerts(self, limit=5):
        """Get recent alerts"""
        conn = self.get_connection()
        alerts = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
        conn.close()
        return alerts
    
    def get_alerts_by_location(self, latitude, longitude, radius_km=50):
        """Get alerts within a certain radius of a location"""
        conn = self.get_connection()
        # Simple approximation for demo purposes
        alerts = conn.execute('''SELECT * FROM alerts 
                              WHERE ABS(latitude - ?) < ? AND ABS(longitude - ?) < ?
                              ORDER BY created_at DESC''', 
                             (latitude, radius_km/100, longitude, radius_km/100)).fetchall()
        conn.close()
        return alerts
    
    def get_emergency_contacts(self, contact_type=None):
        """Get emergency contacts, optionally filtered by type"""
        conn = self.get_connection()
        if contact_type:
            contacts = conn.execute('SELECT * FROM emergency_contacts WHERE type = ? ORDER BY name', 
                                   (contact_type,)).fetchall()
        else:
            contacts = conn.execute('SELECT * FROM emergency_contacts ORDER BY type, name').fetchall()
        conn.close()
        return contacts
    
    def search_nearby_ngos(self, location):
        """Search for NGOs near a location (simplified for demo)"""
        conn = self.get_connection()
        # Simple text-based search for demo
        ngos = conn.execute('''SELECT * FROM ngos 
                            WHERE areas_of_operation LIKE ? 
                            OR address LIKE ? 
                            ORDER BY name''', 
                           (f'%{location}%', f'%{location}%')).fetchall()
        conn.close()
        return ngos

# Create a global database instance
db = Database()