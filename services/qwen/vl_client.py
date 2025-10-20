"""Qwen-VL client for vision-language reasoning via vLLM."""
import os
import base64
import json
import httpx
from typing import Dict, Any, List, Optional
from services.qwen.prompts import (
    SHOT_SYSTEM, SHOT_USER_TEMPLATE,
    SCENE_SYSTEM, SCENE_USER_TEMPLATE
)


# Configuration
QWEN_API_BASE = os.getenv("QWEN_API_BASE", "http://qwen:8000/v1")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "EMPTY")
QWEN_TIMEOUT = int(os.getenv("QWEN_TIMEOUT", "60"))


def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 string.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Base64-encoded image string
    """
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def build_shot_prompt(shot: Dict[str, Any]) -> str:
    """Build user prompt for shot analysis.
    
    Args:
        shot: Shot bundle with detections
        
    Returns:
        Formatted prompt string
    """
    detectors = shot.get("detectors", {})
    
    # Extract key info
    objects = [obj.get("label") for obj in detectors.get("objects", [])][:10]
    faces = len(detectors.get("faces", []))
    text = [t.get("text") for t in detectors.get("text", [])][:5]
    color = detectors.get("color", {})
    motion = detectors.get("motion", {})
    
    return SHOT_USER_TEMPLATE.format(
        shot_id=shot.get("shot_id", "unknown"),
        duration_s=round(shot.get("duration_s", 0), 2),
        frame_count=shot.get("frame_count", 0),
        objects=", ".join(objects) if objects else "none",
        faces=f"{faces} face(s)" if faces > 0 else "none",
        text=", ".join(text) if text else "none",
        brightness=round(color.get("brightness", 0.5), 2),
        saturation=round(color.get("saturation", 0.5), 2),
        motion_type=motion.get("motion_type", "static")
    )


def build_scene_prompt(scene: Dict[str, Any], shots: List[Dict[str, Any]]) -> str:
    """Build user prompt for scene analysis.
    
    Args:
        scene: Scene metadata
        shots: List of shot bundles in scene
        
    Returns:
        Formatted prompt string
    """
    shot_summaries = []
    for shot in shots:
        summary = shot.get("summary", "No summary available")
        shot_summaries.append(f"- {shot['shot_id']}: {summary}")
    
    features = scene.get("features", {})
    
    return SCENE_USER_TEMPLATE.format(
        scene_id=scene.get("scene_id", "unknown"),
        duration_s=round(features.get("total_duration_s", 0), 2),
        shot_count=features.get("shot_count", 0),
        shot_summaries="\n".join(shot_summaries),
        features=json.dumps(features, indent=2)
    )


async def call_qwen_vl(
    system_prompt: str,
    user_prompt: str,
    image_paths: Optional[List[str]] = None,
    max_tokens: int = 512
) -> Dict[str, Any]:
    """Call Qwen-VL API.
    
    Args:
        system_prompt: System prompt
        user_prompt: User prompt
        image_paths: List of image paths (optional)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Parsed JSON response
    """
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Build user message with images
    if image_paths:
        content = [{"type": "text", "text": user_prompt}]
        
        # Limit number of images
        for img_path in image_paths[:12]:
            try:
                img_b64 = encode_image_base64(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })
            except Exception as e:
                print(f"Warning: Failed to encode image {img_path}: {e}")
        
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_prompt})
    
    # Call API
    async with httpx.AsyncClient(timeout=QWEN_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{QWEN_API_BASE}/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-VL-7B-Instruct",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.1
                },
                headers={"Authorization": f"Bearer {QWEN_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract and parse JSON response
            content = result["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    # Return error
                    return {"error": "Failed to parse JSON", "raw": content}
        
        except Exception as e:
            print(f"Error calling Qwen-VL: {e}")
            return {"error": str(e)}


async def analyze_shot(
    shot: Dict[str, Any],
    frame_paths: List[str]
) -> Dict[str, Any]:
    """Analyze a shot using Qwen-VL.
    
    Args:
        shot: Shot bundle with detections
        frame_paths: Paths to frames for this shot
        
    Returns:
        Qwen-VL analysis results
    """
    user_prompt = build_shot_prompt(shot)
    
    # Sample frames evenly
    num_frames = min(len(frame_paths), 12)
    if len(frame_paths) > num_frames:
        step = len(frame_paths) // num_frames
        sampled_frames = [frame_paths[i * step] for i in range(num_frames)]
    else:
        sampled_frames = frame_paths
    
    result = await call_qwen_vl(
        SHOT_SYSTEM,
        user_prompt,
        sampled_frames,
        max_tokens=512
    )
    
    return result


async def analyze_scene(
    scene: Dict[str, Any],
    shots: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze a scene using Qwen-VL.
    
    Args:
        scene: Scene metadata
        shots: List of shot bundles in scene
        
    Returns:
        Qwen-VL scene analysis
    """
    user_prompt = build_scene_prompt(scene, shots)
    
    result = await call_qwen_vl(
        SCENE_SYSTEM,
        user_prompt,
        image_paths=None,  # No images for scene-level analysis
        max_tokens=512
    )
    
    return result
