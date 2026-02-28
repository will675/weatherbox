"""
Boot-time Wi-Fi provisioning orchestration.
Attempts to connect to stored credentials, falls back to AP mode if connection fails.
"""

from src.weatherbox.logging import configure_logging, get_logger
from src.weatherbox.credentials.store import CredentialStore
from src.weatherbox.wifi.wpa_adapter import WpaSupplicantAdapter
from src.weatherbox.wifi.nm_adapter import NetworkManagerAdapter
from src.weatherbox.wifi.adapter import WifiAdapter
import time
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


logger = get_logger("provisioning.boot")


class BootProvisioner:
    """Orchestrates Wi-Fi provisioning at boot time."""

    def __init__(
            self,
            credential_file: str = "/etc/weatherbox/credentials.yaml"):
        """
        Initialize boot provisioner.

        Args:
            credential_file: Path to stored credentials
        """
        self.credential_store = CredentialStore(credential_file)
        self.wifi_adapter = self._select_wifi_adapter()
        self.logged_in = False

    def _select_wifi_adapter(self) -> WifiAdapter:
        """
        Select best available Wi-Fi adapter.
        Try NetworkManager first, fallback to wpa_supplicant.

        Returns:
            WifiAdapter implementation
        """
        try:
            logger.info("Attempting to use NetworkManager adapter")
            adapter = NetworkManagerAdapter()
            logger.info("Using NetworkManager adapter")
            return adapter
        except Exception as e:
            logger.warning(f"NetworkManager not available: {e}")
            logger.info("Falling back to wpa_supplicant adapter")
            return WpaSupplicantAdapter()

    def provision(self) -> bool:
        """
        Perform boot-time provisioning flow:
        1. Load stored credentials
        2. Attempt to connect (up to 3 attempts with backoff)
        3. Fall back to AP mode if connection fails

        Returns:
            True if network is connected or AP is ready, False on critical failure
        """
        logger.info("Starting boot provisioning flow")

        # Step 1: Try to connect to stored credentials
        credentials = self.credential_store.load_credentials()
        if credentials:
            ssid, password = credentials
            logger.info(f"Found stored credentials for SSID: {ssid}")

            if self._attempt_connection(ssid, password):
                logger.info("Successfully connected to stored network")
                self.logged_in = True
                return True
            else:
                logger.warning(
                    "Failed to connect to stored network; falling back to AP mode")
        else:
            logger.info(
                "No stored credentials found; starting AP for provisioning")

        # Step 2: Start AP for provisioning
        if self._start_ap():
            logger.info("Access point started successfully")
            return True
        else:
            logger.error("Failed to start access point")
            return False

    def _attempt_connection(
            self,
            ssid: str,
            password: str,
            max_attempts: int = 3) -> bool:
        """
        Attempt to connect to a network with retries and backoff.

        Args:
            ssid: Network SSID
            password: Network password
            max_attempts: Maximum connection attempts

        Returns:
            True if connection succeeded, False otherwise
        """
        backoff_seconds = 5

        for attempt in range(1, max_attempts + 1):
            logger.info(
                f"Connection attempt {attempt}/{max_attempts} to {ssid}")

            try:
                if self.wifi_adapter.connect(
                        ssid, password, timeout_seconds=30):
                    logger.info(f"Connected to {ssid} on attempt {attempt}")
                    return True
                else:
                    logger.warning(f"Connection attempt {attempt} failed")
            except Exception as e:
                logger.error(
                    f"Connection attempt {attempt} raised exception: {e}")

            # Backoff between attempts (except after last attempt)
            if attempt < max_attempts:
                logger.debug(f"Waiting {backoff_seconds}s before retry")
                time.sleep(backoff_seconds)

        logger.warning(f"All {max_attempts} connection attempts failed")
        return False

    def _start_ap(self) -> bool:
        """
        Start access point for provisioning.

        Returns:
            True if AP started successfully, False otherwise
        """
        try:
            from src.weatherbox.provisioning.ap_manager import AccessPointManager

            ap_manager = AccessPointManager(
                ssid="weatherbox-setup",
                mode="open"  # Open AP with captive portal
            )

            if ap_manager.start():
                logger.info("Access point started")
                return True
            else:
                logger.error("Failed to start access point")
                return False
        except ImportError:
            logger.error("AP manager module not available")
            return False
        except Exception as e:
            logger.error(f"Error starting AP: {e}")
            return False


def main():
    """Boot provisioning entry point."""
    # Configure logging
    configure_logging(
        log_level="INFO",
        log_file="/var/log/weatherbox/provisioning.log")

    logger.info("=" * 70)
    logger.info("Weatherbox Boot Provisioner Starting")
    logger.info("=" * 70)

    try:
        provisioner = BootProvisioner()
        success = provisioner.provision()

        if success:
            logger.info("Boot provisioning completed successfully")
            if provisioner.logged_in:
                logger.info("Device is connected to Wi-Fi network")
            else:
                logger.info(
                    "Access point is ready for provisioning at http://192.168.4.1:8080")

            # Start provisioning service/display service would happen here
            # For now, just log success
            return 0
        else:
            logger.error(
                "Boot provisioning failed; device may not be operable")
            return 1

    except KeyboardInterrupt:
        logger.warning("Boot provisioning interrupted by user")
        return 130
    except Exception as e:
        logger.error(
            f"Unexpected error during boot provisioning: {e}",
            exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
