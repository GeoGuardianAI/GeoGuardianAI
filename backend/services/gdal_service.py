"""Georeferencing boundary; use rasterio/GDAL here when deployed with GDAL support."""
from pathlib import Path
class GdalService:
    def metadata(self, path: Path) -> dict: return {"path": str(path), "crs": None, "bounds": None}
