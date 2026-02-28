"""
Icon manager for loading and mapping weather types to LED matrix icon IDs.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@staticmethod
def load_icon_mapping(config_path: str = "config/icons.yaml") -> Dict[str, int]:
    """
    Load icon mapping from YAML configuration.
    
    Expected YAML structure:
    ```yaml
    # Fallback icon used for unmapped weather types
    fallback: 0
    
    mappings:
      "Clear": 1
      "Partly cloudy": 2
      "Overcast": 3
      "Light rain": 5
      etc.
    ```
    
    Args:
        config_path: Path to icons.yaml configuration file
    
    Returns:
        Dictionary mapping weather type strings to icon bitmap IDs
    
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If YAML parsing fails
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Icon config not found: {config_path}")
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            raise ValueError("Icon config must be YAML dict")
        
        mappings = config.get('mappings', {})
        
        if not isinstance(mappings, dict):
            raise ValueError("Icon mappings must be dict")
        
        logger.info(f"Loaded {len(mappings)} icon mappings from {config_path}")
        return mappings
    
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse icon config: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading icon config: {e}")
        raise


class IconLoader:
    """
    Manages icon mapping and fallback logic for weather forecast display.
    """
    
    def __init__(
        self,
        config_path: str = "config/icons.yaml",
        fallback_icon_id: int = 0
    ):
        """
        Initialize icon loader.
        
        Args:
            config_path: Path to icons.yaml configuration
            fallback_icon_id: Icon ID to use for unmapped weather types
        """
        self.config_path = config_path
        self.fallback_icon_id = fallback_icon_id
        self.mappings = {}
        self.load_mapping()
    
    def load_mapping(self) -> None:
        """Load icon mapping from configuration file."""
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                logger.warning(f"Icon config not found: {self.config_path}, using fallback")
                return
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                logger.warning("Icon config is not a dict, using fallback")
                return
            
            # Extract fallback icon ID if specified
            if 'fallback' in config:
                try:
                    self.fallback_icon_id = int(config['fallback'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid fallback icon ID: {config.get('fallback')}")
            
            # Load mappings
            mappings = config.get('mappings', {})
            if isinstance(mappings, dict):
                self.mappings = mappings
                logger.info(f"Loaded {len(self.mappings)} icon mappings")
            else:
                logger.warning("Icon mappings is not a dict")
        
        except Exception as e:
            logger.error(f"Error loading icon config: {e}")
    
    def get_icon_id(self, weather_type: str) -> int:
        """
        Map weather type to icon ID.
        
        Args:
            weather_type: Weather type string (e.g., "Partly cloudy", "Heavy rain")
        
        Returns:
            Icon bitmap ID (uses fallback if type not found)
        """
        # Exact match
        if weather_type in self.mappings:
            icon_id = self.mappings[weather_type]
            logger.debug(f"Mapped weather type '{weather_type}' to icon {icon_id}")
            return icon_id
        
        # Try substring match (case-insensitive)
        weather_lower = weather_type.lower()
        for mapped_type, icon_id in self.mappings.items():
            if mapped_type.lower() == weather_lower:
                logger.debug(f"Mapped weather type '{weather_type}' to icon {icon_id} (case-insensitive)")
                return icon_id
        
        # Use fallback for unmapped type
        logger.warning(f"Weather type '{weather_type}' not mapped; using fallback icon {self.fallback_icon_id}")
        return self.fallback_icon_id
    
    def is_mapped(self, weather_type: str) -> bool:
        """Check if weather type has a mapping."""
        if weather_type in self.mappings:
            return True
        
        weather_lower = weather_type.lower()
        for mapped_type in self.mappings.keys():
            if mapped_type.lower() == weather_lower:
                return True
        
        return False
    
    def get_unmapped_types(self, weather_types: list) -> list:
        """Get list of weather types that are not mapped."""
        unmapped = []
        for wtype in weather_types:
            if not self.is_mapped(wtype):
                unmapped.append(wtype)
        return unmapped
    
    def reload_mapping(self) -> None:
        """Reload icon mapping from configuration file."""
        logger.info(f"Reloading icon mapping from {self.config_path}")
        self.mappings = {}
        self.load_mapping()
