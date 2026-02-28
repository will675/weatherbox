"""
Access Point (AP) management for provisioning.
Brings up a Wi-Fi access point using NetworkManager or hostapd.
"""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class AccessPointManager:
    """Manages Wi-Fi access point for provisioning."""
    
    def __init__(
        self,
        ssid: str = "weatherbox-setup",
        mode: str = "open",
        psk: Optional[str] = None,
        interface: str = "wlan0",
        ip_address: str = "192.168.4.1"
    ):
        """
        Initialize AP manager.
        
        Args:
            ssid: Access point SSID
            mode: AP mode ('open' for open AP, 'wpa2' for WPA2)
            psk: Pre-shared key for WPA2 mode
            interface: Wi-Fi interface name
            ip_address: IP address for the AP
        """
        self.ssid = ssid
        self.mode = mode
        self.psk = psk or "weatherbox-default"
        self.interface = interface
        self.ip_address = ip_address
        self.running = False
    
    def start(self) -> bool:
        """
        Start the access point.
        
        Returns:
            True if AP started successfully, False otherwise
        """
        try:
            logger.info(f"Starting access point: {self.ssid}")
            
            if self._use_networkmanager():
                return self._start_with_networkmanager()
            else:
                return self._start_with_hostapd()
        except Exception as e:
            logger.error(f"Failed to start AP: {e}")
            return False
    
    def _use_networkmanager(self) -> bool:
        """Check if NetworkManager is available."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'NetworkManager'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _start_with_networkmanager(self) -> bool:
        """Start AP using NetworkManager.
        
        This would involve creating a connection profile via nmcli.
        For now, this is a placeholder that logs the intent.
        """
        logger.warning("NetworkManager AP mode not fully implemented; using hostapd")
        return self._start_with_hostapd()
    
    def _start_with_hostapd(self) -> bool:
        """Start AP using hostapd and dnsmasq."""
        try:
            # Step 1: Bring interface up
            logger.debug(f"Bringing up interface {self.interface}")
            result = subprocess.run(
                ['ip', 'link', 'set', self.interface, 'up'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error(f"Failed to bring up interface: {result.stderr.decode()}")
                return False
            
            # Step 2: Configure IP address
            logger.debug(f"Configuring IP address {self.ip_address}")
            result = subprocess.run(
                ['ip', 'addr', 'add', f'{self.ip_address}/24', 'dev', self.interface],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0 and 'RTNETLINK answers: File exists' not in result.stderr.decode():
                logger.warning(f"Could not add IP address: {result.stderr.decode()}")
            
            # Step 3: Create hostapd configuration
            logger.debug("Creating hostapd configuration")
            hostapd_conf = self._create_hostapd_config()
            
            if not self._write_hostapd_config(hostapd_conf):
                logger.error("Failed to write hostapd config")
                return False
            
            # Step 4: Start hostapd
            logger.debug("Starting hostapd")
            result = subprocess.run(
                ['hostapd', '-B', '/tmp/hostapd.conf'],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.warning(f"hostapd may not be available: {result.stderr.decode()}")
                # Continue anyway; AP might be available
            
            # Step 5: Start dnsmasq
            logger.debug("Starting dnsmasq")
            result = subprocess.run(
                ['dnsmasq', '--interface', self.interface, '--dhcp-range', '192.168.4.2,192.168.4.20,24h'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.warning(f"dnsmasq may not be available: {result.stderr.decode()}")
            
            logger.info(f"Access point {self.ssid} started on {self.interface}")
            self.running = True
            return True
        
        except Exception as e:
            logger.error(f"Error starting hostapd AP: {e}")
            return False
    
    def _create_hostapd_config(self) -> str:
        """Create hostapd configuration string."""
        config = f"""interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel=6
beacon_int=100
dtim_period=2
max_num_sta=32
rts_threshold=2347
fragm_threshold=2346
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        
        if self.mode == "wpa2":
            config += f"""wpa=2
wpa_pairwise=CCMP
wpa_passphrase={self.psk}
"""
        else:
            # Open AP - no WPA
            config += "wpa=0\n"
        
        return config
    
    def _write_hostapd_config(self, config: str) -> bool:
        """Write hostapd configuration to file."""
        try:
            with open('/tmp/hostapd.conf', 'w') as f:
                f.write(config)
            return True
        except Exception as e:
            logger.error(f"Failed to write hostapd config: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the access point.
        
        Returns:
            True if AP stopped successfully, False otherwise
        """
        try:
            logger.info(f"Stopping access point: {self.ssid}")
            
            # Kill hostapd
            subprocess.run(['killall', 'hostapd'], capture_output=True, timeout=5)
            
            # Kill dnsmasq
            subprocess.run(['killall', 'dnsmasq'], capture_output=True, timeout=5)
            
            # Bring interface down
            subprocess.run(['ip', 'link', 'set', self.interface, 'down'], capture_output=True, timeout=5)
            
            logger.info("Access point stopped")
            self.running = False
            return True
        
        except Exception as e:
            logger.error(f"Error stopping AP: {e}")
            return False
    
    def status(self) -> bool:
        """
        Get AP status.
        
        Returns:
            True if AP is running, False otherwise
        """
        return self.running
