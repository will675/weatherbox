"""
Flask captive portal for Wi-Fi provisioning.
Provides web UI for scanning and configuring Wi-Fi credentials.
Includes CSRF protections and server-side validation.
"""

import logging
import os
from flask import Flask, render_template, request, jsonify
from itsdangerous import URLSafeTimedSerializer

logger = logging.getLogger(__name__)


def create_app(credential_store=None, wifi_adapter=None) -> Flask:
    """
    Create and configure Flask application for provisioning.

    Args:
        credential_store: CredentialStore instance
        wifi_adapter: WifiAdapter instance

    Returns:
        Configured Flask app
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )

    # Security configuration
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'weatherbox-provisioning-dev-key')
    # Disabled for local network access
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # CSRF token serializer
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    # Dependency injection
    app.credential_store = credential_store
    app.wifi_adapter = wifi_adapter

    @app.before_request
    def initialize_session():
        """Initialize CSRF token in session."""
        from flask import session
        if 'csrf_token' not in session:
            session['csrf_token'] = serializer.dumps(
                {'nonce': os.urandom(16).hex()})

    @app.context_processor
    def inject_csrf_token():
        """Inject CSRF token into template context."""
        from flask import session
        return {'csrf_token': session.get('csrf_token', '')}

    def verify_csrf_token(token: str) -> bool:
        """Verify CSRF token."""
        try:
            serializer.loads(token, max_age=3600)  # Valid for 1 hour
            return True
        except Exception:
            return False

    @app.route('/', methods=['GET'])
    def index():
        """Serve provisioning UI."""
        logger.info("Provisioning UI requested")
        return render_template('index.html')

    @app.route('/api/scan', methods=['POST'])
    def scan():
        """
        Scan for available Wi-Fi networks.

        Returns:
            JSON with list of networks or error
        """
        # Verify CSRF token
        data = request.get_json() or {}
        csrf_token = data.get('csrf_token')

        if not csrf_token or not verify_csrf_token(csrf_token):
            logger.warning("CSRF token verification failed for /scan")
            return jsonify({'error': 'Invalid CSRF token'}), 403

        try:
            if not app.wifi_adapter:
                logger.error("Wi-Fi adapter not configured")
                return jsonify({'error': 'Wi-Fi adapter not available'}), 500

            logger.info("Starting Wi-Fi scan")
            networks = app.wifi_adapter.scan(timeout_seconds=10)

            # Convert to JSON-serializable format
            network_list = [
                {
                    'ssid': net.ssid,
                    'strength': net.signal_strength,
                    'security': net.security
                }
                for net in networks
                if net.ssid  # Filter out hidden networks
            ]

            logger.info(f"Scan complete: found {len(network_list)} networks")
            return jsonify({'networks': network_list})

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return jsonify({'error': 'Scan failed'}), 500

    @app.route('/api/provision', methods=['POST'])
    def provision():
        """
        Accept Wi-Fi credentials and save them.

        Expected JSON:
            {
                "ssid": "network-name",
                "password": "network-password",
                "csrf_token": "token"
            }

        Returns:
            JSON with success/error status
        """
        data = request.get_json() or {}

        # Verify CSRF token
        csrf_token = data.get('csrf_token')
        if not csrf_token or not verify_csrf_token(csrf_token):
            logger.warning("CSRF token verification failed for /provision")
            return jsonify({'error': 'Invalid CSRF token'}), 403

        # Server-side validation
        ssid = data.get('ssid', '').strip()
        password = data.get('password', '').strip()

        if not ssid:
            logger.warning("Provision attempt with empty SSID")
            return jsonify({'error': 'SSID is required'}), 400

        if not password:
            logger.warning(f"Provision attempt for {ssid} with empty password")
            return jsonify({'error': 'Password is required'}), 400

        if len(ssid) > 32:
            logger.warning(f"SSID too long: {len(ssid)} characters")
            return jsonify(
                {'error': 'SSID must be 32 characters or less'}), 400

        if len(password) > 63:
            logger.warning(f"Password too long: {len(password)} characters")
            return jsonify(
                {'error': 'Password must be 63 characters or less'}), 400

        if len(password) < 8:
            logger.warning(f"Password too short: {len(password)} characters")
            return jsonify(
                {'error': 'Password must be at least 8 characters'}), 400

        # Save credentials
        try:
            if not app.credential_store:
                logger.error("Credential store not configured")
                return jsonify(
                    {'error': 'Credential storage not available'}), 500

            logger.info(f"Saving credentials for SSID: {ssid}")
            success = app.credential_store.save_credentials(ssid, password)

            if success:
                logger.info(f"Credentials saved successfully for {ssid}")
                return jsonify({
                    'success': True,
                    'message': 'Wi-Fi credentials saved. Device will reconnect at next boot.'
                })
            else:
                logger.error("Failed to save credentials")
                return jsonify({'error': 'Failed to save credentials'}), 500

        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return jsonify({'error': 'Error saving credentials'}), 500

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({'status': 'ok'})

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors by serving the main UI."""
        return render_template('index.html')

    return app


if __name__ == '__main__':
    # Development mode - configure logging and create app
    logging.basicConfig(level=logging.INFO)

    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)
