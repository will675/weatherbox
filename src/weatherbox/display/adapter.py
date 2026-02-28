"""
Display adapter interface for abstraction over LED matrix hardware.
Allows test doubles to be injected in CI environments and enables
support for multiple hardware types (rpi-gpio, frame-capture, etc).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Bitmap:
    """Represents an 8x8 bitmap for LED display."""
    width: int = 8
    height: int = 8
    data: List[int] = None  # List of pixel values (0-255 for brightness)

    def __post_init__(self):
        """Initialize bitmap data if not provided."""
        if self.data is None:
            self.data = [0] * (self.width * self.height)

    def set_pixel(self, x: int, y: int, value: int) -> None:
        """Set pixel at (x, y) to value (0-255)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.data[y * self.width + x] = value

    def get_pixel(self, x: int, y: int) -> int:
        """Get pixel value at (x, y)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.data[y * self.width + x]
        return 0

    def clear(self) -> None:
        """Clear all pixels to 0."""
        self.data = [0] * len(self.data)

    def __repr__(self) -> str:
        return f"Bitmap(8x8, {sum(1 for v in self.data if v > 0)} pixels)"


class DisplayAdapter(ABC):
    """Abstract base class for LED matrix display implementations."""

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the display hardware.

        Returns:
            True if initialization successful, False otherwise
        """

    @abstractmethod
    def render_frame(self, matrix_index: int, bitmap: Bitmap) -> bool:
        """
        Render a single 8x8 bitmap to a specific matrix.

        Args:
            matrix_index: 0-based index of matrix (0=leftmost)
            bitmap: Bitmap object to display

        Returns:
            True if render successful, False otherwise
        """

    @abstractmethod
    def render_all(self, bitmaps: List[Bitmap]) -> bool:
        """
        Render multiple bitmaps to all matrices at once.

        Args:
            bitmaps: List of Bitmap objects (one per matrix)

        Returns:
            True if render successful, False otherwise
        """

    @abstractmethod
    def clear_all(self) -> bool:
        """
        Clear all matrices (turn off all pixels).

        Returns:
            True if clear successful, False otherwise
        """

    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shutdown display and release hardware resources.

        Returns:
            True if shutdown successful, False otherwise
        """

    @abstractmethod
    def get_brightness(self) -> int:
        """
        Get current global brightness setting (0-255).

        Returns:
            Brightness value
        """

    @abstractmethod
    def set_brightness(self, brightness: int) -> bool:
        """
        Set global brightness for all matrices.

        Args:
            brightness: Value 0-255

        Returns:
            True if set successful, False otherwise
        """

    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if display is initialized and ready."""


class MockDisplayAdapter(DisplayAdapter):
    """Mock adapter for testing without hardware."""

    def __init__(self, matrix_count: int = 4):
        """Initialize mock adapter."""
        self.matrix_count = matrix_count
        self.matrices: List[Bitmap] = [Bitmap() for _ in range(matrix_count)]
        self._initialized = False
        self._brightness = 200

    def initialize(self) -> bool:
        """Initialize (no-op for mock)."""
        self._initialized = True
        return True

    def render_frame(self, matrix_index: int, bitmap: Bitmap) -> bool:
        """Store bitmap in memory."""
        if 0 <= matrix_index < self.matrix_count:
            self.matrices[matrix_index] = bitmap
            return True
        return False

    def render_all(self, bitmaps: List[Bitmap]) -> bool:
        """Store all bitmaps."""
        if len(bitmaps) == self.matrix_count:
            self.matrices = bitmaps
            return True
        return False

    def clear_all(self) -> bool:
        """Clear all matrices."""
        self.matrices = [Bitmap() for _ in range(self.matrix_count)]
        return True

    def shutdown(self) -> bool:
        """Shutdown (no-op for mock)."""
        self._initialized = False
        return True

    def get_brightness(self) -> int:
        """Return current brightness."""
        return self._brightness

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        if 0 <= brightness <= 255:
            self._brightness = brightness
            return True
        return False

    def is_initialized(self) -> bool:
        """Check initialization status."""
        return self._initialized

    def get_frame(self, matrix_index: int) -> Optional[Bitmap]:
        """Get currently rendered frame (for testing)."""
        if 0 <= matrix_index < self.matrix_count:
            return self.matrices[matrix_index]
        return None
