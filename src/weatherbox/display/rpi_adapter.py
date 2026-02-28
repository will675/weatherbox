"""
Raspberry Pi GPIO adapter for rpi-rgb-led-matrix 8×8 matrix displays.
Provides hardware-specific implementation of DisplayAdapter for real LED matrices.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RGBMatrix:
    """Wrapper for rpi-rgb-led-matrix library instance (lazy-loaded)."""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get or create rgbmatrix instance (lazy loading)."""
        if cls._instance is None:
            try:
                from rgbmatrix import RGBMatrix as _RGBMatrix
                cls._instance = _RGBMatrix
            except ImportError:
                logger.warning("rgbmatrix library not available; using mock mode")
                cls._instance = None
        return cls._instance


class RpiAdapter:
    """
    Hardware adapter for Raspberry Pi GPIO-connected LED matrices.
    
    Implements DisplayAdapter interface using rpi-rgb-led-matrix library.
    Supports 4 chained 8×8 matrices (or configurable layout).
    """
    
    # Matrix layout configuration
    DEFAULT_COLS = 32           # 4 matrices × 8 pixels wide
    DEFAULT_ROWS = 8
    DEFAULT_MATRIX_COUNT = 4
    
    # GPIO pin configuration (for RPi Hat)
    DEFAULT_CONFIG = {
        'gpio_slowdown': 4,
        'brightness': 100,
        'saturation': 255,
    }
    
    def __init__(
        self,
        rows: int = DEFAULT_ROWS,
        cols: int = DEFAULT_COLS,
        matrix_count: int = DEFAULT_MATRIX_COUNT,
        brightness: int = 100,
        gpio_slowdown: int = 4,
    ):
        """
        Initialize RPi matrix adapter.
        
        Args:
            rows: Matrix height in pixels (typically 8)
            cols: Matrix width in pixels (8 × number of matrices)
            matrix_count: Number of chained matrices (typically 4)
            brightness: Initial brightness (0-255)
            gpio_slowdown: GPIO speed factor for timing (higher = slower, safer)
        """
        self.rows = rows
        self.cols = cols
        self.matrix_count = matrix_count
        self.brightness_value = brightness
        self.gpio_slowdown = gpio_slowdown
        self.matrix = None
        self._initialized = False
        self._is_mock_mode = False
    
    def initialize(self) -> bool:
        """
        Initialize hardware connection to LED matrices.
        
        Returns:
            True if successful, False if hardware unavailable
        """
        try:
            rgbmatrix_class = RGBMatrix.get_instance()
            
            if rgbmatrix_class is None:
                logger.warning("rpi-rgb-led-matrix not installed; using mock mode")
                self._is_mock_mode = True
                self._initialized = True
                return False
            
            # Create matrix with configuration
            options = rgbmatrix_class.Options()
            options.rows = self.rows
            options.cols = self.cols
            options.gpio_slowdown = self.gpio_slowdown
            options.brightness = self.brightness_value
            options.drop_privileges = False  # For systemd service
            
            self.matrix = rgbmatrix_class(options)
            
            logger.info(
                f"Initialized RPi LED matrix: {self.cols}x{self.rows} "
                f"({self.matrix_count} chained) at brightness {self.brightness_value}"
            )
            self._initialized = True
            return True
        
        except ImportError as e:
            logger.warning(f"rpi-rgb-led-matrix import failed: {e}")
            self._is_mock_mode = True
            self._initialized = True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize RPi matrix: {e}")
            self._initialized = False
            return False
    
    def render_frame(self, matrix_index: int, bitmap: 'Bitmap') -> bool:
        """
        Render single 8×8 bitmap to a specific matrix.
        
        Args:
            matrix_index: Matrix position (0-3 for 4-matrix display)
            bitmap: 8×8 bitmap with pixel values
        
        Returns:
            True if successful
        """
        if not self._initialized:
            logger.error("Matrix not initialized; call initialize() first")
            return False
        
        if self._is_mock_mode:
            logger.debug(f"Mock mode: render_frame(matrix_index={matrix_index})")
            return True
        
        try:
            if matrix_index < 0 or matrix_index >= self.matrix_count:
                logger.error(f"Invalid matrix index: {matrix_index}")
                return False
            
            # Calculate column offset for this matrix
            col_offset = matrix_index * 8
            
            # Write bitmap pixels to matrix
            for y in range(8):
                for x in range(8):
                    pixel_value = bitmap.get_pixel(x, y)
                    col = col_offset + x
                    
                    # Convert grayscale to RGB (simple approach: all channels same)
                    # For more control, modify this to use RGB values from bitmap
                    if self.matrix:
                        self.matrix.SetPixel(col, y, pixel_value, pixel_value, pixel_value)
            
            return True
        
        except Exception as e:
            logger.error(f"Error rendering frame to matrix {matrix_index}: {e}")
            return False
    
    def render_all(self, bitmaps: List['Bitmap']) -> bool:
        """
        Render all matrices atomically.
        
        Args:
            bitmaps: List of 8×8 bitmaps (one per matrix)
        
        Returns:
            True if successful
        """
        if not self._initialized:
            logger.error("Matrix not initialized")
            return False
        
        if len(bitmaps) > self.matrix_count:
            logger.error(f"Too many bitmaps: {len(bitmaps)} > {self.matrix_count}")
            return False
        
        try:
            for i, bitmap in enumerate(bitmaps):
                if not self.render_frame(i, bitmap):
                    logger.error(f"Failed to render matrix {i}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error rendering all matrices: {e}")
            return False
    
    def clear_all(self) -> bool:
        """
        Clear all pixels on all matrices.
        
        Returns:
            True if successful
        """
        if not self._initialized:
            logger.error("Matrix not initialized")
            return False
        
        try:
            if self._is_mock_mode:
                logger.debug("Mock mode: clear_all()")
                return True
            
            if self.matrix:
                self.matrix.Clear()
            
            return True
        
        except Exception as e:
            logger.error(f"Error clearing matrices: {e}")
            return False
    
    def shutdown(self) -> None:
        """
        Release hardware resources and turn off displays.
        """
        try:
            if self.matrix:
                self.matrix.Clear()
                # Matrix cleanup is handled by destructor
            
            self._initialized = False
            logger.info("RPi matrix adapter shut down")
        
        except Exception as e:
            logger.error(f"Error shutting down matrix: {e}")
    
    def set_brightness(self, brightness: int) -> bool:
        """
        Set global brightness for all matrices.
        
        Args:
            brightness: Brightness level (0-255)
        
        Returns:
            True if successful
        """
        if brightness < 0 or brightness > 255:
            logger.error(f"Invalid brightness: {brightness}")
            return False
        
        try:
            self.brightness_value = brightness
            
            if self._is_mock_mode:
                logger.debug(f"Mock mode: set_brightness({brightness})")
                return True
            
            if self.matrix:
                self.matrix.brightness = brightness
            
            logger.debug(f"Brightness set to {brightness}")
            return True
        
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            return False
    
    def get_brightness(self) -> int:
        """Get current brightness level."""
        return self.brightness_value
    
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._initialized
    
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode (library not available)."""
        return self._is_mock_mode


# For compatibility with DisplayAdapter interface
class Bitmap:
    """8×8 bitmap for use with RpiAdapter."""
    
    def __init__(self):
        """Initialize 8×8 bitmap with all pixels off."""
        self.pixels = [[0] * 8 for _ in range(8)]
    
    def set_pixel(self, x: int, y: int, value: int) -> None:
        """Set pixel brightness."""
        if 0 <= x < 8 and 0 <= y < 8:
            self.pixels[y][x] = max(0, min(255, value))
    
    def get_pixel(self, x: int, y: int) -> int:
        """Get pixel brightness."""
        if 0 <= x < 8 and 0 <= y < 8:
            return self.pixels[y][x]
        return 0
    
    def clear(self) -> None:
        """Clear all pixels."""
        self.pixels = [[0] * 8 for _ in range(8)]
