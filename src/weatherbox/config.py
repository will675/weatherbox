import os
import yaml

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'config.yaml')


def load_config(path: str | None = None) -> dict:
    cfg_path = path or os.environ.get(
        'WEATHERBOX_CONFIG') or DEFAULT_CONFIG_PATH
    cfg_path = os.path.abspath(os.path.expanduser(cfg_path))
    if not os.path.exists(cfg_path):
        return {}
    with open(cfg_path, 'r', encoding='utf-8') as fh:
        return yaml.safe_load(fh) or {}


def save_wifi_credentials(
        ssid: str,
        password: str,
        path: str | None = None) -> None:
    cfg = load_config(path)
    cfg.setdefault('wifi', {})
    cfg['wifi']['ssid'] = ssid
    cfg['wifi']['password'] = password
    cfg_path = path or os.environ.get(
        'WEATHERBOX_CONFIG') or DEFAULT_CONFIG_PATH
    cfg_path = os.path.abspath(os.path.expanduser(cfg_path))
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, 'w', encoding='utf-8') as fh:
        yaml.safe_dump(cfg, fh)
