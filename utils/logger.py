import logging
import os
from logging.handlers import RotatingFileHandler
import config

# Configure logger
logger = logging.getLogger("TorqueTester")
logger.setLevel(logging.DEBUG)

# Create log formatters
file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
console_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)

# Ensure log directory exists
config.LOG_DIR.mkdir(exist_ok=True)

# Rotating File Handler (10MB max per file, keep 5 backups)
file_handler = RotatingFileHandler(
    config.LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger():
    return logger

def log_action(user, action, details=""):
    """Convenience function to log user actions for traceability."""
    msg = f"User: {user} | Action: {action}"
    if details:
        msg += f" | Details: {details}"
    logger.info(msg)
