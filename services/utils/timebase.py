"""Time utilities for video analysis."""
from typing import Tuple


def frame_to_timecode(frame: int, fps: float) -> str:
    """Convert frame number to timecode string.
    
    Args:
        frame: Frame number (0-indexed)
        fps: Frames per second
        
    Returns:
        Timecode string in format HH:MM:SS.mmm
    """
    seconds = frame / fps
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def timecode_to_frame(timecode: str, fps: float) -> int:
    """Convert timecode string to frame number.
    
    Args:
        timecode: Timecode string in format HH:MM:SS.mmm or MM:SS.mmm
        fps: Frames per second
        
    Returns:
        Frame number (0-indexed)
    """
    parts = timecode.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        hours = 0
        minutes, seconds = parts
    
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return int(total_seconds * fps)


def seconds_to_timecode(seconds: float) -> str:
    """Convert seconds to timecode string.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Timecode string in format HH:MM:SS.mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def frame_range_to_time_range(
    start_frame: int,
    end_frame: int,
    fps: float
) -> Tuple[str, str]:
    """Convert frame range to time range.
    
    Args:
        start_frame: Start frame number
        end_frame: End frame number
        fps: Frames per second
        
    Returns:
        Tuple of (start_timecode, end_timecode)
    """
    return (
        frame_to_timecode(start_frame, fps),
        frame_to_timecode(end_frame, fps)
    )
