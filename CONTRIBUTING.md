# Contributing to Framely-Eyes

Thank you for your interest in contributing to Framely-Eyes! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain high code quality
- Document your changes

## Development Setup

### 1. Clone and Setup
```bash
git clone <repo-url>
cd Framely-eyes
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest services/qa/
```

### 3. Start Development Server
```bash
docker compose -f docker/docker-compose.yml up --build
```

## Project Structure

```
services/
├── api/              # FastAPI endpoints
├── orchestrator/     # DAG execution
├── detectors/        # Detection modules
├── qwen/            # VL reasoning
├── utils/           # Utilities
├── observability/   # Metrics
└── qa/              # Tests
```

## Adding a New Detector

### 1. Create Detector Module

Create `services/detectors/my_detector.py`:

```python
"""My custom detector."""
from typing import Dict, Any
from services.utils.hashing import sha256_obj


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run my detector on a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Detection results with provenance
    """
    params = {
        "model": "my_model_v1",
        "threshold": 0.5
    }
    
    # Load frame
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"results": [], "provenance": {}}
    
    # Run detection
    results = []  # Your detection logic here
    
    # Add provenance
    provenance = {
        "tool": "my_detector",
        "version": "1.0.0",
        "ckpt": "my_model_v1.pth",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "results": results,
        "provenance": provenance
    }
```

### 2. Add to Orchestrator

In `services/orchestrator/orchestrator.py`:

```python
from services.detectors import my_detector

# In analyze_shot function:
my_result = my_detector.detect(shot, cfg)
detectors["my_results"] = my_result.get("results", [])
```

### 3. Add Configuration

In `configs/limits.yaml`:

```yaml
my_detector:
  enabled: true
  threshold: 0.5
  model: my_model_v1
```

### 4. Update Calibration

In `services/orchestrator/orchestrator.py`, add calibration:

```python
vab["calibration"].append({
    "family": "my_detector",
    "expected_tpr": 0.90,
    "expected_fpr": 0.10
})
```

### 5. Write Tests

Create `services/qa/test_my_detector.py`:

```python
"""Tests for my_detector."""
import pytest
from services.detectors import my_detector


def test_my_detector():
    shot = {
        "shot_id": "sh_000",
        "frame_paths": ["test_frame.jpg"]
    }
    cfg = {"my_detector": {"threshold": 0.5}}
    
    result = my_detector.detect(shot, cfg)
    
    assert "results" in result
    assert "provenance" in result
    assert result["provenance"]["tool"] == "my_detector"
```

## Coding Standards

### Python Style
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for all functions

### Example:
```python
def process_frame(
    frame: np.ndarray,
    threshold: float = 0.5
) -> Dict[str, Any]:
    """Process a single frame.
    
    Args:
        frame: Input frame as numpy array
        threshold: Detection threshold
        
    Returns:
        Processing results
    """
    # Implementation
    pass
```

### Documentation
- Document all public APIs
- Include usage examples
- Update README.md for new features
- Add architecture notes to ARCHITECTURE.md

### Commit Messages

Use conventional commits:

```
feat: add new emotion detector
fix: correct STOI calculation for mono audio
docs: update API documentation
test: add tests for tile_yolo
perf: optimize frame extraction
refactor: simplify coverage computation
```

## Testing Guidelines

### Unit Tests
- Test each detector independently
- Mock external dependencies
- Test edge cases

### Integration Tests
- Test full pipeline on sample video
- Validate VAB structure
- Check coverage metrics

### Golden Tests
- Add synthetic test cases
- Validate against ground truth
- Test performance thresholds

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes
4. **Test** thoroughly
5. **Commit** with clear messages
6. **Push** to your fork: `git push origin feature/my-feature`
7. **Submit** a pull request

### PR Checklist
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Provenance tracking added
- [ ] Coverage metrics maintained
- [ ] No breaking changes (or documented)

## Performance Considerations

### GPU Memory
- Use GPU pooling for heavy operations
- Implement OOM fallbacks
- Release resources promptly

### CPU Efficiency
- Parallelize independent operations
- Cache model loading
- Avoid unnecessary copies

### Example:
```python
# Good: Cache model
_model = None

def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model

# Bad: Load every time
def process():
    model = load_model()  # Slow!
    return model.predict()
```

## Debugging Tips

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check GPU Memory
```bash
watch -n 1 nvidia-smi
```

### Inspect VAB
```bash
cat store/video_001/vab.json | jq '.'
```

### Profile Performance
```python
from services.observability.metrics import timed

@timed("my_function")
def my_function():
    pass
```

## Questions?

- Open an issue for bugs
- Start a discussion for features
- Check existing issues first
- Be patient and respectful

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to Framely-Eyes! 🙏
