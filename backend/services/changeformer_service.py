import base64
import cv2
import numpy as np

class ChangeFormerService:
    def compare(self, before: np.ndarray, after: np.ndarray) -> dict:
        """Compare equally sized images without claiming pixel changes are damage."""
        if before.shape != after.shape:
            raise ValueError(
                "Before and after images must have matching dimensions and be pre-aligned."
            )
        delta = cv2.absdiff(cv2.cvtColor(before, cv2.COLOR_BGR2GRAY), cv2.cvtColor(after, cv2.COLOR_BGR2GRAY))
        _, mask = cv2.threshold(cv2.GaussianBlur(delta, (5, 5), 0), 35, 255, cv2.THRESH_BINARY)
        changed = int(np.count_nonzero(mask))
        height, width = mask.shape
        preview = mask
        scale = min(1.0, 1024 / max(width, height))
        if scale < 1:
            preview = cv2.resize(
                mask,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_NEAREST,
            )
        success, encoded = cv2.imencode(".png", preview)
        if not success:
            raise RuntimeError("Unable to encode change preview")
        return {
            "changed_pixel_ratio": round(changed / mask.size, 5),
            "change_preview": f"data:image/png;base64,{base64.b64encode(encoded).decode('ascii')}",
            "width": width,
            "height": height,
            "model": "opencv-baseline",
            "interpretation": "Pixel differences are observations, not confirmed disaster damage.",
        }
