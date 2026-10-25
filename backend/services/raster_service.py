"""Metadata and image readers that work with common images and GeoTIFFs."""
from pathlib import Path
import cv2
import numpy as np
from models.schemas import Coordinates

class RasterService:
    def read(self, path: Path) -> np.ndarray:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None: raise ValueError("The supplied asset is not a readable raster image")
        return image
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def geospatial_center(self, path: Path) -> Coordinates | None:
        if path.suffix.lower() not in {".tif", ".tiff"}:
            return None
        try:
            import rasterio
            from rasterio.errors import RasterioIOError
            from rasterio.warp import transform
        except ImportError:
            return None

        try:
            with rasterio.open(path) as dataset:
                if dataset.crs is None:
                    return None
                x, y = dataset.transform * (dataset.width / 2, dataset.height / 2)
                longitude, latitude = transform(dataset.crs, "EPSG:4326", [x], [y])
                return Coordinates(lat=latitude[0], lng=longitude[0])
        except RasterioIOError:
            return None

    def metadata(self, path: Path) -> dict:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError("The supplied asset is not a readable raster image")
        height, width = image.shape[:2]
        coordinates = self.geospatial_center(path) if path.suffix.lower() in {".tif", ".tiff"} else None
        return {
            "width": width,
            "height": height,
            "coordinates": coordinates.model_dump() if coordinates else None,
        }
