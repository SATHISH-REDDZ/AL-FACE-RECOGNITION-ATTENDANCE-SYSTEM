"""
Automated Engineering Test Suite
---------------------------------
Unit & Integration tests verifying:
- Input validation & path traversal prevention
- User authentication & password hashing
- Database queries & FK constraints
- API endpoints, health check, and authorization middleware
"""

import unittest
import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
import utils_validation
from app import app

class ValidationTestCase(unittest.TestCase):
    def test_valid_student_ids(self):
        valid, val = utils_validation.validate_student_id("STU101")
        self.assertTrue(valid)
        self.assertEqual(val, "STU101")

        valid, val = utils_validation.validate_student_id("CS_2026-001")
        self.assertTrue(valid)

    def test_path_traversal_prevention(self):
        # Path traversal attempts
        invalid_ids = ["../hack", "..\\windows", "/etc/passwd", "student:123", "a" * 50]
        for bad_id in invalid_ids:
            valid, msg = utils_validation.validate_student_id(bad_id)
            self.assertFalse(valid, f"Failed to block dangerous ID: {bad_id}")

    def test_name_and_email_validation(self):
        valid, _ = utils_validation.validate_name("Alex Mercer")
        self.assertTrue(valid)

        valid, _ = utils_validation.validate_name("A")
        self.assertFalse(valid) # Too short

        valid, _ = utils_validation.validate_email("alex@university.edu")
        self.assertTrue(valid)

        valid, _ = utils_validation.validate_email("invalid-email-format")
        self.assertFalse(valid)

    def test_safe_redirect(self):
        self.assertEqual(utils_validation.safe_next_url("/chat"), "/chat")
        self.assertEqual(utils_validation.safe_next_url("https://malicious.com"), "/")
        self.assertEqual(utils_validation.safe_next_url("//malicious.com"), "/")

    def test_base64_image_validation(self):
        import base64
        import cv2
        import numpy as np

        # Create dummy image
        img = np.zeros((150, 150, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', img)
        b64_str = "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

        valid, err, matrix = utils_validation.validate_base64_image(b64_str)
        self.assertTrue(valid, f"Base64 validation failed: {err}")
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix.shape[:2], (150, 150))

class DatabaseAuthTestCase(unittest.TestCase):
    def setUp(self):
        database.init_db()

    def test_admin_seeding(self):
        pwd = config.ADMIN_PASSWORD or "admin123"
        user = database.verify_user(config.ADMIN_USERNAME, pwd)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], config.ADMIN_USERNAME)


    def test_invalid_login(self):
        user = database.verify_user("admin", "wrong_password_123")
        self.assertIsNone(user)

    def test_soft_deletion(self):
        import time
        test_id = f"STU_DEL_{int(time.time())}"
        database.add_student(test_id, "Test Student", "CS", "test@univ.edu")
        student = database.get_student_by_id(test_id)
        self.assertIsNotNone(student)

        database.delete_student(test_id)
        student_after = database.get_student_by_id(test_id)
        self.assertIsNone(student_after) # Soft deleted from active queries

    def test_session_management(self):
        sess_id = database.create_attendance_session("Morning Shift", "Computer Science", "Python AI", "Prof. Alan")
        self.assertIsNotNone(sess_id)

        active = database.get_active_session()
        self.assertIsNotNone(active)
        self.assertEqual(active["session_name"], "Morning Shift")

        database.set_active_session(0)
        self.assertIsNone(database.get_active_session())

    def test_audit_logging(self):
        database.log_audit_event("unit_test_user", "TEST_ACTION", "SUCCESS", "Automated test detail")
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE username = 'unit_test_user';")
        logs = cursor.fetchall()
        conn.close()
        self.assertTrue(len(logs) > 0)

    def test_duplicate_attendance_prevention(self):
        import time
        t_id = f"STU_DUP_{int(time.time())}"
        database.add_student(t_id, "Duplicate Check Student", "CSE", "dup@univ.edu")
        sess_id = database.create_attendance_session("Session Dup Check", "CSE", "Algorithms", "Prof. Turing")

        # First mark should succeed
        ok1, msg1, _ = database.mark_attendance(t_id, session_id=sess_id)
        self.assertTrue(ok1, f"First attendance mark failed: {msg1}")

        # Second mark in same session must fail
        ok2, msg2, _ = database.mark_attendance(t_id, session_id=sess_id)
        self.assertFalse(ok2, "Duplicate attendance in same session was not prevented!")



class FaceEngineTestCase(unittest.TestCase):
    def test_liveness_evaluation(self):
        import numpy as np
        from face_engine import engine
        dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        is_live, score, details = engine.evaluate_liveness(dummy_frame, (50, 50, 150, 150))
        self.assertIsInstance(is_live, bool)
        self.assertGreaterEqual(score, 0.0)


class APIEndpointsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        database.init_db()

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_readiness_endpoint(self):
        response = self.client.get('/ready')
        self.assertIn(response.status_code, (200, 503))

    def test_unauthenticated_api_access(self):
        # Protected endpoints should return 401
        res = self.client.get('/api/stats', headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 401)

        res_audit = self.client.get('/api/audit', headers={"Accept": "application/json"})
        self.assertEqual(res_audit.status_code, 401)

    def test_attendance_export(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {'username': 'admin', 'role': 'admin', 'name': 'Admin User'}

        res_csv = self.client.get('/api/attendance/export?format=csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, 'text/csv')

        res_xlsx = self.client.get('/api/attendance/export?format=xlsx')
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn('spreadsheetml', res_xlsx.mimetype)

if __name__ == '__main__':
    unittest.main()



