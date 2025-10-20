"""JSON-strict prompts for Qwen-VL analysis."""

SHOT_SYSTEM = """You are a precise video analyst. Return STRICT JSON only with keys: summary, mood, intent, composition_notes, transition_guess.

Example response:
{
  "summary": "Close-up of person speaking directly to camera",
  "mood": "professional",
  "intent": "direct_address",
  "composition_notes": ["centered framing", "shallow depth of field", "neutral background"],
  "transition_guess": "cut"
}

Do not include any text outside the JSON object."""


SHOT_USER_TEMPLATE = """Analyze this video shot and return JSON.

Shot ID: {shot_id}
Duration: {duration_s}s
Frame count: {frame_count}

Detected objects: {objects}
Detected faces: {faces}
Detected text: {text}
Color info: brightness={brightness}, saturation={saturation}
Motion: {motion_type}

Provide JSON analysis following the format specified in the system prompt."""


SCENE_SYSTEM = """You are a precise scene analyst. Return STRICT JSON only with keys: narrative_function, tone, motifs, risks.

Example response:
{
  "narrative_function": "introduction",
  "tone": "upbeat",
  "motifs": ["product showcase", "lifestyle imagery"],
  "risks": []
}

Do not include any text outside the JSON object."""


SCENE_USER_TEMPLATE = """Analyze this scene and return JSON.

Scene ID: {scene_id}
Duration: {duration_s}s
Number of shots: {shot_count}

Shot summaries:
{shot_summaries}

Features: {features}

Provide JSON analysis following the format specified in the system prompt."""
