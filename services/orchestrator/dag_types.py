"""DAG types and detector execution order."""
from enum import Enum
from typing import List, Dict, Any


class DetectorStage(Enum):
    """Detector execution stages in DAG."""
    PREP = "prep"
    YOLO_COARSE = "yolo_coarse"
    YOLO_TILED = "yolo_tiled"
    SUPERRES = "superres"
    YOLO_FINE = "yolo_fine"
    SAM2_REFINE = "sam2_refine"
    FACES = "faces"
    OCR_FONTS = "ocr_fonts"
    COLOR_COMP = "color_comp"
    MOTION_SALIENCY = "motion_saliency"
    AUDIO_ENG = "audio_eng"
    TRANSITIONS = "transitions"
    QWEN_VL = "qwen_vl"


class DetectorDAG:
    """Directed Acyclic Graph for detector execution."""
    
    # GPU-intensive stages
    GPU_STAGES = {
        DetectorStage.YOLO_COARSE,
        DetectorStage.YOLO_TILED,
        DetectorStage.YOLO_FINE,
        DetectorStage.SUPERRES,
        DetectorStage.SAM2_REFINE,
        DetectorStage.FACES,
        DetectorStage.QWEN_VL
    }
    
    # CPU-only stages (can run in parallel with GPU)
    CPU_STAGES = {
        DetectorStage.OCR_FONTS,
        DetectorStage.COLOR_COMP,
        DetectorStage.MOTION_SALIENCY,
        DetectorStage.AUDIO_ENG,
        DetectorStage.TRANSITIONS
    }
    
    # Execution order: stages that must complete before next stage
    DEPENDENCIES = {
        DetectorStage.PREP: [],
        DetectorStage.YOLO_COARSE: [DetectorStage.PREP],
        DetectorStage.YOLO_TILED: [DetectorStage.YOLO_COARSE],
        DetectorStage.SUPERRES: [DetectorStage.YOLO_TILED],
        DetectorStage.YOLO_FINE: [DetectorStage.SUPERRES],
        DetectorStage.SAM2_REFINE: [DetectorStage.YOLO_FINE],
        DetectorStage.FACES: [DetectorStage.PREP],
        DetectorStage.OCR_FONTS: [DetectorStage.PREP],
        DetectorStage.COLOR_COMP: [DetectorStage.PREP],
        DetectorStage.MOTION_SALIENCY: [DetectorStage.PREP],
        DetectorStage.AUDIO_ENG: [DetectorStage.PREP],
        DetectorStage.TRANSITIONS: [DetectorStage.PREP],
        DetectorStage.QWEN_VL: [
            DetectorStage.SAM2_REFINE,
            DetectorStage.FACES,
            DetectorStage.OCR_FONTS,
            DetectorStage.COLOR_COMP,
            DetectorStage.MOTION_SALIENCY,
            DetectorStage.AUDIO_ENG
        ]
    }
    
    @classmethod
    def get_execution_order(cls) -> List[List[DetectorStage]]:
        """Get execution order as list of parallel-executable stages.
        
        Returns:
            List of stage groups that can execute in parallel
        """
        return [
            [DetectorStage.PREP],
            [DetectorStage.YOLO_COARSE],
            [DetectorStage.YOLO_TILED],
            [DetectorStage.SUPERRES],
            [DetectorStage.YOLO_FINE],
            [DetectorStage.SAM2_REFINE],
            # These can run in parallel after PREP
            [
                DetectorStage.FACES,
                DetectorStage.OCR_FONTS,
                DetectorStage.COLOR_COMP,
                DetectorStage.MOTION_SALIENCY,
                DetectorStage.AUDIO_ENG,
                DetectorStage.TRANSITIONS
            ],
            [DetectorStage.QWEN_VL]
        ]
    
    @classmethod
    def is_gpu_stage(cls, stage: DetectorStage) -> bool:
        """Check if stage requires GPU.
        
        Args:
            stage: Detector stage
            
        Returns:
            True if GPU required
        """
        return stage in cls.GPU_STAGES
