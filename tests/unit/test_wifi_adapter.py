"""
Unit tests for Wi-Fi adapter implementations.
Tests the adapter interface and both NetworkManager and wpa_supplicant implementations.
Uses mock objects to avoid hardware dependencies.
"""

from weatherbox.wifi.adapter import WifiAdapter, WifiNetwork, WifiStatus
import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))


class TestWifiNetwork:
    """Test WifiNetwork data class."""

    def test_wifi_network_creation(self):
        """Test creating a WifiNetwork object."""
        network = WifiNetwork(
            ssid="TestNet",
            signal_strength=75,
            security="WPA2")
        assert network.ssid == "TestNet"
        assert network.signal_strength == 75
        assert network.security == "WPA2"

    def test_wifi_network_equality(self):
        """Test WifiNetwork equality by comparing attributes."""
        net1 = WifiNetwork(ssid="Test", signal_strength=50, security="Open")
        net2 = WifiNetwork(ssid="Test", signal_strength=50, security="Open")
        assert net1.ssid == net2.ssid
        assert net1.signal_strength == net2.signal_strength
        assert net1.security == net2.security

    def test_wifi_network_repr(self):
        """Test WifiNetwork string representation."""
        network = WifiNetwork(
            ssid="MyNet",
            signal_strength=80,
            security="WPA2")
        repr_str = repr(network)
        assert "MyNet" in repr_str
        assert "80" in repr_str


class TestWifiStatus:
    """Test WifiStatus data class."""

    def test_wifi_status_creation(self):
        """Test creating a WifiStatus object."""
        status = WifiStatus(
            connected=True,
            ssid="Connected",
            ip_address="192.168.1.100")
        assert status.connected is True
        assert status.ssid == "Connected"
        assert status.ip_address == "192.168.1.100"

    def test_wifi_status_disconnected(self):
        """Test disconnected status."""
        status = WifiStatus(connected=False, ssid=None, ip_address=None)
        assert status.connected is False
        assert status.ssid is None


class TestWifiAdapterInterface:
    """Test WifiAdapter abstract interface."""

    def test_wifi_adapter_is_abstract(self):
        """Test that WifiAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WifiAdapter()

    def test_wifi_adapter_requires_scan_method(self):
        """Test that subclasses must implement scan()."""
        class IncompleteAdapter(WifiAdapter):
            def connect(self, ssid, password, timeout_seconds=30):
                pass

            def disconnect(self):
                pass

            def status(self):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_wifi_adapter_requires_all_methods(self):
        """Test that all abstract methods must be implemented."""
        class PartialAdapter(WifiAdapter):
            def scan(self, timeout_seconds=10):
                pass

        with pytest.raises(TypeError):
            PartialAdapter()


class MockWifiAdapter(WifiAdapter):
    """Mock implementation of WifiAdapter for testing."""

    def scan(self, timeout_seconds=10):
        """Return mock networks."""
        return [
            WifiNetwork(ssid="TestNet1", signal_strength=80, security="WPA2"),
            WifiNetwork(ssid="TestNet2", signal_strength=60, security="WPA"),
            WifiNetwork(ssid="OpenNet", signal_strength=40, security="Open"),
        ]

    def connect(self, ssid, password, timeout_seconds=30):
        """Simulate connection."""
        if ssid == "TestNet1" and password == "correctpass":
            return True
        return False

    def disconnect(self):
        """Simulate disconnection."""
        return True

    def status(self):
        """Return mock status."""
        return WifiStatus(
            connected=True,
            ssid="TestNet1",
            ip_address="192.168.1.50")


class TestMockWifiAdapter:
    """Test the mock adapter implementation."""

    def test_scan_returns_networks(self):
        """Test scan returns list of networks."""
        adapter = MockWifiAdapter()
        networks = adapter.scan()
        assert len(networks) == 3
        assert networks[0].ssid == "TestNet1"
        assert networks[0].signal_strength == 80

    def test_connect_success(self):
        """Test successful connection."""
        adapter = MockWifiAdapter()
        result = adapter.connect("TestNet1", "correctpass")
        assert result is True

    def test_connect_failure(self):
        """Test failed connection."""
        adapter = MockWifiAdapter()
        result = adapter.connect("TestNet1", "wrongpass")
        assert result is False

    def test_disconnect(self):
        """Test disconnection."""
        adapter = MockWifiAdapter()
        result = adapter.disconnect()
        assert result is True

    def test_status(self):
        """Test status retrieval."""
        adapter = MockWifiAdapter()
        status = adapter.status()
        assert status.connected is True
        assert status.ssid == "TestNet1"
        assert status.ip_address == "192.168.1.50"


class TestNetworkManagerAdapter:
    """Test NetworkManager adapter with mocks."""

    @patch('weatherbox.wifi.nm_adapter.subprocess.run')
    def test_scan_can_be_called(self, mock_run):
        """Test that scan method can be called."""
        from weatherbox.wifi.nm_adapter import NetworkManagerAdapter

        # Mock nmcli output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="SSID   BSSID   MODE  SIGNAL\nTestNet  AA:BB:CC  Infra  80\n")

        adapter = NetworkManagerAdapter()
        networks = adapter.scan(timeout_seconds=5)

        # Verify scan was called and returned a list
        assert mock_run.called
        assert isinstance(networks, list)

    @patch('weatherbox.wifi.nm_adapter.subprocess.run')
    def test_connect_can_be_called(self, mock_run):
        """Test that connect method can be called."""
        from weatherbox.wifi.nm_adapter import NetworkManagerAdapter

        mock_run.return_value = MagicMock(returncode=0)

        adapter = NetworkManagerAdapter()
        result = adapter.connect("TestNet", "password123", timeout_seconds=10)

        # Verify nmcli was called
        assert mock_run.called
        assert isinstance(result, bool)

    @patch('weatherbox.wifi.nm_adapter.subprocess.run')
    def test_disconnect_can_be_called(self, mock_run):
        """Test that disconnect method can be called."""
        from weatherbox.wifi.nm_adapter import NetworkManagerAdapter

        mock_run.return_value = MagicMock(returncode=0)

        adapter = NetworkManagerAdapter()
        result = adapter.disconnect()

        assert mock_run.called
        assert isinstance(result, bool)


class TestWpaSupplicantAdapter:
    """Test wpa_supplicant adapter with mocks."""

    @patch('weatherbox.wifi.wpa_adapter.subprocess.run')
    def test_scan_can_be_called(self, mock_run):
        """Test that scan method can be called."""
        from weatherbox.wifi.wpa_adapter import WpaSupplicantAdapter

        # Mock wpa_cli scan_results output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="bssid  freq  signal  ssid\naa:bb:cc:dd:ee:01 2437 -50 TestNet1\n")

        adapter = WpaSupplicantAdapter()
        networks = adapter.scan(timeout_seconds=5)

        # Verify networks method returns a list
        assert isinstance(networks, list)

    @patch('weatherbox.wifi.wpa_adapter.subprocess.run')
    def test_connect_can_be_called(self, mock_run):
        """Test that connect method can be called."""
        from weatherbox.wifi.wpa_adapter import WpaSupplicantAdapter

        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n")

        adapter = WpaSupplicantAdapter()
        result = adapter.connect("TestNet", "password123", timeout_seconds=10)

        # Verify returns boolean
        assert isinstance(result, bool)

    @patch('weatherbox.wifi.wpa_adapter.subprocess.run')
    def test_disconnect_can_be_called(self, mock_run):
        """Test that disconnect method can be called."""
        from weatherbox.wifi.wpa_adapter import WpaSupplicantAdapter

        mock_run.return_value = MagicMock(returncode=0)

        adapter = WpaSupplicantAdapter()
        result = adapter.disconnect()

        assert isinstance(result, bool)


class TestAdapterCommonBehaviors:
    """Test common behavior across adapters."""

    def test_scan_returns_list_of_networks(self):
        """Test scan returns list of WifiNetwork objects."""
        adapter = MockWifiAdapter()
        result = adapter.scan()

        assert isinstance(result, list)
        assert all(isinstance(net, WifiNetwork) for net in result)

    def test_scan_timeout_parameter(self):
        """Test scan accepts timeout parameter."""
        adapter = MockWifiAdapter()
        result = adapter.scan(timeout_seconds=5)
        assert isinstance(result, list)

    def test_connect_returns_boolean(self):
        """Test connect returns boolean."""
        adapter = MockWifiAdapter()
        result = adapter.connect("TestNet", "pass")
        assert isinstance(result, bool)

    def test_connect_timeout_parameter(self):
        """Test connect accepts timeout parameter."""
        adapter = MockWifiAdapter()
        result = adapter.connect("TestNet", "pass", timeout_seconds=15)
        assert isinstance(result, bool)

    def test_disconnect_returns_boolean(self):
        """Test disconnect returns boolean."""
        adapter = MockWifiAdapter()
        result = adapter.disconnect()
        assert isinstance(result, bool)

    def test_status_returns_status_object(self):
        """Test status returns WifiStatus object."""
        adapter = MockWifiAdapter()
        result = adapter.status()
        assert isinstance(result, WifiStatus)


class TestErrorHandling:
    """Test error handling in adapters."""

    def test_scan_with_no_networks(self):
        """Test scan when no networks are available."""
        class NoNetworksAdapter(WifiAdapter):
            def scan(self, timeout_seconds=10):
                return []

            def connect(self, ssid, password, timeout_seconds=30):
                return False

            def disconnect(self):
                return True

            def status(self):
                return WifiStatus(connected=False, ssid=None, ip_address=None)

        adapter = NoNetworksAdapter()
        networks = adapter.scan()
        assert networks == []

    def test_connect_with_empty_credentials(self):
        """Test connect with empty credentials."""
        adapter = MockWifiAdapter()
        result = adapter.connect("", "")
        assert result is False

    def test_connect_with_special_characters_in_ssid(self):
        """Test connect with special characters in SSID."""
        class SpecialCharsAdapter(WifiAdapter):
            def scan(self, timeout_seconds=10):
                return [
                    WifiNetwork(
                        ssid='Net "with" quotes',
                        signal_strength=50,
                        security="WPA2")]

            def connect(self, ssid, password, timeout_seconds=30):
                return ssid.startswith("Net")

            def disconnect(self):
                return True

            def status(self):
                return WifiStatus(connected=False, ssid=None, ip_address=None)

        adapter = SpecialCharsAdapter()
        result = adapter.connect('Net "with" quotes', "password")
        assert result is True

    def test_status_when_disconnected(self):
        """Test status when device is not connected."""
        class DisconnectedAdapter(WifiAdapter):
            def scan(self, timeout_seconds=10):
                return []

            def connect(self, ssid, password, timeout_seconds=30):
                return False

            def disconnect(self):
                return True

            def status(self):
                return WifiStatus(connected=False, ssid=None, ip_address=None)

        adapter = DisconnectedAdapter()
        status = adapter.status()
        assert status.connected is False
        assert status.ssid is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
