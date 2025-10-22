"""Detectors package exports.

This makes submodules available via:
    from services.detectors import tracker, yolo, sam2, ...
"""

# Re-export commonly used detector submodules
from . import (
    yolo,
    tile_yolo,
    tracker,
    sam2,
    optical_flow,
    faces,
    ocr_fonts,
    color_comp,
    transitions,
    superres,
    audio_eng,
    motion_saliency,
    prep,
)

__all__ = [
    "yolo",
    "tile_yolo",
    "tracker",
    "sam2",
    "optical_flow",
    "faces",
    "ocr_fonts",
    "color_comp",
    "transitions",
    "superres",
    "audio_eng",
    "motion_saliency",
    "prep",
]

