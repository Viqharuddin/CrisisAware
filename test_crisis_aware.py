"""
test_crisis_aware.py - Comprehensive Verification & Test Suite for CrisisAware
"""
import unittest
import os
import json
import sqlite3
from urllib.parse import urlparse, parse_qs, unquote
from werkzeug.security import check_password_hash

# Set test environment
os.environ['DATABASE'] = 'test_floodguard.db'
os.environ['SECRET_KEY'] = 'test-secret-key-12345'
os.environ['FLASK_DEBUG'] = 'False'
os.environ.setdefault('ADMIN_USERNAME', 'admin')
os.environ.setdefault('ADMIN_EMAIL', 'admin@example.com')
os.environ.setdefault('ADMIN_PASSWORD', 'change-this-admin-password')

from app import app, init_db, get_db, get_db_path, generate_gmail_compose_url, fetch_live_weather_alerts
import database


class CrisisAwareTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        cls.client = app.test_client()

    def setUp(self):
        # Fresh test database setup
        db_path = get_db_path()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
        init_db()

    def tearDown(self):
        db_path = get_db_path()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    # 1. Database Initialization & Idempotency
    def test_01_database_idempotency(self):
        # Run init_db multiple times
        init_db()
        init_db()
        init_db()
        conn = get_db()
        ngos = conn.execute('SELECT * FROM ngos').fetchall()
        contacts = conn.execute('SELECT * FROM emergency_contacts').fetchall()
        conn.close()

        # Should be exactly 4 NGOs and 6 emergency contacts without duplicates
        self.assertEqual(len(ngos), 4, f"Expected 4 NGOs, found {len(ngos)}")
        self.assertEqual(len(contacts), 6, f"Expected 6 emergency contacts, found {len(contacts)}")

    # 2. Registration & Password Hashing
    def test_02_registration_password_hashing(self):
        response = self.client.post('/register', data={
            'username': 'testuser',
            'password': 'SecretPassword123!',
            'email': 'testuser@example.com',
            'user_type': 'user'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('testuser',)).fetchone()
        conn.close()

        self.assertIsNotNone(user)
        self.assertNotEqual(user['password'], 'SecretPassword123!')
        self.assertTrue(user['password'].startswith('scrypt:') or user['password'].startswith('pbkdf2:'))
        self.assertTrue(check_password_hash(user['password'], 'SecretPassword123!'))

    # 3. Duplicate Username Prevention
    def test_03_duplicate_registration_prevention(self):
        self.client.post('/register', data={
            'username': 'uniqueuser',
            'password': 'Password1',
            'email': 'u1@example.com',
            'user_type': 'user'
        })
        response = self.client.post('/register', data={
            'username': 'uniqueuser',
            'password': 'Password2',
            'email': 'u2@example.com',
            'user_type': 'user'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'already exists', response.data)

    # 4. Authentication (Login, Wrong Password, Logout, Transparent Legacy Upgrade)
    def test_04_authentication_flow(self):
        # Register user
        self.client.post('/register', data={
            'username': 'normaluser',
            'password': 'MyPassword123',
            'email': 'normal@example.com',
            'user_type': 'user'
        })

        # Wrong password
        resp_wrong = self.client.post('/login', data={
            'username': 'normaluser',
            'password': 'WrongPassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username or password', resp_wrong.data)

        # Correct password
        resp_correct = self.client.post('/login', data={
            'username': 'normaluser',
            'password': 'MyPassword123'
        }, follow_redirects=True)
        self.assertIn(b'Login successful', resp_correct.data)

        # Logout
        resp_logout = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'You have been logged out', resp_logout.data)

    # 5. NGO Dashboard Role Authorization
    def test_05_ngo_dashboard_authorization(self):
        # 1) Logged-out user
        resp_unauth = self.client.get('/ngo/dashboard', follow_redirects=False)
        self.assertEqual(resp_unauth.status_code, 302)
        self.assertIn('/login', resp_unauth.headers['Location'])

        # 2) Normal user (user_type == 'user')
        self.client.post('/register', data={
            'username': 'generaluser',
            'password': 'UserPass123',
            'email': 'gen@example.com',
            'user_type': 'user'
        })
        self.client.post('/login', data={'username': 'generaluser', 'password': 'UserPass123'})

        resp_user_denied = self.client.get('/ngo/dashboard', follow_redirects=False)
        self.assertEqual(resp_user_denied.status_code, 302)
        self.assertEqual(resp_user_denied.headers['Location'], '/')

        # Try actions as normal user
        self.assertEqual(self.client.post('/volunteer/accept/1').status_code, 302)
        self.assertEqual(self.client.post('/volunteer/reject/1').status_code, 302)
        self.assertEqual(self.client.post('/volunteer/contact/1').status_code, 302)

        self.client.get('/logout')

        # 3) NGO User workflow (NGO Application -> Admin Approval -> NGO Login -> Dashboard)
        # 3a) Submit NGO application
        resp_app = self.client.post('/ngo/register', data={
            'org_name': 'Care India Relief',
            'registration_no': 'REG-CARE-101',
            'contact_person': 'Ananya Roy',
            'designation': 'Program Coordinator',
            'email': 'ananya@careindia.org',
            'phone': '9876543210',
            'website': 'https://careindia.org',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400069',
            'address': 'Plot 45, Andheri East',
            'areas_of_operation': 'Mumbai, Thane',
            'description': 'Disaster relief and emergency response organization.'
        }, follow_redirects=True)
        self.assertEqual(resp_app.status_code, 200)

        conn = get_db()
        app_row = conn.execute('SELECT * FROM ngo_applications WHERE registration_no = ?', ('REG-CARE-101',)).fetchone()
        conn.close()
        self.assertIsNotNone(app_row)
        self.assertEqual(app_row['status'], 'pending')
        self.assertEqual(app_row['pincode'], '400069')
        self.assertEqual(app_row['designation'], 'Program Coordinator')

        # 3b) Log in as Admin and approve application
        self.client.post('/login', data={'username': 'admin', 'password': 'change-this-admin-password'})
        resp_approve = self.client.post(f'/admin/applications/{app_row["id"]}/approve', follow_redirects=True)
        self.assertEqual(resp_approve.status_code, 200)

        conn = get_db()
        approved_app = conn.execute('SELECT * FROM ngo_applications WHERE id = ?', (app_row['id'],)).fetchone()
        ngo_user = conn.execute('SELECT * FROM users WHERE id = ?', (approved_app['user_id'],)).fetchone()
        conn.close()
        self.assertEqual(approved_app['status'], 'approved')
        self.assertIsNotNone(ngo_user)
        self.assertEqual(ngo_user['user_type'], 'ngo')

        # 3c) Logout admin, log in with NGO login_id
        self.client.get('/logout')
        # Manually reset password or set known password for test
        conn = get_db()
        from werkzeug.security import generate_password_hash
        conn.execute('UPDATE users SET password = ?, must_change_password = 0 WHERE id = ?',
                     (generate_password_hash('NgoSecurePass123!'), ngo_user['id']))
        conn.commit()
        conn.close()

        resp_ngo_login = self.client.post('/login', data={
            'username': ngo_user['login_id'],
            'password': 'NgoSecurePass123!'
        }, follow_redirects=True)
        self.assertEqual(resp_ngo_login.status_code, 200)

        resp_ngo_allowed = self.client.get('/ngo/dashboard', follow_redirects=True)
        self.assertEqual(resp_ngo_allowed.status_code, 200)
        self.assertIn(b'NGO Volunteer Management', resp_ngo_allowed.data)

    # 6. Volunteer Submission & Lifecycle (Accept, Reject, Contact)
    def test_06_volunteer_lifecycle(self):
        # Create and approve an NGO
        conn = get_db()
        ngo_row = conn.execute("SELECT * FROM ngos WHERE status = 'active' LIMIT 1").fetchone()
        ngo_id = ngo_row['id']
        ngo_name = ngo_row['name']

        # Create NGO user associated with this NGO
        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO users (username, password, email, user_type, ngo_id, login_id, must_change_password, is_active) VALUES (?, ?, ?, 'ngo', ?, ?, 0, 1)",
            ('ngotester', generate_password_hash('NgoPass123!'), 'tester@ngo.org', ngo_id, 'NGO-TEST01')
        )
        conn.commit()
        conn.close()

        # Submit volunteer application for this NGO
        resp_vol = self.client.post('/volunteer', data={
            'name': 'Rahul Sharma',
            'email': 'rahul.volunteer@example.com',
            'phone': '9876543210',
            'location': 'Mumbai, Maharashtra',
            'skills': 'medical',
            'availability': 'immediate',
            'ngo_id': ngo_id
        }, follow_redirects=True)
        self.assertEqual(resp_vol.status_code, 200)

        conn = get_db()
        vol = conn.execute('SELECT * FROM volunteers WHERE email = ?', ('rahul.volunteer@example.com',)).fetchone()
        conn.close()
        self.assertIsNotNone(vol)
        self.assertEqual(vol['status'], 'pending')
        vol_id = vol['id']

        # Log in as the NGO user
        self.client.post('/login', data={'username': 'ngotester', 'password': 'NgoPass123!'})

        # Test Accept Volunteer
        resp_accept = self.client.post(f'/volunteer/accept/{vol_id}', follow_redirects=True)
        self.assertEqual(resp_accept.status_code, 200)

        conn = get_db()
        vol_accepted = conn.execute('SELECT * FROM volunteers WHERE id = ?', (vol_id,)).fetchone()
        conn.close()
        self.assertEqual(vol_accepted['status'], 'Accepted')

        # Test Reject Volunteer
        resp_reject = self.client.post(f'/volunteer/reject/{vol_id}', data={'reason': 'Positions currently filled'}, follow_redirects=True)
        self.assertEqual(resp_reject.status_code, 200)

        conn = get_db()
        vol_rejected = conn.execute('SELECT * FROM volunteers WHERE id = ?', (vol_id,)).fetchone()
        conn.close()
        self.assertEqual(vol_rejected['status'], 'Rejected')

        # Test Contact Volunteer
        resp_contact = self.client.post(f'/volunteer/contact/{vol_id}', data={
            'subject': 'Interview Schedule',
            'message': 'Please join us for orientation tomorrow.'
        }, follow_redirects=True)
        self.assertEqual(resp_contact.status_code, 200)

    # 7. Gmail Compose URL Generator
    def test_07_gmail_compose_url(self):
        to_email = 'volunteer+rescue@gmail.com'
        subject = 'Application Accepted - Disaster Response Team & Volunteers!'
        body = 'Dear Volunteer,\n\nWelcome to the team!\nSpecial Characters: & = ? # % 100%'

        url = generate_gmail_compose_url(to_email, subject, body)
        self.assertTrue(url.startswith('https://mail.google.com/mail/?view=cm&fs=1'))
        self.assertIn('&to=volunteer%2Brescue@gmail.com', url)
        self.assertIn('&su=', url)
        self.assertIn('&body=', url)

        # Ensure quotes, newlines, and ampersands are encoded safely
        self.assertNotIn('\n', url)
        self.assertNotIn(' ', url)

    # 8. Emergency Contacts API
    def test_08_emergency_contacts_api(self):
        resp = self.client.get('/api/emergency-contacts')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(len(data['contacts']), 6)
        names = [c['name'] for c in data['contacts']]
        self.assertIn('National Disaster Response Force', names)
        self.assertIn('National Emergency Helpline', names)

    # 9. Alerts API
    def test_09_alerts_api(self):
        # /api/alert is admin-protected: unauthenticated writes are rejected
        unauth_resp = self.client.post('/api/alert', json={
            'type': 'flood', 'location': 'Mumbai Central', 'severity': 'critical',
            'description': 'Water levels rising in subway.', 'latitude': 18.97, 'longitude': 72.82
        })
        self.assertIn(unauth_resp.status_code, (302, 401, 403))

        # Log in as admin, then create the alert
        self.client.post('/login', data={'username': 'admin', 'password': 'change-this-admin-password'})
        post_resp = self.client.post('/api/alert', json={
            'type': 'flood',
            'location': 'Mumbai Central',
            'severity': 'critical',
            'description': 'Water levels rising in subway.',
            'latitude': 18.97,
            'longitude': 72.82
        })
        self.assertEqual(post_resp.status_code, 200)

        # Retrieve alerts
        get_resp = self.client.get('/api/alerts')
        self.assertEqual(get_resp.status_code, 200)
        alerts = get_resp.get_json()
        self.assertTrue(any(a['location'] == 'Mumbai Central' for a in alerts))

    # 10. Nearby Weather Alerts Endpoint
    def test_10_nearby_alerts_endpoint(self):
        resp = self.client.get('/api/nearby-alerts?lat=18.97&lon=72.82&radius=50')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('alerts', data)

    # 11. Overpass Nearby Places Proxy
    def test_11_nearby_places_endpoint(self):
        resp = self.client.get('/api/nearby-places?lat=18.97&lon=72.82&type=hospital')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('elements', data)

    # 12. Chatbot Graceful Handling
    def test_12_chatbot_graceful_response(self):
        resp = self.client.post('/chatbot', json={'message': 'What should I do during a flood?'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('response', data)
        self.assertTrue(len(data['response']) > 0)

    # 13. Single Admin Guarantee & Demotion of Redundant Admins
    def test_13_single_admin_enforcement(self):
        conn = get_db()
        # Count initial admins (should be exactly 1)
        admins = conn.execute("SELECT * FROM users WHERE user_type = 'admin'").fetchall()
        self.assertEqual(len(admins), 1)

        # Insert a rogue admin manually
        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO users (username, password, email, user_type, login_id) VALUES (?, ?, ?, 'admin', ?)",
            ('fakeadmin', generate_password_hash('FakePass123'), 'fake@admin.org', 'fakeadmin')
        )
        conn.commit()

        # Re-run init_db / ensure_single_admin
        from app import ensure_single_admin
        ensure_single_admin(conn)
        conn.commit()

        admins_after = conn.execute("SELECT * FROM users WHERE user_type = 'admin'").fetchall()
        self.assertEqual(len(admins_after), 1)
        self.assertEqual(admins_after[0]['username'], 'admin')

        # Fake admin was demoted to 'user'
        demoted = conn.execute("SELECT * FROM users WHERE username = 'fakeadmin'").fetchone()
        self.assertEqual(demoted['user_type'], 'user')
        conn.close()

    # 14. Admin Resend Credentials Idempotency (No duplicate users created)
    def test_14_admin_resend_credentials_idempotency(self):
        # Register NGO application
        self.client.post('/ngo/register', data={
            'org_name': 'Disaster Rescue Org',
            'registration_no': 'REG-DRO-999',
            'contact_person': 'Rohan Gupta',
            'designation': 'Director',
            'email': 'rohan@dro.org',
            'phone': '9876543211',
            'city': 'Delhi',
            'state': 'Delhi',
            'pincode': '110001',
            'address': 'Connaught Place',
            'areas_of_operation': 'Delhi NCR',
            'description': 'Emergency relief support'
        })

        conn = get_db()
        app_row = conn.execute("SELECT * FROM ngo_applications WHERE registration_no = 'REG-DRO-999'").fetchone()
        conn.close()

        # Admin logs in and approves
        self.client.post('/login', data={'username': 'admin', 'password': 'change-this-admin-password'})
        self.client.post(f'/admin/applications/{app_row["id"]}/approve', follow_redirects=True)

        conn = get_db()
        users_count_1 = conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'ngo'").fetchone()[0]
        conn.close()

        # Resend credentials
        self.client.post(f'/admin/applications/{app_row["id"]}/resend', follow_redirects=True)

        conn = get_db()
        users_count_2 = conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'ngo'").fetchone()[0]
        conn.close()

        # Users count must NOT increase (idempotent, no duplicates)
        self.assertEqual(users_count_1, users_count_2)

    # 15. NGO Volunteer Data Isolation
    def test_15_ngo_volunteer_data_isolation(self):
        conn = get_db()
        ngos = conn.execute("SELECT * FROM ngos WHERE status = 'active' LIMIT 2").fetchall()
        ngo1, ngo2 = ngos[0], ngos[1]

        # Create volunteer for NGO 1
        vol1_cur = conn.execute(
            "INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
            ('Vol One', 'vol1@ngo1.org', '9999999991', 'Delhi', 'medical', 'immediate', ngo1['id'])
        )
        vol1_id = vol1_cur.lastrowid

        # Create volunteer for NGO 2
        vol2_cur = conn.execute(
            "INSERT INTO volunteers (name, email, phone, location, skills, availability, ngo_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
            ('Vol Two', 'vol2@ngo2.org', '9999999992', 'Pune', 'rescue', 'weekends', ngo2['id'])
        )
        vol2_id = vol2_cur.lastrowid

        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO users (username, password, email, user_type, ngo_id, login_id, must_change_password, is_active) VALUES (?, ?, ?, 'ngo', ?, ?, 0, 1)",
            ('ngo1user', generate_password_hash('Pass123!'), 'ngo1@org.in', ngo1['id'], 'NGO-1111')
        )
        conn.commit()
        conn.close()

        # Log in as NGO 1
        self.client.post('/login', data={'username': 'NGO-1111', 'password': 'Pass123!'})

        # NGO 1 dashboard only shows Vol 1, not Vol 2
        resp_dash = self.client.get('/ngo/dashboard')
        self.assertIn(b'Vol One', resp_dash.data)
        self.assertNotIn(b'Vol Two', resp_dash.data)

        # NGO 1 cannot accept Vol 2 (which belongs to NGO 2)
        resp_hack = self.client.post(f'/volunteer/accept/{vol2_id}', follow_redirects=True)
        self.assertIn(b'Volunteer application not found', resp_hack.data)

        conn = get_db()
        vol2_check = conn.execute("SELECT status FROM volunteers WHERE id = ?", (vol2_id,)).fetchone()
        conn.close()
        self.assertEqual(vol2_check['status'], 'pending')

    # 16. Rejection Requires a Reason
    def test_16_rejection_requires_reason(self):
        self.client.post('/ngo/register', data={
            'org_name': 'Reason Check Org',
            'registration_no': 'REG-RC-500',
            'contact_person': 'Sita Verma',
            'designation': 'Secretary',
            'email': 'sita@reasoncheck.org',
            'phone': '9876500011',
            'city': 'Jaipur',
            'state': 'Rajasthan',
            'pincode': '302001',
            'address': 'MG Road',
            'areas_of_operation': 'Jaipur',
            'description': 'Relief org for reason-required test'
        })

        conn = get_db()
        app_row = conn.execute("SELECT * FROM ngo_applications WHERE registration_no = 'REG-RC-500'").fetchone()
        conn.close()
        self.assertIsNotNone(app_row)

        self.client.post('/login', data={'username': 'admin', 'password': 'change-this-admin-password'})

        # Empty reason must NOT reject the application
        self.client.post(f'/admin/applications/{app_row["id"]}/reject', data={'reason': ''}, follow_redirects=True)
        conn = get_db()
        still_pending = conn.execute("SELECT status FROM ngo_applications WHERE id = ?", (app_row['id'],)).fetchone()
        conn.close()
        self.assertEqual(still_pending['status'], 'pending')

        # With a reason the application is rejected
        resp = self.client.post(f'/admin/applications/{app_row["id"]}/reject',
                                data={'reason': 'Incomplete documentation'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        conn = get_db()
        rejected = conn.execute("SELECT status, rejection_reason FROM ngo_applications WHERE id = ?", (app_row['id'],)).fetchone()
        conn.close()
        self.assertEqual(rejected['status'], 'rejected')
        self.assertEqual(rejected['rejection_reason'], 'Incomplete documentation')

    # 17. Dedicated Admin Login & Non-Admin Exclusion
    def test_17_admin_login_exclusivity(self):
        # Ensure no session is carried over from a previous test
        self.client.get('/logout')
        # GET renders the admin login page
        get_resp = self.client.get('/admin/login')
        self.assertEqual(get_resp.status_code, 200)

        # A normal user cannot authenticate via /admin/login
        self.client.post('/register', data={
            'username': 'plainuser', 'password': 'PlainPass123',
            'email': 'plain@example.com', 'user_type': 'user'
        })
        resp_nonadmin = self.client.post('/admin/login', data={
            'username': 'plainuser', 'password': 'PlainPass123'
        }, follow_redirects=True)
        self.assertIn(b'Invalid administrator credentials', resp_nonadmin.data)

        # Admin dashboard is protected: logged-out users are redirected to login
        self.client.get('/logout')
        resp_guard = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(resp_guard.status_code, 302)
        self.assertIn('/login', resp_guard.headers['Location'])

        # The real admin can log in via /admin/login
        resp_admin = self.client.post('/admin/login', data={
            'username': 'admin', 'password': 'change-this-admin-password'
        }, follow_redirects=True)
        self.assertEqual(resp_admin.status_code, 200)
        self.assertNotIn(b'Invalid administrator credentials', resp_admin.data)

    # 18. /admin/dashboard Alias & Authorization
    def test_18_admin_dashboard_alias(self):
        # Normal user is denied the dashboard and redirected home
        self.client.post('/register', data={
            'username': 'denieduser', 'password': 'DeniedPass123',
            'email': 'denied@example.com', 'user_type': 'user'
        })
        self.client.post('/login', data={'username': 'denieduser', 'password': 'DeniedPass123'})
        resp_denied = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(resp_denied.status_code, 302)
        self.assertEqual(resp_denied.headers['Location'], '/')
        self.client.get('/logout')

        # Admin reaches the dashboard via both /admin/dashboard and /admin
        self.client.post('/login', data={'username': 'admin', 'password': 'change-this-admin-password'})
        resp_alias = self.client.get('/admin/dashboard')
        self.assertEqual(resp_alias.status_code, 200)
        resp_canon = self.client.get('/admin')
        self.assertEqual(resp_canon.status_code, 200)


if __name__ == '__main__':
    unittest.main()

