import cv2
import numpy as np

class ChangeFormerService:
    def compare(self, before: np.ndarray, after: np.ndarray) -> dict:
        """Deterministic baseline registered to the same contract as ChangeFormer."""
        target = (min(before.shape[1], after.shape[1]), min(before.shape[0], after.shape[0]))
        before, after = cv2.resize(before, target), cv2.resize(after, target)
        delta = cv2.absdiff(cv2.cvtColor(before, cv2.COLOR_BGR2GRAY), cv2.cvtColor(after, cv2.COLOR_BGR2GRAY))
        _, mask = cv2.threshold(cv2.GaussianBlur(delta, (5, 5), 0), 35, 255, cv2.THRESH_BINARY)
        changed = int(np.count_nonzero(mask)); total = mask.size
        return {"changed_pixel_ratio": round(changed / total, 5), "change_mask": mask.tolist(), "model": "opencv-baseline"}
