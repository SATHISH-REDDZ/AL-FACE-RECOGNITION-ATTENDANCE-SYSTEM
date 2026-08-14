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

class DatabaseAuthTestCase(unittest.TestCase):
    def setUp(self):
        database.init_db()

    def test_admin_seeding(self):
        user = database.verify_user(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], config.ADMIN_USERNAME)

    def test_invalid_login(self):
        user = database.verify_user("admin", "wrong_password_123")
        self.assertIsNone(user)

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
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ready")

    def test_unauthenticated_api_access(self):
        # Protected endpoints should return 401
        res = self.client.get('/api/stats', headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 401)

if __name__ == '__main__':
    unittest.main()
