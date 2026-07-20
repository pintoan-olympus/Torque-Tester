import hashlib
from typing import Optional
import config
from utils.logger import get_logger, log_action
from database.models import User
from database.db_manager import DatabaseManager

logger = get_logger()

# Hashing strategy using bcrypt with hashlib fallback
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    logger.warning("bcrypt module not found. Falling back to SHA-256 for password hashing.")

def hash_password(password: str) -> str:
    """Hash password using bcrypt or SHA-256 fallback."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    else:
        # Salted SHA-256 fallback
        salt = "TorqueTesterAppSalt"
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against its hash."""
    if not hashed:
        return False
    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            # If the database password was stored in SHA-256 format, try fallback comparison
            pass
    
    # SHA-256 fallback comparison
    salt = "TorqueTesterAppSalt"
    fallback_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return fallback_hash == hashed


class UserManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.current_user: Optional[User] = None
        self.seed_default_admin()

    def seed_default_admin(self):
        """Seed the default admin if no users exist in the database."""
        users = self.db.get_all_users()
        if not users:
            logger.info("No users found in database. Seeding default admin user.")
            admin_user = User(
                username="admin",
                password_hash=hash_password("admin"),
                full_name="System Administrator",
                access_level=config.ACCESS_ADMIN,
                active=True
            )
            self.db.create_user(admin_user)
            log_action("SYSTEM", "SEED_ADMIN", "Default admin account created ('admin')")

    def login(self, username: str, password: str) -> bool:
        """Authenticate user and establish session."""
        logger.info(f"Login attempt for user: {username}")
        user = self.db.get_user_by_username(username)
        if not user:
            logger.warning(f"Login failed: user '{username}' not found.")
            return False
        
        if not user.active:
            logger.warning(f"Login failed: user '{username}' is inactive.")
            return False

        if verify_password(password, user.password_hash):
            self.current_user = user
            log_action(user.username, "LOGIN", "Successfully logged in")
            return True
        else:
            logger.warning(f"Login failed: incorrect password for user '{username}'.")
            return False

    def logout(self):
        """Clear session."""
        if self.current_user:
            log_action(self.current_user.username, "LOGOUT", "User logged out")
            self.current_user = None

    def create_user(self, username: str, password: str, full_name: str, access_level: int) -> bool:
        """Create a new user (requires supervisor or admin to call this contextually)."""
        new_user = User(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            access_level=access_level,
            active=True
        )
        success = self.db.create_user(new_user)
        if success and self.current_user:
            log_action(self.current_user.username, "CREATE_USER", f"Created user {username} with level {access_level}")
        return success

    def change_password(self, user_id: int, new_password: str) -> bool:
        """Update password for a user."""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        user.password_hash = hash_password(new_password)
        success = self.db.update_user(user)
        if success and self.current_user:
            log_action(self.current_user.username, "CHANGE_PASSWORD", f"Changed password for user ID {user_id}")
        return success

    def update_user_profile(self, user_id: int, full_name: str, access_level: int, active: bool) -> bool:
        """Update details of a user."""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        user.full_name = full_name
        user.access_level = access_level
        user.active = active
        success = self.db.update_user(user)
        if success and self.current_user:
            log_action(self.current_user.username, "UPDATE_USER", f"Updated user {user.username}: level={access_level}, active={active}")
        return success

    def has_access(self, required_level: int) -> bool:
        """Check if current user has the required access level."""
        if not self.current_user:
            return False
        return self.current_user.access_level >= required_level
