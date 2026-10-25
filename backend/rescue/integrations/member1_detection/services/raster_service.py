"""Metadata and image readers that work with common images and GeoTIFFs."""
from pathlib import Path
import cv2
import numpy as np

class RasterService:
    def read(self, path: Path) -> np.ndarray:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None: raise ValueError("The supplied asset is not a readable raster image")
        return image
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
