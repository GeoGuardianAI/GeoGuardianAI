import os
from pathlib import Path
import cv2
import numpy as np

class SamService:
    """Adapter boundary for SAM2. Emits no semantic claim without configured SAM2 weights."""
    def segment(self, image: np.ndarray) -> dict:
        if not os.getenv("GEOGUARDIAN_SAM2_CHECKPOINT"):
            raise RuntimeError("SAM2 checkpoint is not configured. Set GEOGUARDIAN_SAM2_CHECKPOINT.")
        # SAM2 integration belongs here; keeping the contract isolated prevents route changes.
        raise NotImplementedError("Install the SAM2 runtime and register its predictor in SamService.segment.")
