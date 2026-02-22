"""
wpa_supplicant-based Wi-Fi adapter implementation.
Provides fallback for systems without NetworkManager.
Shells out to wpa_cli and wpa_supplicant for Wi-Fi operations.
"""

import logging
import subprocess
import re
from typing import List, Optional
from src.weatherbox.wifi.adapter import WifiAdapter, WifiNetwork, WifiStatus

logger = logging.getLogger(__name__)


class WpaSupplicantAdapter(WifiAdapter):
    """Wi-Fi adapter implementation using wpa_supplicant / wpa_cli."""
    
    def __init__(self, interface: str = "wlan0"):
        """
        Initialize wpa_supplicant adapter.
        
        Args:
            interface: Wi-Fi interface name (default: wlan0)
        """
        self.interface = interface
        self._check_available()
    
    def _check_available(self) -> bool:
        """Check if wpa_cli is available."""
        try:
            result = subprocess.run(['which', 'wpa_cli'], capture_output=True, timeout=5)
            if result.returncode != 0:
                logger.warning("wpa_cli not found; wpa_supplicant adapter will not function")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to check wpa_cli availability: {e}")
            return False
    
    def scan(self, timeout_seconds: int = 10) -> List[WifiNetwork]:
        """
        Scan for available Wi-Fi networks using wpa_cli.
        
        Args:
            timeout_seconds: Timeout for scan operation
        
        Returns:
            List of discovered WifiNetwork objects
        """
        try:
            # Start scan
            result = subprocess.run(
                ['wpa_cli', '-i', self.interface, 'scan'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'FAIL' in result.stdout:
                logger.warning(f"wpa_cli scan failed: {result.stdout}")
                return []
            
            # Get scan results
            result = subprocess.run(
                ['wpa_cli', '-i', self.interface, 'scan_results'],
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            networks = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if not line.strip():
                    continue
                
                # Format: bssid / frequency / signal level / flags / ssid
                parts = line.split('\t')
                if len(parts) < 5:
                    continue
                
                bssid = parts[0]
                frequency = parts[1]
                signal_level = int(parts[2])  # dBm value
                flags = parts[3]
                ssid = parts[4] if len(parts) > 4 else ""
                
                # Convert dBm to percentage (roughly -30 dBm = 100%, -90 dBm = 0%)
                signal_strength = max(0, min(100, 2 * (signal_level + 100)))
                
                # Parse security from flags
                security = self._parse_security_flags(flags)
                
                networks.append(WifiNetwork(ssid, signal_strength, security))
            
            logger.info(f"Scan found {len(networks)} networks")
            return networks
        except Exception as e:
            logger.error(f"wpa_cli scan failed: {e}")
            return []
    
    def _parse_security_flags(self, flags: str) -> str:
        """Parse security type from wpa_cli flags."""
        if 'WPA2' in flags or 'RSN' in flags:
            return 'WPA2'
        elif 'WPA' in flags:
            return 'WPA'
        elif 'WEP' in flags:
            return 'WEP'
        else:
            return 'Open'
    
    def connect(self, ssid: str, password: str, timeout_seconds: int = 30) -> bool:
        """
        Connect to a Wi-Fi network using wpa_cli.
        
        Args:
            ssid: Network SSID
            password: Network password
            timeout_seconds: Timeout for connection attempt
        
        Returns:
            True if connection succeeded, False otherwise
        """
        try:
            # Add network
            result = subprocess.run(
                ['wpa_cli', '-i', self.interface, 'add_network'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'FAIL' in result.stdout:
                logger.error(f"Failed to add network: {result.stdout}")
                return False
            
            network_id = result.stdout.strip()
            logger.debug(f"Added network with ID: {network_id}")
            
            # Set SSID
            subprocess.run(
                ['wpa_cli', '-i', self.interface, 'set_network', network_id, 'ssid', f'"{ssid}"'],
                capture_output=True,
                timeout=5
            )
            
            # Set password
            subprocess.run(
                ['wpa_cli', '-i', self.interface, 'set_network', network_id, 'psk', f'"{password}"'],
                capture_output=True,
                timeout=5
            )
            
            # Enable network
            result = subprocess.run(
                ['wpa_cli', '-i', self.interface, 'enable_network', network_id],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'FAIL' in result.stdout:
                logger.error(f"Failed to enable network: {result.stdout}")
                return False
            
            # Wait for connection
            for i in range(timeout_seconds):
                status = self.status()
                if status.connected and status.ssid == ssid:
                    logger.info(f"Connected to {ssid}")
                    return True
                
                import time
                time.sleep(1)
            
            logger.warning(f"Connection to {ssid} timed out after {timeout_seconds}s")
            return False
        except Exception as e:
            logger.error(f"wpa_cli connect failed: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Wi-Fi network."""
        try:
            result = subprocess.run(
                ['wpa_cli', '-i', self.interface, 'disconnect'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'FAIL' not in result.stdout
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False
    
    def status(self) -> WifiStatus:
        """Get current Wi-Fi connection status."""
        try:
            result = subprocess.run(
                ['wpa_cli', '-i', self.interface, 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            connected = False
            ssid = None
            ip_address = None
            
            for line in result.stdout.split('\n'):
                if line.startswith('wpa_state=COMPLETED'):
                    connected = True
                elif line.startswith('ssid='):
                    ssid = line.split('=', 1)[1]
                elif line.startswith('ip_address='):
                    ip_address = line.split('=', 1)[1]
            
            return WifiStatus(connected, ssid, ip_address)
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return WifiStatus(False)
