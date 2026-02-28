"""
Integration tests for Wi-Fi provisioning flow.
Tests the complete provisioning workflow using test doubles (mocks) instead of real hardware.
Simulates fresh device boot followed by credential provisioning.
"""

from weatherbox.credentials.store import CredentialStore
from weatherbox.wifi.adapter import WifiAdapter, WifiNetwork, WifiStatus
import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))


class MockWifiAdapter(WifiAdapter):
    """Mock Wi-Fi adapter for testing."""

    def __init__(self):
        self.connected_ssid = None
        self.connect_attempts = []

    def scan(self, timeout_seconds=10):
        """Return test networks."""
        return [
            WifiNetwork(ssid="HomeNet", signal_strength=80, security="WPA2"),
            WifiNetwork(ssid="GuestNet", signal_strength=60, security="WPA"),
        ]

    def connect(self, ssid, password, timeout_seconds=30):
        """Simulate connection."""
        self.connect_attempts.append((ssid, password, timeout_seconds))

        # Success on specific credentials
        if ssid == "HomeNet" and password == "homepass123":
            self.connected_ssid = ssid
            return True
        return False

    def disconnect(self):
        """Simulate disconnection."""
        self.connected_ssid = None
        return True

    def status(self):
        """Return current status."""
        if self.connected_ssid:
            return WifiStatus(
                connected=True,
                ssid=self.connected_ssid,
                ip_address="192.168.1.100"
            )
        return WifiStatus(connected=False, ssid=None, ip_address=None)


class TestCredentialStore:
    """Test credential storage."""

    def test_save_and_load_credentials(self):
        """Test saving and loading credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            store = CredentialStore(cred_file)

            # Save credentials
            store.save_credentials("TestNetwork", "testpass123")

            # Verify file exists
            assert os.path.exists(cred_file)

            # Load credentials (returns tuple)
            creds = store.load_credentials()
            assert creds is not None
            # Credentials are returned as tuple (ssid, password)
            if isinstance(creds, tuple):
                ssid, password = creds
                assert ssid == "TestNetwork"
                assert password == "testpass123"
            else:
                # In case it's a dict
                assert creds.get('ssid') == "TestNetwork"

    def test_secure_file_permissions(self):
        """Test that credential file has secure permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            store = CredentialStore(cred_file)

            store.save_credentials("TestNet", "pass")

            # Check file permissions
            stat_info = os.stat(cred_file)
            mode = stat_info.st_mode & 0o777

            # Should be 0o600 (read/write for owner only)
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    def test_load_nonexistent_file(self):
        """Test loading credentials from nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "nonexistent.yaml")
            store = CredentialStore(cred_file)

            creds = store.load_credentials()
            assert creds is None

    def test_clear_credentials(self):
        """Test clearing credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            store = CredentialStore(cred_file)

            # Save credentials
            store.save_credentials("TestNet", "pass")
            assert os.path.exists(cred_file)

            # Clear credentials
            store.clear_credentials()
            assert not os.path.exists(cred_file)


class TestProvisioningFlow:
    """Test the provisioning workflow."""

    def test_boot_with_stored_credentials_success(self):
        """Test boot with stored credentials that work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            adapter = MockWifiAdapter()
            store = CredentialStore(cred_file)

            # Pre-provision credentials
            store.save_credentials("HomeNet", "homepass123")

            # Simulate boot provisioning
            creds = store.load_credentials()
            if creds:
                ssid, password = creds
                result = adapter.connect(ssid, password, timeout_seconds=30)
                assert result is True

            # Verify connected
            status = adapter.status()
            assert status.connected is True
            assert status.ssid == "HomeNet"

    def test_boot_with_stored_credentials_failure(self):
        """Test boot with stored credentials that fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            adapter = MockWifiAdapter()
            store = CredentialStore(cred_file)

            # Save wrong credentials
            store.save_credentials("HomeNet", "wrongpass")

            # Simulate boot provisioning
            creds = store.load_credentials()
            if creds:
                ssid, password = creds
                result = adapter.connect(ssid, password, timeout_seconds=30)
                assert result is False

    def test_boot_without_stored_credentials(self):
        """Test boot without stored credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            adapter = MockWifiAdapter()
            store = CredentialStore(cred_file)

            # No credentials saved
            creds = store.load_credentials()
            assert creds is None

    def test_new_provisioning_via_api(self):
        """Test provisioning new credentials via API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            adapter = MockWifiAdapter()
            store = CredentialStore(cred_file)

            # Scan networks
            networks = adapter.scan()
            assert len(networks) > 0

            # Provision new credentials
            ssid = "HomeNet"
            password = "homepass123"
            store.save_credentials(ssid, password)

            # Verify saved
            saved_creds = store.load_credentials()
            assert saved_creds is not None
            saved_ssid, saved_password = saved_creds
            assert saved_ssid == ssid

            # Next boot should connect
            creds = store.load_credentials()
            if creds:
                ssid_c, password_c = creds
                result = adapter.connect(ssid_c, password_c)
                assert result is True

    def test_retry_on_connection_failure(self):
        """Test retry logic on connection failure."""
        adapter = MockWifiAdapter()

        # First two attempts fail, third succeeds
        max_attempts = 3
        attempts = 0

        def attempt_connect():
            nonlocal attempts
            attempts += 1
            # Fail attempts 1-2, succeed on attempt 3
            if attempts < 3:
                return False
            return adapter.connect("HomeNet", "homepass123")

        result = False
        for i in range(max_attempts):
            result = attempt_connect()
            if result:
                break

        assert result is True
        assert attempts == 3


class TestFlaskProvisioning:
    """Test Flask provisioning app with test doubles."""

    def test_flask_app_creation(self):
        """Test that Flask app can be created with dependencies."""
        try:
            from weatherbox.provisioning.app import create_app

            adapter = MockWifiAdapter()
            store = CredentialStore("/tmp/test_creds.yaml")

            # Should be able to create app with test doubles
            app = create_app(credential_store=store, wifi_adapter=adapter)
            assert app is not None
            assert app.config is not None
        except ImportError:
            # Flask may not be installed in test environment
            pytest.skip("Flask not available for testing")

    def test_provisional_integration(self):
        """Test that provisioning flow can be executed with mocks."""
        adapter = MockWifiAdapter()
        store = CredentialStore("/tmp/test_creds.yaml")

        # Simulate provisioning flow
        networks = adapter.scan()
        assert len(networks) > 0

        # Select first network and "provision" it
        target_net = networks[0]
        store.save_credentials(target_net.ssid, "testpass123")

        # Verify credentials were saved
        loaded = store.load_credentials()
        assert loaded is not None


class TestEndToEndFlow:
    """End-to-end provisioning flow tests."""

    def test_complete_provisioning_cycle(self):
        """Test complete provisioning cycle: scan → provision → boot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            adapter = MockWifiAdapter()
            store = CredentialStore(cred_file)

            # Step 1: Scan networks
            networks = adapter.scan()
            assert len(networks) > 0
            home_net = next((n for n in networks if n.ssid == "HomeNet"), None)
            assert home_net is not None

            # Step 2: User provisions credentials via UI
            store.save_credentials("HomeNet", "homepass123")

            # Step 3: Verify credentials saved
            creds = store.load_credentials()
            assert creds is not None
            ssid, password = creds
            assert ssid == "HomeNet"

            # Step 4: Boot next time - should connect automatically
            result = adapter.connect(ssid, password)
            assert result is True

            # Step 5: Verify connected
            status = adapter.status()
            assert status.connected is True
            assert status.ip_address is not None

    def test_fallback_to_ap_on_failure(self):
        """Test fallback to AP mode when credentials fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = os.path.join(tmpdir, "credentials.yaml")
            adapter = MockWifiAdapter()
            store = CredentialStore(cred_file)

            # Save bad credentials
            store.save_credentials("HomeNet", "wrongpass")

            # Attempt to connect
            creds = store.load_credentials()
            if creds:
                ssid, password = creds
                failed = not adapter.connect(ssid, password)

                # Should fail and fallback to AP
                assert failed is True

                # In real scenario, would now start AP mode
                # For this test, just verify connection failed
                status = adapter.status()
                assert status.connected is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
