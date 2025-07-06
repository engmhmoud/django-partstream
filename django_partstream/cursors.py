"""
Cursor management for progressive delivery.
"""

import json
import time
from typing import Dict, Any, Optional

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .exceptions import InvalidCursorError, CursorExpiredError


class CursorManager:
    """
    Manages cursor creation and validation for progressive delivery.
    Uses Fernet encryption for secure, stateless cursor management.
    """

    def __init__(self, secret_key: Optional[str] = None, ttl: Optional[int] = None):
        """
        Initialize the cursor manager.

        Args:
            secret_key: Secret key for encryption. If None, uses Django's SECRET_KEY.
            ttl: Time-to-live for cursors in seconds. If None, cursors don't expire.
        """
        self.secret_key = secret_key or getattr(settings, "SECRET_KEY", None)
        if not self.secret_key:
            raise ImproperlyConfigured("SECRET_KEY is required for cursor encryption")

        self.ttl = ttl
        self._setup_encryption()

    def _setup_encryption(self):
        """Setup Fernet encryption with Django secret key."""
        # Create a consistent key from Django's SECRET_KEY
        key = self.secret_key.encode()
        if len(key) < 32:
            # Pad the key to 32 bytes if needed
            key = key + b"\x00" * (32 - len(key))
        else:
            key = key[:32]

        # Generate a proper Fernet key from the secret
        import base64
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"django_partstream_salt",
            iterations=100000,
        )
        fernet_key = base64.urlsafe_b64encode(kdf.derive(key))
        self.fernet = Fernet(fernet_key)

    def create_cursor(self, data: Dict[str, Any]) -> str:
        """
        Create a signed cursor from data.

        Args:
            data: Dictionary containing cursor data

        Returns:
            Encrypted cursor token
        """
        cursor_data = {"data": data, "timestamp": time.time() if self.ttl else None}

        json_data = json.dumps(cursor_data, separators=(",", ":"))
        encrypted_data = self.fernet.encrypt(json_data.encode())
        return encrypted_data.decode()

    def decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """
        Decode and validate a cursor.

        Args:
            cursor: Encrypted cursor token

        Returns:
            Decoded cursor data

        Raises:
            InvalidCursorError: If cursor is invalid or tampered
            CursorExpiredError: If cursor has expired
        """
        try:
            encrypted_data = cursor.encode()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            cursor_data = json.loads(decrypted_data.decode())

            # Check expiration if TTL is set
            if self.ttl and cursor_data.get("timestamp"):
                if time.time() - cursor_data["timestamp"] > self.ttl:
                    raise CursorExpiredError()

            return cursor_data.get("data", {})

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise InvalidCursorError(f"Invalid cursor format: {str(e)}")
        except Exception as e:
            raise InvalidCursorError(f"Cursor decryption failed: {str(e)}")

    def is_valid_cursor(self, cursor: str) -> bool:
        """
        Check if a cursor is valid without raising exceptions.

        Args:
            cursor: Cursor token to validate

        Returns:
            True if cursor is valid, False otherwise
        """
        try:
            self.decode_cursor(cursor)
            return True
        except (InvalidCursorError, CursorExpiredError):
            return False

    # Alias for backwards compatibility
    def generate_cursor(self, data: Dict[str, Any]) -> str:
        """Alias for create_cursor for backwards compatibility."""
        return self.create_cursor(data)
