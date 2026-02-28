"""
Wi-Fi adapter interface for abstraction over NetworkManager / wpa_supplicant.
Allows test doubles to be injected in CI environments.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class WifiNetwork:
    """Represents a discovered Wi-Fi network."""

    def __init__(
            self,
            ssid: str,
            signal_strength: int,
            security: Optional[str] = None):
        """
        Args:
            ssid: Network SSID
            signal_strength: Signal strength in dBm or percentage (implementation-dependent)
            security: Security type (e.g., 'WPA2', 'WEP', 'Open')
        """
        self.ssid = ssid
        self.signal_strength = signal_strength
        self.security = security or "Open"

    def __repr__(self) -> str:
        return f"WifiNetwork(ssid={
            self.ssid!r}, strength={
            self.signal_strength}, security={
            self.security!r})"


class WifiStatus:
    """Represents the current Wi-Fi connection status."""

    def __init__(
            self,
            connected: bool,
            ssid: Optional[str] = None,
            ip_address: Optional[str] = None):
        self.connected = connected
        self.ssid = ssid
        self.ip_address = ip_address

    def __repr__(self) -> str:
        if self.connected:
            return f"WifiStatus(connected=True, ssid={
                self.ssid!r}, ip={
                self.ip_address!r})"
        return "WifiStatus(connected=False)"


class WifiAdapter(ABC):
    """Abstract base class for Wi-Fi adapter implementations."""

    @abstractmethod
    def scan(self, timeout_seconds: int = 10) -> List[WifiNetwork]:
        """
        Scan for available Wi-Fi networks.

        Args:
            timeout_seconds: Timeout for scan operation

        Returns:
            List of discovered WifiNetwork objects

        Raises:
            RuntimeError: If scan operation fails
        """

    @abstractmethod
    def connect(self, ssid: str, password: str,
                timeout_seconds: int = 30) -> bool:
        """
        Attempt to connect to a Wi-Fi network.

        Args:
            ssid: Network SSID to connect to
            password: Network password
            timeout_seconds: Timeout for connection attempt

        Returns:
            True if connection succeeded, False otherwise

        Raises:
            RuntimeError: If connection operation fails
        """

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the current Wi-Fi network.

        Returns:
            True if disconnection succeeded, False otherwise

        Raises:
            RuntimeError: If disconnection operation fails
        """

    @abstractmethod
    def status(self) -> WifiStatus:
        """
        Get current Wi-Fi connection status.

        Returns:
            WifiStatus object indicating current connection state

        Raises:
            RuntimeError: If status retrieval fails
        """
