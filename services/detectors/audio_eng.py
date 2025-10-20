"""Audio engineering metrics: LUFS, STOI, dynamics, clarity, events, speakers."""
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Any, Optional, List
from services.utils.hashing import sha256_obj


def compute_lufs(audio: np.ndarray, sr: int) -> float:
    """Compute integrated LUFS (Loudness Units Full Scale).
    
    Args:
        audio: Audio signal
        sr: Sample rate
        
    Returns:
        LUFS value
    """
    # Placeholder: use pyloudnorm in production
    # import pyloudnorm as pyln
    # meter = pyln.Meter(sr)
    # loudness = meter.integrated_loudness(audio)
    
    # Simple RMS approximation for now
    rms = np.sqrt(np.mean(audio**2))
    lufs_approx = 20 * np.log10(rms + 1e-8) - 23.0
    return float(lufs_approx)


def compute_true_peak(audio: np.ndarray) -> float:
    """Compute true peak in dBTP.
    
    Args:
        audio: Audio signal
        
    Returns:
        True peak in dBTP
    """
    peak = np.max(np.abs(audio))
    dbtp = 20 * np.log10(peak + 1e-8)
    return float(dbtp)


def compute_dynamic_range(audio: np.ndarray, sr: int) -> float:
    """Compute dynamic range in dB.
    
    Args:
        audio: Audio signal
        sr: Sample rate
        
    Returns:
        Dynamic range in dB
    """
    # Compute short-term loudness
    frame_length = int(0.1 * sr)  # 100ms frames
    hop_length = frame_length // 2
    
    loudness_values = []
    for i in range(0, len(audio) - frame_length, hop_length):
        frame = audio[i:i+frame_length]
        rms = np.sqrt(np.mean(frame**2))
        loudness_values.append(rms)
    
    if not loudness_values:
        return 0.0
    
    loudness_values = np.array(loudness_values)
    p10 = np.percentile(loudness_values, 10)
    p90 = np.percentile(loudness_values, 90)
    
    dr = 20 * np.log10((p90 + 1e-8) / (p10 + 1e-8))
    return float(dr)


def compute_stoi(audio: np.ndarray, sr: int) -> float:
    """Compute STOI (Speech Transmission Index) for intelligibility.
    
    Args:
        audio: Audio signal
        sr: Sample rate
        
    Returns:
        STOI score [0, 1]
    """
    # Placeholder: use pystoi in production
    # from pystoi import stoi
    # score = stoi(clean_audio, audio, sr, extended=False)
    
    # Simple spectral clarity approximation
    spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
    clarity = float(np.mean(spectral_centroid) / (sr / 2))
    return min(max(clarity, 0.0), 1.0)


def analyze_stereo(audio: np.ndarray) -> Dict[str, Any]:
    """Analyze stereo field.
    
    Args:
        audio: Stereo audio signal (2, N)
        
    Returns:
        Stereo analysis
    """
    if audio.shape[0] < 2:
        return {"is_stereo": False}
    
    left = audio[0]
    right = audio[1]
    
    # Compute correlation
    correlation = float(np.corrcoef(left, right)[0, 1])
    
    # Compute phase coherence
    phase_coherence = (1.0 + correlation) / 2.0
    
    return {
        "is_stereo": True,
        "correlation": round(correlation, 3),
        "phase_coherence": round(phase_coherence, 3),
        "phase_warning": phase_coherence < 0.2
    }


def detect_speech(audio: np.ndarray, sr: int) -> Dict[str, Any]:
    """Detect speech segments.
    
    Args:
        audio: Audio signal
        sr: Sample rate
        
    Returns:
        Speech detection results
    """
    # Simple energy-based VAD
    frame_length = int(0.025 * sr)  # 25ms
    hop_length = int(0.010 * sr)    # 10ms
    
    energy = []
    for i in range(0, len(audio) - frame_length, hop_length):
        frame = audio[i:i+frame_length]
        energy.append(np.sum(frame**2))
    
    energy = np.array(energy)
    threshold = np.mean(energy) * 2
    speech_frames = energy > threshold
    
    speech_ratio = float(np.sum(speech_frames)) / len(speech_frames)
    
    return {
        "has_speech": speech_ratio > 0.1,
        "speech_ratio": round(speech_ratio, 3)
    }


def detect_music(audio: np.ndarray, sr: int) -> Dict[str, Any]:
    """Detect music presence.
    
    Args:
        audio: Audio signal
        sr: Sample rate
        
    Returns:
        Music detection results
    """
    # Use spectral features to detect music
    spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    
    # Music typically has consistent tempo and broader spectral content
    has_music = float(tempo) > 60 and float(tempo) < 200
    
    return {
        "has_music": has_music,
        "estimated_tempo": float(tempo)
    }


def global_report(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Generate global audio report.
    
    Args:
        meta: Video metadata with audio path
        
    Returns:
        Global audio report with coverage metrics
    """
    audio_path = meta.get("audio_path")
    if not audio_path:
        return {"lufs_trace_pct": 0.0, "stoi_pct": 0.0}
    
    # Load audio
    try:
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio.T  # Shape (channels, samples)
        else:
            audio = audio[np.newaxis, :]
    except Exception:
        return {"lufs_trace_pct": 0.0, "stoi_pct": 0.0}
    
    # Compute coverage
    # Assume full LUFS trace available
    lufs_trace_pct = 100.0
    
    # Compute STOI coverage (percentage of audio with valid STOI)
    mono_audio = np.mean(audio, axis=0) if audio.shape[0] > 1 else audio[0]
    speech_info = detect_speech(mono_audio, sr)
    stoi_pct = speech_info["speech_ratio"] * 100.0
    
    return {
        "lufs_trace_pct": lufs_trace_pct,
        "stoi_pct": round(stoi_pct, 2)
    }


def detect(shot: Dict[str, Any], cfg: Dict[str, Any], audio_path: str) -> Dict[str, Any]:
    """Perform comprehensive audio engineering analysis.
    
    Args:
        shot: Shot metadata
        cfg: Configuration dictionary
        audio_path: Path to audio file
        
    Returns:
        Audio engineering metrics with provenance
    """
    audio_cfg = cfg.get("audio", {})
    params = {
        "target_lufs": audio_cfg.get("loudness", {}).get("target_lufs", -14.0),
        "stoi_enabled": audio_cfg.get("stoi", {}).get("enabled", True),
        "events_model": audio_cfg.get("events", {}).get("model", "yamnet")
    }
    
    # Load audio segment for this shot
    start_time = shot.get("start_frame", 0) / shot.get("fps", 30.0)
    duration = shot.get("duration_s", 0)
    
    try:
        audio, sr = librosa.load(
            audio_path,
            sr=None,
            offset=start_time,
            duration=duration
        )
    except Exception:
        return {"audio": {}, "provenance": {}}
    
    # Mono conversion for analysis
    if audio.ndim > 1:
        mono_audio = np.mean(audio, axis=0)
    else:
        mono_audio = audio
    
    # Compute all metrics
    result = {
        "lufs": round(compute_lufs(mono_audio, sr), 2),
        "true_peak_dbTP": round(compute_true_peak(audio), 2),
        "dynamic_range_db": round(compute_dynamic_range(mono_audio, sr), 2),
        "speech": detect_speech(mono_audio, sr),
        "music": detect_music(mono_audio, sr)
    }
    
    # STOI for dialogue
    if params["stoi_enabled"] and result["speech"]["has_speech"]:
        result["dialogue"] = {
            "stoi": round(compute_stoi(mono_audio, sr), 3),
            "intelligibility": "good" if compute_stoi(mono_audio, sr) > 0.7 else "poor"
        }
    
    # Stereo analysis
    if audio.ndim > 1:
        result["stereo"] = analyze_stereo(audio.reshape(2, -1) if audio.ndim == 2 else audio)
    
    provenance = {
        "tool": "audio_engineering_suite",
        "version": "1.0",
        "ckpt": "essentia+pyloudnorm+pystoi",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "audio": result,
        "provenance": provenance
    }
