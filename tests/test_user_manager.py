import unittest
from auth.user_manager import hash_password, verify_password

class TestUserManager(unittest.TestCase):
    def test_hash_and_verify_password_success(self):
        password = "SecretPassword123!"
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed))

    def test_verify_password_failure(self):
        password = "SecretPassword123!"
        hashed = hash_password(password)
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_verify_empty_password_returns_false(self):
        self.assertFalse(verify_password("password", ""))

    def test_account_lockout_after_five_failed_attempts(self):
        from unittest.mock import MagicMock
        from auth.user_manager import UserManager
        from database.models import User

        db_mock = MagicMock()
        db_mock.get_all_users.return_value = [User(id=1, username="admin")]
        db_mock.get_user_by_username.return_value = User(id=1, username="admin", password_hash=hash_password("correct_pass"), active=True)

        mgr = UserManager(db_mock)

        # 4 failed attempts -> still not locked out
        for _ in range(4):
            self.assertFalse(mgr.login("admin", "wrong_pass"))
            self.assertNotIn("admin", mgr.lockout_until)

        # 5th failed attempt -> locks out account
        self.assertFalse(mgr.login("admin", "wrong_pass"))
        self.assertIn("admin", mgr.lockout_until)

        # Even correct password is now blocked during lockout
        self.assertFalse(mgr.login("admin", "correct_pass"))

if __name__ == "__main__":
    unittest.main()
