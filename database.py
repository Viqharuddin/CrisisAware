# database.py
import sqlite3
import os
import shutil
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


def get_db_path():
    """Resolve database file path across local and Vercel serverless environments."""
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
                print(f"Warning copying DB to /tmp: {e}")
        return tmp_db

    return source_db


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.init_db()

    def get_connection(self):
        """Create and return a database connection with Row factory"""
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database with required tables idempotently"""
        conn = self.get_connection()
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

        # Ensure unique indexes and cleanup any legacy duplicate records
        try:
            c.execute('DELETE FROM ngos WHERE rowid NOT IN (SELECT min(rowid) FROM ngos GROUP BY name)')
            c.execute('DELETE FROM emergency_contacts WHERE rowid NOT IN (SELECT min(rowid) FROM emergency_contacts GROUP BY name)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_ngos_name ON ngos(name)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_emergency_contacts_name ON emergency_contacts(name)')
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        except Exception as idx_err:
            print(f"Index creation note: {idx_err}")

        # Seed NGOs idempotently
        self._insert_sample_ngos(c)

        # Seed Emergency Contacts idempotently
        self._insert_sample_contacts(c)

        # Seed Alerts idempotently
        self._insert_sample_alerts(c)

        conn.commit()
        conn.close()

    def _insert_sample_ngos(self, cursor):
        ngos = [
            ('Disaster Response Team India', 'drti@example.com', '9876543210', 'Mumbai, Maharashtra', 'Mumbai, Pune, Thane'),
            ('Flood Relief Foundation', 'frf@example.com', '8765432109', 'Kolkata, West Bengal', 'Kolkata, Howrah, Hooghly'),
            ('Coastal Rescue Organization', 'cro@example.com', '7654321098', 'Chennai, Tamil Nadu', 'Chennai, Pondicherry, Cuddalore'),
            ('Mountain Safety Network', 'msn@example.com', '6543210987', 'Dehradun, Uttarakhand', 'Dehradun, Rishikesh, Haridwar')
        ]
        for ngo in ngos:
            cursor.execute('''INSERT OR IGNORE INTO ngos (name, email, phone, address, areas_of_operation) 
                             VALUES (?, ?, ?, ?, ?)''', ngo)

    def _insert_sample_contacts(self, cursor):
        contacts = [
            ('National Disaster Response Force', '1070', 'emergency', 'Nationwide'),
            ('National Emergency Helpline', '112', 'emergency', 'Nationwide'),
            ('Flood Control Room', '011-2389-2342', 'flood_control', 'Delhi / Regional'),
            ('Coastal Emergency Assistance', '044-2345-6789', 'coastal_emergency', 'Tamil Nadu / Coastal'),
            ('Mountain Rescue Network', '0135-2345-678', 'mountain_rescue', 'Uttarakhand / Hilly Regions'),
            ('Cyclone Warning Center', '033-2456-7890', 'cyclone_warning', 'Odisha & West Bengal')
        ]
        for contact in contacts:
            cursor.execute('''INSERT OR IGNORE INTO emergency_contacts (name, phone, type, location) 
                             VALUES (?, ?, ?, ?)''', contact)

    def _insert_sample_alerts(self, cursor):
        cursor.execute('SELECT COUNT(*) FROM alerts')
        if cursor.fetchone()[0] == 0:
            alerts = [
                ('flood', 'Kerala, Kochi', 'warning', 'Heavy rainfall expected in the next 24 hours', 9.9312, 76.2673),
                ('flood', 'Assam, Guwahati', 'critical', 'River water levels rising rapidly', 26.1445, 91.7362),
                ('cyclone', 'Odisha, Bhubaneswar', 'info', 'Cyclone watch issued for coastal areas', 20.2961, 85.8245),
                ('landslide', 'Himachal Pradesh, Shimla', 'warning', 'Heavy rains may cause landslides in hilly areas', 31.1048, 77.1734)
            ]
            for alert in alerts:
                cursor.execute('''INSERT INTO alerts (type, location, severity, description, latitude, longitude) 
                                 VALUES (?, ?, ?, ?, ?, ?)''', alert)

    def get_user_by_credentials(self, username, password):
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            stored_pw = user['password']
            if stored_pw.startswith('pbkdf2:') or stored_pw.startswith('scrypt:'):
                if check_password_hash(stored_pw, password):
                    conn.close()
                    return user
            elif stored_pw == password:
                # Upgrade hash
                new_hash = generate_password_hash(password)
                conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_hash, user['id']))
                conn.commit()
                conn.close()
                return user
        conn.close()
        return None

    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return user

    def create_user(self, username, password, email, user_type='user'):
        hashed_password = generate_password_hash(password)
        conn = self.get_connection()
        try:
            conn.execute('INSERT INTO users (username, password, email, user_type) VALUES (?, ?, ?, ?)',
                         (username, hashed_password, email, user_type))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_all_ngos(self):
        conn = self.get_connection()
        ngos = conn.execute('SELECT * FROM ngos ORDER BY name').fetchall()
        conn.close()
        return ngos

    def get_ngo_by_id(self, ngo_id):
        conn = self.get_connection()
        ngo = conn.execute('SELECT * FROM ngos WHERE id = ?', (ngo_id,)).fetchone()
        conn.close()
        return ngo

    def create_volunteer(self, name, email, phone, location, skills, availability, ngo_id=None):
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
        conn = self.get_connection()
        volunteers = conn.execute('''SELECT v.*, n.name as ngo_name 
                                  FROM volunteers v 
                                  JOIN ngos n ON v.ngo_id = n.id 
                                  WHERE v.ngo_id = ?
                                  ORDER BY v.created_at DESC''', (ngo_id,)).fetchall()
        conn.close()
        return volunteers

    def get_all_volunteers(self):
        conn = self.get_connection()
        volunteers = conn.execute('''SELECT v.*, n.name as ngo_name 
                                  FROM volunteers v 
                                  LEFT JOIN ngos n ON v.ngo_id = n.id 
                                  ORDER BY v.created_at DESC''').fetchall()
        conn.close()
        return volunteers

    def update_volunteer_status(self, volunteer_id, status):
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
        conn = self.get_connection()
        alerts = conn.execute('SELECT * FROM alerts ORDER BY created_at DESC').fetchall()
        conn.close()
        return alerts

    def get_emergency_contacts(self, contact_type=None):
        conn = self.get_connection()
        if contact_type:
            contacts = conn.execute('SELECT * FROM emergency_contacts WHERE type = ? ORDER BY name',
                                    (contact_type,)).fetchall()
        else:
            contacts = conn.execute('SELECT * FROM emergency_contacts ORDER BY type, name').fetchall()
        conn.close()
        return contacts


# Initialize global database helper instance
db = Database()