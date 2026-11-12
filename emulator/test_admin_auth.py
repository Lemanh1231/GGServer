"""Test suite for Admin Dashboard Authentication and Access Control."""
import unittest
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))
from server import admin

class TestAdminAuth(unittest.TestCase):
    def test_verify_admin_password(self):
        """Direct password verification."""
        self.assertTrue(admin.verify_admin_token('Stingdau@1231@@'))
        self.assertFalse(admin.verify_admin_token('WrongPassword'))
        self.assertFalse(admin.verify_admin_token(''))
        self.assertFalse(admin.verify_admin_token(None))

    def test_token_creation_and_validation(self):
        """Signed HMAC token creation, validation, and expiry."""
        token = admin.create_admin_token(ttl=3600)
        self.assertTrue(admin.verify_admin_token(token))

        # Tampered signature
        parts = token.split('.')
        tampered = f"{parts[0]}.wrongsignature123456"
        self.assertFalse(admin.verify_admin_token(tampered))

        # Expired token
        expired_token = admin.create_admin_token(ttl=-10)
        self.assertFalse(admin.verify_admin_token(expired_token))

    def test_headers_auth_detection(self):
        """Check Authorization header and Cookie header detection."""
        valid_token = admin.create_admin_token()

        # Bearer with valid token
        self.assertTrue(admin.is_admin_authenticated({'Authorization': f'Bearer {valid_token}'}))
        # Bearer with raw password
        self.assertTrue(admin.is_admin_authenticated({'Authorization': 'Bearer Stingdau@1231@@'}))
        # Bearer with invalid token
        self.assertFalse(admin.is_admin_authenticated({'Authorization': 'Bearer invalid_pass'}))

        # Cookie with valid token
        self.assertTrue(admin.is_admin_authenticated({'Cookie': f'other_cookie=xyz; gg_admin_token={valid_token}; foo=bar'}))
        # Cookie with invalid token
        self.assertFalse(admin.is_admin_authenticated({'Cookie': 'gg_admin_token=invalid_pass'}))
        # Missing headers
        self.assertFalse(admin.is_admin_authenticated({}))

    def test_login_and_dashboard_html_templates(self):
        """Verify login HTML and dashboard HTML are rendered properly."""
        login_html = admin.get_login_html()
        self.assertIn('Guitar Girl', login_html)
        self.assertIn('password', login_html)
        self.assertIn('Đăng Nhập', login_html)

        dash_html = admin.get_admin_html()
        self.assertIn('Guitar Girl - Trung Tâm Quản Trị', dash_html)
        self.assertIn('logoutAdmin', dash_html)
        self.assertIn('btn_logout', dash_html)

if __name__ == '__main__':
    unittest.main()
