"""
Frame capture display adapter for testing and diagnostics.
Saves rendered frames to disk instead of displaying on hardware.
Useful for: CI/CD testing, debugging, verification without LED matrices.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from weatherbox.display.adapter import DisplayAdapter, Bitmap

logger = logging.getLogger(__name__)


class FrameCaptureAdapter(DisplayAdapter):
    """
    Display adapter that captures frames to disk for inspection.
    Each render operation saves current frame state to a timestamped file.
    """

    def __init__(
            self,
            matrix_count: int = 4,
            capture_dir: str = "/tmp/weatherbox_frames"):
        """
        Initialize frame capture adapter.

        Args:
            matrix_count: Number of matrices
            capture_dir: Directory to save captured frames
        """
        self.matrix_count = matrix_count
        self.capture_dir = Path(capture_dir)
        self.matrices: List[Bitmap] = [Bitmap() for _ in range(matrix_count)]
        self._initialized = False
        self._brightness = 200
        self._render_count = 0

    def initialize(self) -> bool:
        """Initialize capture directory."""
        try:
            self.capture_dir.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            logger.info(f"Frame capture initialized: {self.capture_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize frame capture: {e}")
            return False

    def render_frame(self, matrix_index: int, bitmap: Bitmap) -> bool:
        """
        Render single frame to disk.

        Args:
            matrix_index: Matrix index
            bitmap: Bitmap to capture

        Returns:
            True if capture successful
        """
        if 0 <= matrix_index < self.matrix_count:
            self.matrices[matrix_index] = bitmap
            self._render_count += 1
            self._save_frame()
            return True
        return False

    def render_all(self, bitmaps: List[Bitmap]) -> bool:
        """
        Render all matrices to disk.

        Args:
            bitmaps: List of bitmaps

        Returns:
            True if capture successful
        """
        if len(bitmaps) == self.matrix_count:
            self.matrices = bitmaps
            self._render_count += 1
            self._save_frame()
            return True
        return False

    def clear_all(self) -> bool:
        """Clear all matrices."""
        self.matrices = [Bitmap() for _ in range(self.matrix_count)]
        self._save_frame()
        return True

    def shutdown(self) -> bool:
        """Shutdown capture."""
        self._initialized = False
        logger.info(
            f"Frame capture shutdown. Total renders: {
                self._render_count}")
        return True

    def get_brightness(self) -> int:
        """Get brightness."""
        return self._brightness

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness."""
        if 0 <= brightness <= 255:
            self._brightness = brightness
            return True
        return False

    def is_initialized(self) -> bool:
        """Check initialization."""
        return self._initialized

    def _save_frame(self) -> None:
        """Save current frame state to JSON."""
        try:
            timestamp = datetime.now().isoformat()
            frame_data = {
                'timestamp': timestamp,
                'render_count': self._render_count,
                'brightness': self._brightness,
                'matrices': [
                    {
                        'index': i,
                        'bitmap': bm.data,
                        'pixel_count': sum(1 for v in bm.data if v > 0)
                    }
                    for i, bm in enumerate(self.matrices)
                ]
            }

            filename = self.capture_dir / \
                f"frame_{self._render_count:06d}.json"
            with open(filename, 'w') as f:
                json.dump(frame_data, f, indent=2)

            logger.debug(f"Frame captured: {filename.name}")
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")

    def get_captured_frames(self) -> List[Path]:
        """Get list of all captured frame files."""
        return sorted(self.capture_dir.glob("frame_*.json"))

    def load_frame(self, frame_file: Path) -> Optional[dict]:
        """Load a captured frame for inspection."""
        try:
            with open(frame_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load frame {frame_file}: {e}")
            return None
