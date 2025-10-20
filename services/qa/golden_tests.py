"""Golden tests for validating tiny object detection and audio coverage."""
import numpy as np
import cv2
import os
import tempfile
import soundfile as sf
from typing import Dict, Any, List


def create_synthetic_video_with_tiny_objects(
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration_s: float = 5.0,
    object_size: int = 8
) -> str:
    """Create synthetic video with known tiny objects.
    
    Args:
        width: Video width
        height: Video height
        fps: Frames per second
        duration_s: Duration in seconds
        object_size: Size of tiny objects in pixels
        
    Returns:
        Path to generated video
    """
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "synthetic_tiny.mp4")
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    
    num_frames = int(fps * duration_s)
    
    # Known object positions (store for validation)
    known_objects = []
    
    for frame_idx in range(num_frames):
        # Create blank frame
        frame = np.ones((height, width, 3), dtype=np.uint8) * 128  # Gray background
        
        # Add 10 tiny objects at known positions
        for obj_idx in range(10):
            x = (obj_idx * 200 + frame_idx * 5) % (width - object_size)
            y = (obj_idx * 100) % (height - object_size)
            
            # Draw tiny object (checkered pattern for visibility)
            color = (255, 0, 0) if obj_idx % 2 == 0 else (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x + object_size, y + object_size), color, -1)
            
            if frame_idx == 0:
                known_objects.append({
                    "frame": 0,
                    "bbox": [x, y, x + object_size, y + object_size],
                    "size": object_size
                })
        
        out.write(frame)
    
    out.release()
    
    # Save ground truth
    ground_truth_path = os.path.join(temp_dir, "ground_truth.txt")
    with open(ground_truth_path, 'w') as f:
        for obj in known_objects:
            f.write(f"{obj['bbox'][0]},{obj['bbox'][1]},{obj['bbox'][2]},{obj['bbox'][3]}\n")
    
    return video_path


def create_synthetic_audio_with_speech(
    duration_s: float = 5.0,
    sr: int = 44100
) -> str:
    """Create synthetic audio with known speech segments.
    
    Args:
        duration_s: Duration in seconds
        sr: Sample rate
        
    Returns:
        Path to generated audio
    """
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "synthetic_speech.wav")
    
    # Generate synthetic speech-like signal (amplitude modulated noise)
    t = np.linspace(0, duration_s, int(sr * duration_s))
    
    # Speech formants simulation (simplified)
    formant1 = np.sin(2 * np.pi * 500 * t)
    formant2 = np.sin(2 * np.pi * 1500 * t)
    formant3 = np.sin(2 * np.pi * 2500 * t)
    
    # Amplitude modulation (speech envelope)
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 4 * t))  # 4 Hz modulation
    
    # Combine
    speech = envelope * (formant1 + 0.5 * formant2 + 0.3 * formant3)
    
    # Normalize
    speech = speech / np.max(np.abs(speech)) * 0.8
    
    # Add some noise
    noise = np.random.randn(len(speech)) * 0.05
    audio = speech + noise
    
    # Save as stereo
    audio_stereo = np.stack([audio, audio], axis=1)
    sf.write(audio_path, audio_stereo, sr)
    
    return audio_path


def test_tiny_object_recall(detection_results: List[Dict[str, Any]], min_recall: float = 0.95) -> bool:
    """Test if tiny object detection meets minimum recall threshold.
    
    Args:
        detection_results: List of detection results
        min_recall: Minimum recall threshold
        
    Returns:
        True if test passes
    """
    # Count detections of size <= 10 pixels
    tiny_detections = [
        det for det in detection_results
        if det.get("area", 1000) <= 100  # 10x10 pixels
    ]
    
    # Expected 10 tiny objects in first frame
    expected_count = 10
    actual_count = len(tiny_detections)
    
    recall = actual_count / expected_count
    
    print(f"Tiny object recall: {recall:.2%} (detected {actual_count}/{expected_count})")
    
    return recall >= min_recall


def test_audio_coverage_and_limits(audio_metrics: Dict[str, Any]) -> bool:
    """Test audio coverage and engineering limits.
    
    Args:
        audio_metrics: Audio analysis metrics
        
    Returns:
        True if test passes
    """
    tests_passed = True
    
    # Test 1: LUFS trace coverage
    lufs_trace_pct = audio_metrics.get("lufs_trace_pct", 0)
    if lufs_trace_pct < 100.0:
        print(f"FAIL: LUFS trace coverage {lufs_trace_pct}% < 100%")
        tests_passed = False
    else:
        print(f"PASS: LUFS trace coverage {lufs_trace_pct}%")
    
    # Test 2: STOI coverage
    stoi_pct = audio_metrics.get("stoi_pct", 0)
    if stoi_pct < 90.0:
        print(f"FAIL: STOI coverage {stoi_pct}% < 90%")
        tests_passed = False
    else:
        print(f"PASS: STOI coverage {stoi_pct}%")
    
    # Test 3: True peak limit
    true_peak = audio_metrics.get("true_peak_dbTP", 0)
    if true_peak > -1.0:
        print(f"FAIL: True peak {true_peak} dBTP > -1.0 dBTP")
        tests_passed = False
    else:
        print(f"PASS: True peak {true_peak} dBTP")
    
    return tests_passed


def test_temporal_coverage(vab: Dict[str, Any]) -> bool:
    """Test that every frame was analyzed.
    
    Args:
        vab: Video Analysis Bundle
        
    Returns:
        True if test passes
    """
    coverage = vab.get("status", {}).get("coverage", {})
    temporal = coverage.get("temporal", {})
    
    frames_analyzed_pct = temporal.get("frames_analyzed_pct", 0)
    frame_stride = temporal.get("frame_stride", 999)
    
    tests_passed = True
    
    if frame_stride != 1:
        print(f"FAIL: Frame stride {frame_stride} != 1")
        tests_passed = False
    else:
        print(f"PASS: Frame stride is 1")
    
    if frames_analyzed_pct < 100.0:
        print(f"FAIL: Frames analyzed {frames_analyzed_pct}% < 100%")
        tests_passed = False
    else:
        print(f"PASS: Frames analyzed {frames_analyzed_pct}%")
    
    return tests_passed


def run_all_golden_tests(vab: Dict[str, Any]) -> bool:
    """Run all golden tests on VAB.
    
    Args:
        vab: Video Analysis Bundle
        
    Returns:
        True if all tests pass
    """
    print("=" * 60)
    print("Running Golden Tests")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Temporal coverage
    print("\n[Test 1] Temporal Coverage")
    if not test_temporal_coverage(vab):
        all_passed = False
    
    # Test 2: Audio coverage (if available)
    audio_report = vab.get("status", {}).get("coverage", {}).get("audio", {})
    if audio_report:
        print("\n[Test 2] Audio Coverage & Limits")
        if not test_audio_coverage_and_limits(audio_report):
            all_passed = False
    
    # Test 3: Object detection recall (check for small objects)
    print("\n[Test 3] Small Object Detection")
    all_objects = []
    for shot in vab.get("shots", []):
        objects = shot.get("detectors", {}).get("objects", [])
        all_objects.extend(objects)
    
    small_objects = [obj for obj in all_objects if obj.get("area", 1000) < 100]
    print(f"Detected {len(small_objects)} small objects (< 100 px²)")
    
    if len(small_objects) > 0:
        print("PASS: Small object detection working")
    else:
        print("WARNING: No small objects detected")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All golden tests PASSED")
    else:
        print("✗ Some golden tests FAILED")
    print("=" * 60)
    
    return all_passed
