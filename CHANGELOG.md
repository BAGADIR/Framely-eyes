# Changelog

All notable changes to Framely-Eyes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-20

### Added
- 🎉 Initial release of Framely-Eyes Video Perception OS
- GPU-first video analysis pipeline with DAG orchestration
- Multi-scale object detection with YOLOv8 (coarse + tiled)
- Tiny object detection (8×8 pixels minimum)
- Real-ESRGAN super-resolution integration
- SAM2 mask refinement for precise segmentation
- InsightFace + EmoNet for face detection and emotion recognition
- PaddleOCR + DeepFont for text and font detection
- Comprehensive audio engineering metrics (LUFS, STOI, dynamics)
- Color and composition analysis
- Motion detection and saliency mapping
- Qwen-VL-2.5 vision-language reasoning
- Scene and shot boundary detection
- Complete coverage tracking (spatial, temporal, audio)
- Quality gates with automatic degradation handling
- OOM safety with fallback ladder
- GPU resource pooling with semaphore
- Provenance tracking for all detectors
- Calibration metrics (TPR/FPR) for each detector family
- Risk detection (low intelligibility, clipping, overlaps)
- FastAPI REST API with async job processing
- Redis-backed job queue
- Docker Compose setup with GPU support
- Comprehensive documentation (README, ARCHITECTURE, QUICKSTART, CONTRIBUTING)
- Golden tests for validation
- Smoke test script
- Observability with metrics collection

### Detector Coverage
- **Objects**: YOLOv8 multi-scale (100% spatial coverage)
- **Faces**: InsightFace detection + EmoNet emotions
- **Text**: PaddleOCR + font classification
- **Color**: Dominant colors, brightness, saturation, contrast
- **Motion**: Optical flow + saliency maps
- **Audio**: LUFS, true peak, STOI, dynamics, speech/music detection
- **Transitions**: SSIM-based cut/fade/dissolve detection
- **Reasoning**: Qwen-VL shot and scene analysis

### API Endpoints
- `POST /analyze` - Start video analysis job
- `POST /ingest` - Upload video file
- `GET /status/{video_id}` - Get job status
- `GET /result/{video_id}` - Get VAB JSON
- `GET /health` - Health check

### Configuration
- `configs/limits.yaml` - Detection parameters and thresholds
- `configs/model_paths.yaml` - Model checkpoints and versions
- `configs/settings.example.env` - Environment configuration

### Quality Guarantees
- 100% spatial coverage (tiled detection)
- 100% temporal coverage (frame_stride=1)
- 100% LUFS audio trace
- ≥90% STOI coverage for speech
- 8×8 pixel minimum detectable object size

### Performance
- GPU-accelerated parallel processing
- Configurable concurrency (GPU semaphore)
- OOM-safe with automatic fallback
- ~1-2 minutes per minute of 1080p video (GPU-dependent)

### Security
- File size limits (1000 MB default)
- MIME type whitelist
- Input validation
- SHA256 checksums for provenance

[1.0.0]: https://github.com/yourorg/framely-eyes/releases/tag/v1.0.0
