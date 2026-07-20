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

if __name__ == "__main__":
    unittest.main()
