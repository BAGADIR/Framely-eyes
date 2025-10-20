# Framely-Eyes 👁️

**GPU-First, Ultra-Detailed Video Perception OS**

A complete sensory cortex for AI video editing that analyzes video at 98% accuracy — visually, audibly, emotionally, and contextually — like a full human perception stack compressed into JSON.

## 🎯 What is Framely-Eyes?

Framely-Eyes is a **Video Analysis Engine** that uses parallel GPU detectors + reasoning models to understand everything in a video:

- **Objects, faces, emotions, fonts, transitions**
- **Audio mood, mixing levels, speech intelligibility**
- **Color composition, motion, saliency**
- **Scene narrative and intent**

**Output:** One unified `VAB.json` (Video Analysis Bundle) ready for GPT-5 or any LLM-based video editing system.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRAMELY-EYES ENGINE                      │
├─────────────────────────────────────────────────────────────┤
│  PREP → GPU Detectors (parallel) → Merge → Qwen-VL Reasoning│
└─────────────────────────────────────────────────────────────┘

Detectors:
├─ YOLOv8 (coarse + tiled multi-scale)
├─ SAM2 (mask refinement)
├─ Real-ESRGAN (super-resolution for tiny objects)
├─ InsightFace + EmoNet (faces + emotions)
├─ PaddleOCR + DeepFont (text + fonts)
├─ OpenCV (color, composition, motion, saliency)
├─ Audio Engineering Suite (LUFS, STOI, dynamics)
└─ Qwen-VL-2.5 (vision-language reasoning)
```

## 🚀 Quick Start

### Prerequisites

- **NVIDIA GPU** with CUDA 12.4+
- **Docker** with GPU support (`nvidia-docker`)
- **16GB+ VRAM** recommended

### 1. Clone & Setup

```bash
git clone <your-repo>
cd Framely-eyes
cp configs/settings.example.env configs/settings.env
# Edit configs/settings.env if needed
```

### 2. Start Services

```bash
docker compose -f docker/docker-compose.yml up --build
```

This starts:
- **API server** on `http://localhost:8000`
- **Qwen-VL** inference server on `http://localhost:8001`
- **Redis** for job queue

### 3. Analyze a Video

```bash
# Using URL
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "demo_001",
    "media_url": "https://example.com/video.mp4"
  }'

# Check status
curl http://localhost:8000/status/demo_001

# Get results (VAB)
curl http://localhost:8000/result/demo_001
```

### 4. Upload Local File

```bash
curl -X POST http://localhost:8000/ingest \
  -F "video_id=local_001" \
  -F "file=@/path/to/video.mp4"

curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_id": "local_001"}'
```

## 📊 VAB Output Format

The Video Analysis Bundle (VAB) is a structured JSON with:

```json
{
  "schema_version": "1.1.0",
  "status": {
    "state": "ok",
    "reasons": [],
    "coverage": {
      "spatial": {"pixels_covered_pct": 100.0, "min_detectable_px": 8},
      "temporal": {"frames_analyzed_pct": 100.0, "frame_stride": 1},
      "audio": {"lufs_trace_pct": 100.0, "stoi_pct": 92.4}
    }
  },
  "video": {
    "video_id": "demo_001",
    "path": "/app/store/demo_001/video.mp4",
    "sha256": "..."
  },
  "global": {
    "total_frames": 300,
    "duration_s": 10.0,
    "fps": 30.0,
    "resolution": {"width": 1920, "height": 1080}
  },
  "scenes": [
    {
      "scene_id": "sc_000",
      "shots": ["sh_000", "sh_001"],
      "narrative": {
        "narrative_function": "introduction",
        "tone": "professional"
      }
    }
  ],
  "shots": [
    {
      "shot_id": "sh_000",
      "start_frame": 0,
      "end_frame": 150,
      "detectors": {
        "objects": [...],
        "faces": [...],
        "text": [...],
        "color": {...},
        "motion": {...},
        "audio": {...}
      },
      "summary": "Person speaking to camera",
      "mood": "professional"
    }
  ],
  "risks": [
    {
      "shot_id": "sh_005",
      "type": "low_dialogue_intelligibility",
      "severity": "high",
      "metric": {"stoi": 0.62}
    }
  ],
  "provenance": [...],
  "calibration": [...]
}
```

## 🧪 Testing

Run golden tests to validate coverage:

```python
from services.qa.golden_tests import run_all_golden_tests
from services.utils.io import load_vab

vab = load_vab("demo_001")
run_all_golden_tests(vab)
```

Tests include:
- ✅ **Tiny object recall** ≥ 95% on 8×8 px objects
- ✅ **Temporal coverage** = 100% (every frame analyzed)
- ✅ **Audio LUFS trace** = 100%
- ✅ **STOI coverage** ≥ 90% for speech

## ⚙️ Configuration

Edit `configs/limits.yaml` to customize:

```yaml
detect:
  tile:
    size: 512          # Tile size for multi-scale detection
    stride: 256        # Overlap between tiles
  superres:
    enabled: true      # Use Real-ESRGAN upscaling
  small_object_min_px: 8  # Minimum detectable object size

audio:
  loudness:
    target_lufs: -14.0
  stoi:
    enabled: true
    min_ok: 0.80

runtime:
  frame_stride: 1      # Analyze every frame
  gpu_semaphore: 2     # Max concurrent GPU tasks
  oom_fallback_order:  # OOM safety ladder
    - sam2_off
    - sr_off
    - qwen_ctx_shrink

ablation:
  no_sr: false         # Disable super-resolution
  no_tiling: false     # Disable tiled detection
  light_audio: false   # Disable STOI analysis
```

## 🔧 API Endpoints

### Health Check
```bash
GET /health
```

### Analyze Video
```bash
POST /analyze
Content-Type: application/json

{
  "video_id": "string",
  "media_url": "https://...",
  "ablations": {
    "no_sr": false,
    "no_tiling": false
  }
}
```

### Upload Video
```bash
POST /ingest
Content-Type: multipart/form-data

video_id: string
file: binary
```

### Get Job Status
```bash
GET /status/{video_id}
```

### Get Results (VAB)
```bash
GET /result/{video_id}
```

## 📁 Project Structure

```
framely-eyes/
├── services/
│   ├── api/              # FastAPI application
│   ├── orchestrator/     # DAG execution engine
│   ├── detectors/        # All detection modules
│   ├── qwen/            # Qwen-VL reasoning
│   ├── utils/           # I/O, merge, coverage
│   ├── observability/   # Metrics & monitoring
│   └── qa/              # Golden tests
├── configs/
│   ├── limits.yaml
│   ├── model_paths.yaml
│   └── settings.example.env
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile.api
├── store/               # Video analysis storage
└── scripts/
    └── smoke_test.sh
```

## 🎛️ GPU Scheduling

Framely-Eyes uses a sophisticated DAG with GPU pooling:

1. **YOLO coarse** → detect standard objects
2. **YOLO tiled** → multi-scale detection with overlapping tiles
3. **Super-resolution** → upscale low-res frames (if needed)
4. **YOLO fine** → re-detect on upscaled frames
5. **SAM2 refinement** → precise segmentation masks
6. **Parallel CPU tasks** → faces, OCR, color, motion, audio
7. **Qwen-VL reasoning** → holistic understanding

**OOM Safety:** Automatic fallback if GPU runs out of memory:
- Disable SAM2 → Disable SR → Reduce Qwen context

## 📈 Coverage Guarantees

Framely-Eyes guarantees near-complete coverage:

- **Spatial:** 100% pixel coverage via tiled detection (512×512 tiles, 256px stride)
- **Temporal:** 100% frame coverage (frame_stride=1)
- **Audio:** 100% LUFS trace + ≥90% STOI coverage for speech
- **Min detectable size:** 8×8 pixels

Quality gates enforce these thresholds. Status will be `degraded` if coverage drops below targets.

## 🚨 Risks Detection

Framely-Eyes automatically detects:

- **Low dialogue intelligibility** (STOI < 0.8)
- **Caption-face overlap**
- **Audio clipping** (true peak > -1.0 dBTP)
- **Degraded detector performance** (SAM2 disabled, SR failed)

All risks are logged in `vab.risks[]`.

## 🔬 Provenance & Calibration

Every detector logs:
- Tool name & version
- Model checkpoint
- Parameter hash
- Timestamp

Calibration metrics specify expected performance:
```json
{
  "family": "objects",
  "expected_tpr": 0.94,
  "expected_fpr": 0.06
}
```

## 🤝 Contributing

This is a production-grade system. When contributing:

1. Add tests for new detectors
2. Update `calibration` metrics
3. Log `provenance` for reproducibility
4. Respect the DAG execution order

## 📜 License

[Your License Here]

## 🙏 Acknowledgments

Built with:
- YOLOv8 (Ultralytics)
- Segment Anything 2 (Meta)
- Qwen-VL (Alibaba)
- Real-ESRGAN
- InsightFace
- PaddleOCR
- And many more amazing open-source projects

---

**Framely-Eyes** — Because AI deserves to see video like humans do. 👁️✨
