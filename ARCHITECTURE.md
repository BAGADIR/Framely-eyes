# Framely-Eyes Architecture

## System Overview

Framely-Eyes is a GPU-first video analysis pipeline that processes video through multiple specialized detectors in a DAG (Directed Acyclic Graph) structure, producing a unified VAB (Video Analysis Bundle) JSON output.

## Core Components

### 1. Preparation Layer (`services/detectors/prep.py`)
- Downloads/locates video file
- Extracts metadata (resolution, fps, duration)
- Detects shot boundaries using PySceneDetect
- Extracts keyframes (configurable stride)
- Extracts audio track

### 2. Detection Pipeline

#### GPU-Heavy Detectors (Sequential)
```
YOLO Coarse → YOLO Tiled → Super-Res → YOLO Fine → SAM2 Refine
```

**YOLO Coarse** (`yolo.py`)
- Standard YOLOv8 detection at 640px input
- Detects common objects with confidence thresholds

**YOLO Tiled** (`tile_yolo.py`)
- Multi-scale detection with 512×512 tiles, 256px stride
- Covers 100% of pixels with overlap
- NMS to merge duplicate detections
- Enables tiny object detection (8×8 px minimum)

**Super-Resolution** (`superres.py`)
- Real-ESRGAN x4 upscaling for low-res videos
- Triggered when height < 1440px
- Enhances small object visibility

**SAM2 Refinement** (`sam2.py`)
- Segment Anything 2 for precise masks
- Refines bounding boxes to pixel-accurate masks
- Can be disabled via OOM fallback

#### Parallel CPU Detectors
```
Faces + OCR + Color + Motion + Audio (run simultaneously)
```

**Faces** (`faces.py`)
- InsightFace detection + tracking
- EmoNet emotion classification
- Face embedding for identity

**OCR + Fonts** (`ocr_fonts.py`)
- PaddleOCR for text detection
- DeepFont for font classification
- Stroke/shadow contrast analysis

**Color & Composition** (`color_comp.py`)
- K-means dominant color extraction
- Brightness, contrast, saturation metrics
- Rule of thirds composition analysis

**Motion & Saliency** (`motion_saliency.py`)
- Optical flow for camera motion
- Motion type classification (pan, tilt, static)
- Spectral residual saliency maps

**Audio Engineering** (`audio_eng.py`)
- LUFS loudness (target: -14.0)
- True peak (limit: -1.0 dBTP)
- Dynamic range
- STOI speech intelligibility
- Speech/music detection
- Stereo phase analysis

**Transitions** (`transitions.py`)
- SSIM similarity between shots
- Transition type detection (cut, fade, dissolve)

### 3. Vision-Language Reasoning (`services/qwen/`)

**Qwen-VL Client** (`vl_client.py`)
- Connects to vLLM-served Qwen-VL model
- JSON-strict prompting for structured output
- Shot-level: summary, mood, intent, composition
- Scene-level: narrative function, tone, motifs

**Prompts** (`prompts.py`)
- System prompts enforce JSON-only responses
- User prompts include detector outputs
- Sample up to 12 frames per shot for context

### 4. Orchestrator (`services/orchestrator/`)

**GPU Pool** (`gpu_pool.py`)
- Semaphore-based GPU resource allocation
- Configurable concurrency (default: 2)
- Prevents GPU oversubscription

**DAG Execution** (`orchestrator.py`)
- Executes detectors in dependency order
- Parallel execution where possible
- OOM safety with automatic fallback ladder:
  1. Disable SAM2
  2. Disable Super-Resolution
  3. Reduce Qwen context frames

**OOM Recovery Flow**
```python
try:
    run_detector()
except CUDA_OOM:
    apply_fallback()
    retry_once()
```

### 5. Merge & Assembly (`services/utils/merge.py`)

**Scene Building**
- Groups shots by visual similarity
- Aggregates shot-level features
- Computes scene-level statistics

**VAB Assembly**
- Combines all detector outputs
- Adds provenance for each tool
- Includes calibration metrics (TPR/FPR)
- Computes coverage metrics

### 6. Coverage System (`services/utils/coverage.py`)

**Spatial Coverage**
- Tile overlap guarantees 100% pixel coverage
- Min detectable size: 8×8 pixels

**Temporal Coverage**
- Frame stride = 1 (every frame)
- Validates 99%+ frames analyzed

**Audio Coverage**
- 100% LUFS trace
- 90%+ STOI for speech segments

**Quality Gates**
- `state: "ok"` if all thresholds met
- `state: "degraded"` if coverage drops
- `state: "failed"` if critical failure

### 7. API Layer (`services/api/`)

**FastAPI Application** (`api.py`)
- RESTful API with async handlers
- CORS enabled for web clients
- Auto-generated OpenAPI docs

**Routes** (`router.py`)
- `POST /analyze` - Start analysis job
- `POST /ingest` - Upload video file
- `GET /status/{video_id}` - Check job status
- `GET /result/{video_id}` - Get VAB JSON
- `GET /health` - System health check

**Job Queue**
- Redis-backed job state
- Background async task execution
- Progress tracking

### 8. Observability (`services/observability/`)

**Metrics** (`metrics.py`)
- Latency tracking per detector
- VRAM peak usage monitoring
- OOM trip counter
- Retry counter

### 9. QA & Testing (`services/qa/`)

**Golden Tests** (`golden_tests.py`)
- Synthetic video generation
- Tiny object recall validation
- Audio coverage validation
- Temporal coverage validation

## Data Flow

```
1. User Request
   ↓
2. API (FastAPI)
   ↓
3. Job Queue (Redis)
   ↓
4. Orchestrator
   ↓
5. Prep (video decode, shot detection)
   ↓
6. Detector DAG (parallel + sequential)
   ↓
7. Qwen-VL Reasoning
   ↓
8. Merge & Assembly
   ↓
9. Coverage Validation
   ↓
10. VAB Storage
   ↓
11. API Response
```

## Configuration System

**limits.yaml**
- Detection parameters (tile size, thresholds)
- Audio engineering targets
- Coverage thresholds
- Runtime settings (GPU semaphore, OOM fallbacks)
- Ablation flags

**model_paths.yaml**
- Model checkpoints and versions
- Used for provenance tracking

**settings.env**
- Environment-specific config
- API settings, paths, security

## Key Design Decisions

### 1. Two-Pass Detection
Coarse pass identifies regions → Super-res upscales → Fine pass on enhanced regions
**Rationale:** Balance between speed and tiny object recall

### 2. Tiled Processing
512×512 tiles with 256px stride
**Rationale:** Guarantees spatial coverage, handles arbitrary resolutions

### 3. GPU Pooling
Semaphore limits concurrent GPU tasks
**Rationale:** Prevents OOM, enables controlled parallelism

### 4. OOM Fallback Ladder
Progressive degradation instead of failure
**Rationale:** Graceful degradation for resource-constrained scenarios

### 5. Strict JSON Output
Force LLM to output parseable JSON
**Rationale:** Downstream systems need structured data, not prose

### 6. Provenance Tracking
Every detector logs tool/version/params
**Rationale:** Scientific reproducibility, debugging, auditing

### 7. Coverage Guarantees
Validate 100% frame/pixel/audio coverage
**Rationale:** "No frame left behind" philosophy for production systems

## Scaling Considerations

**Horizontal Scaling**
- Stateless API servers
- Redis job queue supports multiple workers
- Each job is independent

**Vertical Scaling**
- GPU semaphore adjusts concurrency
- Multi-GPU support via CUDA_VISIBLE_DEVICES
- Memory-aware fallbacks

**Performance**
- ~1-2 minutes per minute of 1080p video (GPU-dependent)
- Parallel shot processing
- Detector caching (models loaded once)

## Security

- File size limits (configurable)
- MIME type whitelist
- Input validation on all endpoints
- No arbitrary code execution
- SHA256 checksums for provenance

## Future Enhancements

1. **Tracking**: ByteTrack for object persistence across shots
2. **Speech Diarization**: Speaker identification with pyannote
3. **3D Scene Reconstruction**: Depth estimation for spatial understanding
4. **Real-time Mode**: Streaming analysis for live video
5. **Distributed GPU**: Multi-node GPU cluster support
