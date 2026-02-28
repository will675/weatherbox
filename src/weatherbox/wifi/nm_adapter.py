"""
NetworkManager-based Wi-Fi adapter implementation.
Uses python-networkmanager or nmcli fallback for Wi-Fi operations.
"""

import logging
import subprocess
from typing import List
from src.weatherbox.wifi.adapter import WifiAdapter, WifiNetwork, WifiStatus

logger = logging.getLogger(__name__)


class NetworkManagerAdapter(WifiAdapter):
    """Wi-Fi adapter implementation using NetworkManager."""

    def __init__(self):
        """Initialize NetworkManager adapter."""
        self.use_nmcli = self._check_nmcli()
        if not self.use_nmcli:
            try:
                import gi
                gi.require_version('NM', '1.0')
                from gi.repository import NM
                self.nm = NM
                self.use_python_nm = True
                logger.info("Using python-networkmanager bindings")
            except (ImportError, ValueError) as e:
                logger.error(f"Failed to import python-networkmanager: {e}")
                self.use_python_nm = False
        else:
            self.use_python_nm = False
            logger.info("Using nmcli command-line interface")

    def _check_nmcli(self) -> bool:
        """Check if nmcli command is available."""
        try:
            result = subprocess.run(
                ['which', 'nmcli'], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def scan(self, timeout_seconds: int = 10) -> List[WifiNetwork]:
        """
        Scan for available Wi-Fi networks using NetworkManager.

        Args:
            timeout_seconds: Timeout for scan operation

        Returns:
            List of discovered WifiNetwork objects
        """
        try:
            if self.use_nmcli:
                return self._scan_nmcli(timeout_seconds)
            elif self.use_python_nm:
                return self._scan_python_nm(timeout_seconds)
            else:
                logger.error("No NetworkManager interface available")
                return []
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return []

    def _scan_nmcli(self, timeout_seconds: int) -> List[WifiNetwork]:
        """Scan using nmcli command-line interface."""
        try:
            # Use 'nmcli device wifi list' to get available networks
            result = subprocess.run(
                ['nmcli', 'device', 'wifi', 'list'],
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            networks = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 5:
                    continue

                # Format: IN-USE BSSID SSID MODE CHAN RATE SIGNAL BARS SECURITY
                ssid = parts[2]
                signal = int(parts[6])  # Signal strength as percentage
                security = parts[8] if len(parts) > 8 else "Open"

                networks.append(WifiNetwork(ssid, signal, security))

            logger.info(f"Scan found {len(networks)} networks")
            return networks
        except Exception as e:
            logger.error(f"nmcli scan failed: {e}")
            return []

    def _scan_python_nm(self, timeout_seconds: int) -> List[WifiNetwork]:
        """Scan using python-networkmanager bindings."""
        try:
            devices = self.nm.Client.new(None).get_devices()
            networks = []

            for device in devices:
                if device.get_device_type() != self.nm.DeviceType.WIFI:
                    continue

                aps = device.get_access_points()
                for ap in aps:
                    ssid_bytes = ap.get_ssid()
                    if not ssid_bytes:
                        continue

                    ssid = ssid_bytes.get_data().decode('utf-8', errors='replace')
                    strength = ap.get_strength()

                    networks.append(WifiNetwork(ssid, strength))

            logger.info(f"Scan found {len(networks)} networks")
            return networks
        except Exception as e:
            logger.error(f"python-networkmanager scan failed: {e}")
            return []

    def connect(self, ssid: str, password: str,
                timeout_seconds: int = 30) -> bool:
        """
        Connect to a Wi-Fi network using NetworkManager.

        Args:
            ssid: Network SSID
            password: Network password
            timeout_seconds: Timeout for connection attempt

        Returns:
            True if connection succeeded, False otherwise
        """
        try:
            if self.use_nmcli:
                return self._connect_nmcli(ssid, password, timeout_seconds)
            elif self.use_python_nm:
                return self._connect_python_nm(ssid, password, timeout_seconds)
            else:
                logger.error("No NetworkManager interface available")
                return False
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    def _connect_nmcli(
            self,
            ssid: str,
            password: str,
            timeout_seconds: int) -> bool:
        """Connect using nmcli command-line interface."""
        try:
            result = subprocess.run(
                ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password],
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            if result.returncode == 0:
                logger.info(f"Connected to Wi-Fi network: {ssid}")
                return True
            else:
                logger.warning(f"Failed to connect to {ssid}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"nmcli connect failed: {e}")
            return False

    def _connect_python_nm(
            self,
            ssid: str,
            password: str,
            timeout_seconds: int) -> bool:
        """Connect using python-networkmanager bindings."""
        try:
            # This is a simplified placeholder; actual implementation would need
            # to create and activate a connection using NM API
            logger.warning(
                "python-networkmanager connection not fully implemented")
            return False
        except Exception as e:
            logger.error(f"python-networkmanager connect failed: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from Wi-Fi network."""
        try:
            if self.use_nmcli:
                result = subprocess.run(
                    ['nmcli', 'device', 'disconnect', 'wlan0'],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            else:
                logger.warning(
                    "Disconnect not implemented for python-networkmanager")
                return False
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False

    def status(self) -> WifiStatus:
        """Get current Wi-Fi connection status."""
        try:
            if self.use_nmcli:
                return self._status_nmcli()
            elif self.use_python_nm:
                return self._status_python_nm()
            else:
                return WifiStatus(False)
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return WifiStatus(False)

    def _status_nmcli(self) -> WifiStatus:
        """Get status using nmcli."""
        try:
            result = subprocess.run(
                ['nmcli', 'device', 'show', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=10
            )

            connected = False
            ssid = None
            ip_address = None

            for line in result.stdout.split('\n'):
                if 'IP4.ADDRESS' in line and line.strip():
                    # Extract IP
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip_address = parts[1].strip().split('/')[0]
                        connected = True
                elif 'GENERAL.CON-PATH' in line and 'none' not in line:
                    connected = True
                elif 'GENERAL.SSID' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        ssid = parts[1].strip()

            return WifiStatus(connected, ssid, ip_address)
        except Exception as e:
            logger.error(f"nmcli status check failed: {e}")
            return WifiStatus(False)

    def _status_python_nm(self) -> WifiStatus:
        """Get status using python-networkmanager."""
        try:
            client = self.nm.Client.new(None)
            conn_active = client.get_active_connections()

            if not conn_active:
                return WifiStatus(False)

            for conn in conn_active:
                if conn.get_connection_type() == 'wireless':
                    ssid = conn.get_id()
                    return WifiStatus(True, ssid)

            return WifiStatus(False)
        except Exception as e:
            logger.error(f"python-networkmanager status check failed: {e}")
            return WifiStatus(False)
