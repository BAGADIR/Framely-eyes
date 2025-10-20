# Framely-Eyes API Examples

Complete examples for all API endpoints.

---

## 1. Health Check

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-20T22:00:00.000000",
  "gpu_available": true,
  "redis_connected": true,
  "qwen_available": true
}
```

---

## 2. Analyze Video (URL)

**Request:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "demo_001",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'
```

**Response:**
```json
{
  "job_id": "job_demo_001",
  "video_id": "demo_001",
  "status": "queued",
  "message": "Analysis job queued"
}
```

---

## 3. Analyze Video (with Ablations)

**Request:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "demo_002",
    "media_url": "https://example.com/video.mp4",
    "ablations": {
      "no_sr": true,
      "light_audio": false
    }
  }'
```

**Response:**
```json
{
  "job_id": "job_demo_002",
  "video_id": "demo_002",
  "status": "queued",
  "message": "Analysis job queued"
}
```

---

## 4. Upload Video File

**Request:**
```bash
curl -X POST http://localhost:8000/ingest \
  -F "video_id=local_001" \
  -F "file=@/path/to/video.mp4"
```

**Response:**
```json
{
  "status": "success",
  "video_id": "local_001",
  "path": "/app/store/local_001/video.mp4"
}
```

Then analyze:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_id": "local_001"}'
```

---

## 5. Check Job Status

**Request:**
```bash
curl http://localhost:8000/status/demo_001
```

**Response (Processing):**
```json
{
  "job_id": "job_demo_001",
  "video_id": "demo_001",
  "state": "processing",
  "progress": 45.0,
  "message": "Analyzing shots...",
  "vab_available": false
}
```

**Response (Completed):**
```json
{
  "job_id": "job_demo_001",
  "video_id": "demo_001",
  "state": "completed",
  "progress": 100.0,
  "message": null,
  "vab_available": true
}
```

**Response (Failed):**
```json
{
  "job_id": "job_demo_001",
  "video_id": "demo_001",
  "state": "failed",
  "progress": 30.0,
  "message": "CUDA out of memory",
  "vab_available": false
}
```

---

## 6. Get Analysis Results (VAB)

**Request:**
```bash
curl http://localhost:8000/result/demo_001
```

**Response (Truncated):**
```json
{
  "schema_version": "1.1.0",
  "status": {
    "state": "ok",
    "reasons": [],
    "coverage": {
      "spatial": {
        "tile_size": 512,
        "stride": 256,
        "sr_used": false,
        "pixels_covered_pct": 100.0,
        "min_detectable_px": 8
      },
      "temporal": {
        "frame_stride": 1,
        "frames_analyzed_pct": 100.0
      },
      "audio": {
        "lufs_trace_pct": 100.0,
        "stoi_pct": 92.4
      }
    }
  },
  "video": {
    "video_id": "demo_001",
    "path": "/app/store/demo_001/video.mp4",
    "sha256": "abc123...",
    "metrics": {
      "latency_ms": {
        "run_analysis": 45230.5
      },
      "gpu_mem_mb_peak": 8192,
      "retries": 0,
      "oom_trips": 0
    }
  },
  "global": {
    "total_frames": 300,
    "duration_s": 10.0,
    "fps": 30.0,
    "resolution": {
      "width": 1920,
      "height": 1080
    },
    "detections": {
      "total_objects": 156,
      "total_faces": 12,
      "total_text_regions": 5,
      "object_counts": {
        "person": 45,
        "car": 8,
        "tree": 23
      },
      "unique_object_classes": 15
    }
  },
  "scenes": [
    {
      "scene_id": "sc_000",
      "shots": ["sh_000", "sh_001", "sh_002"],
      "start_frame": 0,
      "end_frame": 150,
      "features": {
        "avg_brightness": 0.65,
        "dominant_mood": "professional",
        "has_camera_motion": true,
        "shot_count": 3,
        "total_duration_s": 5.0,
        "audio": {
          "avg_loudness": -14.2,
          "has_speech": true,
          "has_music": false
        }
      },
      "narrative": {
        "narrative_function": "introduction",
        "tone": "professional",
        "motifs": ["direct address", "corporate setting"],
        "risks": []
      }
    }
  ],
  "shots": [
    {
      "shot_id": "sh_000",
      "start_frame": 0,
      "end_frame": 50,
      "frame_count": 50,
      "duration_s": 1.67,
      "detectors": {
        "objects": [
          {
            "label": "person",
            "conf": 0.95,
            "bbox": [450, 200, 850, 900],
            "area": 280000.0,
            "class_id": 0
          },
          {
            "label": "laptop",
            "conf": 0.87,
            "bbox": [300, 600, 600, 800],
            "area": 60000.0,
            "class_id": 5
          }
        ],
        "faces": [
          {
            "bbox": [500, 250, 750, 600],
            "conf": 0.98,
            "emotion": "neutral",
            "emotion_conf": 0.85,
            "age": 32,
            "gender": "male"
          }
        ],
        "text": [
          {
            "text": "Welcome",
            "conf": 0.94,
            "bbox": [100, 100, 300, 150],
            "font_family": "sans-serif",
            "is_bold": true
          }
        ],
        "color": {
          "dominant_colors": [
            [45, 85, 120],
            [200, 210, 220],
            [30, 40, 50]
          ],
          "brightness": 0.62,
          "contrast": 45.3,
          "saturation": 0.48,
          "composition": {
            "grid_interest": [
              [0.12, 0.45, 0.23],
              [0.34, 0.67, 0.29],
              [0.15, 0.38, 0.19]
            ],
            "rule_of_thirds_score": 0.34
          }
        },
        "motion": {
          "camera_motion": false,
          "motion_type": "static",
          "avg_flow": [0.02, -0.01],
          "magnitude": 0.022
        },
        "saliency": {
          "salient_center": [0.52, 0.45],
          "salient_area_pct": 23.5,
          "avg_saliency": 0.67
        },
        "audio": {
          "lufs": -14.2,
          "true_peak_dbTP": -3.5,
          "dynamic_range_db": 12.4,
          "speech": {
            "has_speech": true,
            "speech_ratio": 0.89
          },
          "music": {
            "has_music": false,
            "estimated_tempo": 0.0
          },
          "dialogue": {
            "stoi": 0.92,
            "intelligibility": "good"
          },
          "stereo": {
            "is_stereo": true,
            "correlation": 0.85,
            "phase_coherence": 0.92,
            "phase_warning": false
          }
        },
        "transition": {
          "type": "cut",
          "similarity": 0.15,
          "sharpness": "hard"
        },
        "sr_used": false
      },
      "summary": "Professional person speaking directly to camera in office setting",
      "mood": "professional",
      "intent": "direct_address",
      "composition_notes": [
        "centered framing",
        "medium close-up",
        "shallow depth of field"
      ],
      "transition_guess": "cut"
    }
  ],
  "tracks": [],
  "risks": [
    {
      "shot_id": "sh_005",
      "type": "low_dialogue_intelligibility",
      "severity": "high",
      "metric": {
        "stoi": 0.62
      }
    }
  ],
  "provenance": [
    {
      "tool": "ingest",
      "version": "0.2.1",
      "params_hash": "abc123...",
      "ts": "2025-10-20T22:00:00.000000"
    }
  ],
  "calibration": [
    {
      "family": "objects",
      "expected_tpr": 0.94,
      "expected_fpr": 0.06
    },
    {
      "family": "ocr",
      "expected_tpr": 0.97,
      "expected_fpr": 0.03
    },
    {
      "family": "audio",
      "expected_tpr": 0.98,
      "expected_fpr": 0.02
    }
  ]
}
```

---

## 7. Python Client Example

```python
import httpx
import asyncio
import json

class FramelyClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def analyze_video(self, video_id: str, url: str) -> dict:
        """Analyze a video and wait for results."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Start analysis
            response = await client.post(
                f"{self.base_url}/analyze",
                json={"video_id": video_id, "media_url": url}
            )
            response.raise_for_status()
            print(f"Job started: {response.json()}")
            
            # Poll status
            while True:
                status = await client.get(f"{self.base_url}/status/{video_id}")
                status_data = status.json()
                state = status_data["state"]
                progress = status_data.get("progress", 0)
                
                print(f"Status: {state} ({progress}%)")
                
                if state == "completed":
                    break
                elif state == "failed":
                    raise Exception(f"Analysis failed: {status_data.get('message')}")
                
                await asyncio.sleep(5)
            
            # Get results
            result = await client.get(f"{self.base_url}/result/{video_id}")
            return result.json()

# Usage
async def main():
    client = FramelyClient()
    
    vab = await client.analyze_video(
        video_id="test_001",
        url="https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
    )
    
    # Print summary
    print(f"\nAnalysis complete!")
    print(f"Status: {vab['status']['state']}")
    print(f"Frames: {vab['global']['total_frames']}")
    print(f"Shots: {len(vab['shots'])}")
    print(f"Scenes: {len(vab['scenes'])}")
    
    # Save VAB
    with open("vab.json", "w") as f:
        json.dump(vab, f, indent=2)
    
    print(f"VAB saved to vab.json")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8. JavaScript/TypeScript Client Example

```typescript
interface VAB {
  schema_version: string;
  status: {
    state: string;
    coverage: any;
  };
  shots: any[];
  scenes: any[];
}

class FramelyClient {
  constructor(private baseUrl: string = "http://localhost:8000") {}

  async analyzeVideo(videoId: string, url: string): Promise<VAB> {
    // Start analysis
    const analyzeResponse = await fetch(`${this.baseUrl}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, media_url: url })
    });
    
    const jobInfo = await analyzeResponse.json();
    console.log("Job started:", jobInfo);

    // Poll status
    while (true) {
      const statusResponse = await fetch(`${this.baseUrl}/status/${videoId}`);
      const status = await statusResponse.json();
      
      console.log(`Status: ${status.state} (${status.progress}%)`);
      
      if (status.state === "completed") break;
      if (status.state === "failed") {
        throw new Error(`Analysis failed: ${status.message}`);
      }
      
      await new Promise(resolve => setTimeout(resolve, 5000));
    }

    // Get results
    const resultResponse = await fetch(`${this.baseUrl}/result/${videoId}`);
    return await resultResponse.json();
  }
}

// Usage
const client = new FramelyClient();
const vab = await client.analyzeVideo(
  "test_001",
  "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
);

console.log("Analysis complete!");
console.log(`Shots: ${vab.shots.length}`);
console.log(`Scenes: ${vab.scenes.length}`);
```

---

## Query Examples (using jq)

### Get coverage metrics
```bash
curl -s http://localhost:8000/result/demo_001 | jq '.status.coverage'
```

### List all detected objects
```bash
curl -s http://localhost:8000/result/demo_001 | jq '.shots[].detectors.objects[] | .label'
```

### Get shot summaries
```bash
curl -s http://localhost:8000/result/demo_001 | jq '.shots[] | {id: .shot_id, summary: .summary}'
```

### Check for risks
```bash
curl -s http://localhost:8000/result/demo_001 | jq '.risks'
```

### Get audio metrics for first shot
```bash
curl -s http://localhost:8000/result/demo_001 | jq '.shots[0].detectors.audio'
```

### Count faces per shot
```bash
curl -s http://localhost:8000/result/demo_001 | jq '.shots[] | {shot: .shot_id, faces: (.detectors.faces | length)}'
```
