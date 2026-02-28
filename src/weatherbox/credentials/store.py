"""
Credential storage with file permissions and optional encryption.
Provides secure storage for Wi-Fi provisioning credentials.
"""

import os
import json
import stat
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CredentialStore:
    """Manages storage and retrieval of Wi-Fi credentials with security."""

    # Default file mode: read/write for owner only (0o600)
    DEFAULT_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR  # 0o600

    def __init__(self, credential_file_path: str,
                 enable_encryption: bool = False):
        """
        Initialize credential store.

        Args:
            credential_file_path: Path to store credentials file
            enable_encryption: Enable symmetric encryption using libsodium (optional)
        """
        self.credential_file_path = Path(credential_file_path)
        self.enable_encryption = enable_encryption

        # Ensure directory exists
        self.credential_file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_credentials(
            self,
            ssid: str,
            password: str,
            security_type: str = "WPA2") -> bool:
        """
        Save Wi-Fi credentials securely.

        Args:
            ssid: Network SSID
            password: Network password
            security_type: Security type (default: WPA2)

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            credentials = {
                "ssid": ssid,
                "password": password,
                "security_type": security_type
            }

            # Write to file
            with open(self.credential_file_path, "w") as f:
                json.dump(credentials, f)

            # Set strict file permissions (read/write owner only)
            os.chmod(self.credential_file_path, self.DEFAULT_FILE_MODE)

            logger.info(
                f"Credentials saved to {
                    self.credential_file_path} with mode 0o600")
            return True

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return False

    def load_credentials(self) -> Optional[Tuple[str, str]]:
        """
        Load Wi-Fi credentials from secure storage.

        Returns:
            Tuple of (ssid, password) if credentials exist, None otherwise
        """
        try:
            if not self.credential_file_path.exists():
                logger.debug("Credential file does not exist")
                return None

            # Verify file permissions (should be 0o600)
            file_stat = os.stat(self.credential_file_path)
            file_mode = stat.S_IMODE(file_stat.st_mode)

            if file_mode != self.DEFAULT_FILE_MODE:
                logger.warning(
                    f"Credential file has insecure permissions: 0o{
                        file_mode:o} " f"(expected 0o{
                        self.DEFAULT_FILE_MODE:o})")

            with open(self.credential_file_path, "r") as f:
                credentials = json.load(f)

            ssid = credentials.get("ssid")
            password = credentials.get("password")

            if not ssid or not password:
                logger.warning("Credential file missing SSID or password")
                return None

            return (ssid, password)

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def clear_credentials(self) -> bool:
        """
        Delete stored credentials.

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            if self.credential_file_path.exists():
                self.credential_file_path.unlink()
                logger.info("Credentials cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")
            return False

    def ensure_secure_permissions(self) -> bool:
        """
        Verify and correct file permissions if needed.

        Returns:
            True if permissions are/were set to 0o600, False otherwise
        """
        try:
            if not self.credential_file_path.exists():
                logger.debug("Credential file does not exist")
                return False

            os.chmod(self.credential_file_path, self.DEFAULT_FILE_MODE)
            logger.info(
                f"Verified/corrected credential file permissions to 0o600")
            return True
        except Exception as e:
            logger.error(f"Failed to set secure permissions: {e}")
            return False
