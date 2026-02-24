#!/bin/bash
#
# Smoke Test: Wi-Fi Provisioning Service
# Runs automated checks on a live Raspberry Pi to verify provisioning service health
#
# Usage: sudo ./smoke_provision.sh [OPTIONS]
# Options:
#   -v, --verbose     Enable verbose output
#   -q, --quiet       Minimal output (pass/fail only)
#   -s, --skip-ap     Skip AP mode tests (requires network interface restart)
#   --check-only      Don't start service, just check existing installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=0
QUIET=0
SKIP_AP=0
CHECK_ONLY=0
ERRORS=0
WARNINGS=0
PASSED=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -q|--quiet)
            QUIET=1
            shift
            ;;
        -s|--skip-ap)
            SKIP_AP=1
            shift
            ;;
        --check-only)
            CHECK_ONLY=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    [[ $QUIET -eq 0 ]] && echo -e "${BLUE}ℹ${NC} $1"
}

log_pass() {
    [[ $QUIET -eq 0 ]] && echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

log_warn() {
    [[ $QUIET -eq 0 ]] && echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

log_verbose() {
    [[ $VERBOSE -eq 1 ]] && echo -e "${BLUE}  →${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_fail "This script must be run with sudo"
        exit 1
    fi
}

# Check system prerequisites
check_prerequisites() {
    log_info "Checking system prerequisites..."
    
    # Python
    if ! command -v python3 &> /dev/null; then
        log_fail "Python 3 not found"
        return 1
    fi
    log_pass "Python 3 installed"
    log_verbose "$(python3 --version)"
    
    # Pip
    if ! command -v pip3 &> /dev/null; then
        log_warn "pip3 not found (may be needed for install)"
    else
        log_pass "pip3 found"
    fi
    
    # NetworkManager or wpa_supplicant
    if command -v nmcli &> /dev/null; then
        log_pass "NetworkManager detected (nmcli)"
        log_verbose "$(nmcli --version)"
    elif command -v wpa_cli &> /dev/null; then
        log_pass "wpa_supplicant detected (wpa_cli)"
    else
        log_fail "Neither NetworkManager nor wpa_supplicant found"
        return 1
    fi
    
    # hostapd and dnsmasq for AP mode
    local hostapd_status="not installed"
    local dnsmasq_status="not installed"
    
    if dpkg -l | grep -q "^ii.*hostapd"; then
        hostapd_status="installed"
        log_pass "hostapd installed"
    else
        log_warn "hostapd not installed (required for AP mode)"
    fi
    
    if dpkg -l | grep -q "^ii.*dnsmasq"; then
        dnsmasq_status="installed"
        log_pass "dnsmasq installed"
    else
        log_warn "dnsmasq not installed (required for AP mode)"
    fi
    
    return 0
}

# Check provisioning installation
check_installation() {
    log_info "Checking provisioning installation..."
    
    local base_path="${1:-/opt/weatherbox}"
    
    # Check main service file
    if [[ -f /etc/systemd/system/weatherbox-provisioning.service ]]; then
        log_pass "Systemd service file found"
        log_verbose "$(systemctl status weatherbox-provisioning --no-pager 2>&1 | head -3)"
    else
        log_fail "Systemd service file not found"
        return 1
    fi
    
    # Check Python packages
    local missing_packages=()
    for pkg in flask requests yaml; do
        if ! python3 -c "import ${pkg}" 2>/dev/null; then
            missing_packages+=("$pkg")
        else
            log_pass "Python module '${pkg}' found"
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        log_warn "Missing Python packages: ${missing_packages[*]}"
        return 1
    fi
    
    return 0
}

# Check service status
check_service_status() {
    log_info "Checking service status..."
    
    if systemctl is-active --quiet weatherbox-provisioning; then
        log_pass "Service is running"
    else
        if [[ $CHECK_ONLY -eq 0 ]]; then
            log_info "Starting service..."
            systemctl start weatherbox-provisioning || {
                log_fail "Failed to start service"
                return 1
            }
            sleep 2
            log_pass "Service started successfully"
        else
            log_fail "Service is not running"
            return 1
        fi
    fi
    
    # Check service enabled
    if systemctl is-enabled --quiet weatherbox-provisioning; then
        log_pass "Service is enabled (auto-start on boot)"
    else
        log_warn "Service is not enabled for auto-start"
    fi
    
    return 0
}

# Check credential storage
check_credential_storage() {
    log_info "Checking credential storage..."
    
    local cred_path="/etc/weatherbox/credentials.yaml"
    
    # Check if directory exists
    if [[ ! -d "/etc/weatherbox" ]]; then
        log_warn "Credentials directory not found: /etc/weatherbox"
        mkdir -p /etc/weatherbox 2>/dev/null || {
            log_fail "Cannot create credentials directory"
            return 1
        }
        log_pass "Created credentials directory"
    else
        log_pass "Credentials directory exists"
    fi
    
    # Check permissions on directory
    local dir_perms=$(stat -c %a /etc/weatherbox)
    if [[ "$dir_perms" == "700" || "$dir_perms" == "750" || "$dir_perms" == "755" ]]; then
        log_pass "Directory permissions acceptable (${dir_perms})"
    else
        log_warn "Directory permissions: ${dir_perms} (expected 700-755)"
    fi
    
    # If credential file exists, check its permissions
    if [[ -f "$cred_path" ]]; then
        local file_perms=$(stat -c %a "$cred_path")
        if [[ "$file_perms" == "600" ]]; then
            log_pass "Credential file has secure permissions (${file_perms})"
        else
            log_warn "Credential file permissions: ${file_perms} (should be 600)"
        fi
    else
        log_pass "No existing credentials (fresh state)"
    fi
    
    return 0
}

# Check logging
check_logging() {
    log_info "Checking logging..."
    
    # Check systemd journal
    local recent_logs=$(journalctl -u weatherbox-provisioning -n 5 --no-pager 2>/dev/null | wc -l)
    if [[ $recent_logs -gt 0 ]]; then
        log_pass "Service logs found in systemd journal"
        [[ $VERBOSE -eq 1 ]] && journalctl -u weatherbox-provisioning -n 3 --no-pager | sed 's/^/  /'
    else
        log_warn "No recent logs found"
    fi
    
    return 0
}

# Check Wi-Fi adapter
check_wifi_adapter() {
    log_info "Checking Wi-Fi adapter..."
    
    # Check for wireless interfaces
    local wifi_interfaces=$(find /sys/class/net -type l -exec basename {} \; | grep -E '^w' || true)
    
    if [[ -z "$wifi_interfaces" ]]; then
        log_fail "No Wi-Fi interfaces found"
        return 1
    fi
    
    log_pass "Wi-Fi interface(s) found: $wifi_interfaces"
    
    # Check interface status
    for iface in $wifi_interfaces; do
        local if_up=$(ip link show "$iface" | grep -q "UP" && echo "up" || echo "down")
        log_pass "  Interface $iface is $if_up"
    done
    
    return 0
}

# Test Wi-Fi scan (if adapter available)
test_wifi_scan() {
    if [[ $SKIP_AP -eq 1 ]]; then
        log_info "Skipping Wi-Fi scan test (--skip-ap)"
        return 0
    fi
    
    log_info "Testing Wi-Fi scan capability..."
    
    if command -v nmcli &> /dev/null; then
        log_verbose "Using nmcli to scan networks..."
        if nmcli device wifi list &>/dev/null; then
            local networks=$(nmcli device wifi list | grep -v "SSID" | wc -l)
            log_pass "Wi-Fi scan successful ($networks networks detected)"
        else
            log_warn "Wi-Fi scan returned no results"
        fi
    elif command -v wpa_cli &> /dev/null; then
        log_verbose "Using wpa_cli to scan networks..."
        if wpa_cli scan &>/dev/null; then
            sleep 2
            if wpa_cli scan_results &>/dev/null; then
                log_pass "Wi-Fi scan successful (wpa_cli)"
            fi
        fi
    else
        log_warn "No Wi-Fi scan tool available"
    fi
    
    return 0
}

# Test credential store (read/write)
test_credential_storage() {
    log_info "Testing credential storage..."
    
    local test_creds="/tmp/test_credentials_$$.yaml"
    
    # Write test credentials
    cat > "$test_creds" <<EOF
ssid: TestNetwork
password: testpass123
EOF
    
    # Check file created
    if [[ -f "$test_creds" ]]; then
        log_pass "Test credentials file created"
        
        # Read it back
        local ssid=$(grep "^ssid:" "$test_creds" | cut -d' ' -f2)
        if [[ "$ssid" == "TestNetwork" ]]; then
            log_pass "Test credentials read successfully"
        else
            log_fail "Failed to read test credentials"
        fi
        
        # Clean up
        rm "$test_creds"
    else
        log_fail "Failed to create test credentials file"
        return 1
    fi
    
    return 0
}

# Check Flask app endpoints (if service is running)
check_flask_endpoints() {
    log_info "Checking Flask app endpoints..."
    
    local health_endpoint="http://127.0.0.1:8080/health"
    
    # Try to reach health endpoint
    if curl -s "$health_endpoint" &>/dev/null; then
        log_pass "Flask health endpoint reachable"
    else
        log_warn "Flask endpoint not reachable (service may still be starting)"
    fi
    
    return 0
}

# Summary
print_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Test Summary:"
    echo -e "  ${GREEN}Passed: $PASSED${NC}"
    echo -e "  ${RED}Errors: $ERRORS${NC}"
    echo -e "  ${YELLOW}Warnings: $WARNINGS${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "${GREEN}✓ Smoke test PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ Smoke test FAILED (${ERRORS} errors)${NC}"
        return 1
    fi
}

# Main execution
main() {
    log_info "Wi-Fi Provisioning Service Smoke Test"
    echo ""
    
    check_root
    check_prerequisites || true
    check_installation || true
    check_service_status || true
    check_credential_storage || true
    check_logging
    check_wifi_adapter || true
    test_wifi_scan || true
    test_credential_storage || true
    check_flask_endpoints || true
    
    print_summary
}

# Run main function
main
exit $?
