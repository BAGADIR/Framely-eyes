"""Lazy-export detector submodules to avoid circular imports."""

from importlib import import_module
from typing import Dict

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

_CACHE: Dict[str, object] = {}


def __getattr__(name: str):
    if name in _CACHE:
        return _CACHE[name]
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        _CACHE[name] = module
        return module
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + __all__)
