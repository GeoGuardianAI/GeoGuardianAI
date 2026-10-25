# Disaster Detection & Monitoring API

This is the Member 1 boundary for geospatial perception. It owns uploads, visual analysis, change analysis, video tracking, detection history, and GIS-ready heatmap features. Downstream modules should consume the structured response from `POST /detect`, `GET /detections`, and `GET /heatmap`; they must not read the local upload store.

## Run locally

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload
```

On Windows PowerShell, create and activate the environment with:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

For inference, install a compatible Ultralytics runtime separately, set `GEOGUARDIAN_YOLO_WEIGHTS` to the path of a trained weights file, and optionally set `GEOGUARDIAN_YOLO_CONFIDENCE`. The model's actual trained classes determine what it can detect.

The client is a Vite application and proxies `/api` to the FastAPI server:

```bash
cd frontend
npm install
npm run dev
```

The dashboard provides overview/map, satellite and drone intake, detection history/details, confidence-weighted geospatial points, before/after comparison, and prompted SAM2 segmentation screens. Satellite and video intake include local previews and drag-and-drop; video tracking exposes frame-stride and decode limits.

## API flow

1. `POST /upload-image` or `POST /upload-video` as multipart form data (`file`). Keep the returned `asset_id`.
2. Send `asset_id`, optional `coordinates`, and optional `location` to `POST /detect` or `POST /segment`.
3. Send two image asset IDs to `POST /change-detection`; send a video asset ID to `POST /track`.
4. For asynchronous detection, send the same request body to `POST /jobs/detection` and use its `job_id` to monitor `GET /jobs/{job_id}` or `WS /ws/detection/{job_id}`. Completed jobs contain the normal incident response under `result`; failed jobs include an `error`.
5. Read an individual persisted incident with `GET /detections/{incident_id}`. Consume the incident list via `GET /detections` and GeoJSON via `GET /heatmap`.

Detection responses include the source asset ID/name, configured model label, processing status, optional coordinates, and a GeoJSON Point when a location is known. Coordinates supplied by the caller take precedence; otherwise, GeoTIFF coordinates are derived from its CRS and raster center. Image upload responses include raster dimensions and any available GeoTIFF center. Images without geospatial metadata remain unlocated; the API does not substitute a default coordinate.

Uploaded asset metadata is stored in the existing SQLite database so asset IDs remain usable after an API restart. Image uploads accept JPG/JPEG, PNG, and TIFF; video uploads accept MP4, MOV, and AVI. Uploads are limited to 2 GB.

## Model configuration

`YoloService` loads an Ultralytics-compatible trained model only when `GEOGUARDIAN_YOLO_WEIGHTS` points to an existing weights file. Optionally set `GEOGUARDIAN_YOLO_CONFIDENCE` (default `0.25`, range `0`-`1`). Install Ultralytics separately to enable inference. Detection requests fail clearly if the weights or runtime are missing; no synthetic detections are returned. Video tracking uses the same configured detector with Ultralytics ByteTrack and samples frames according to `frame_stride` (default 10) up to `max_frames` (default 300).

SAM 2 segmentation is enabled when the SAM2/PyTorch runtime is installed and both `GEOGUARDIAN_SAM2_CHECKPOINT` and `GEOGUARDIAN_SAM2_CONFIG` point to files. `POST /segment` accepts foreground/background `points` (`x`, `y`, and optional `label` 0/1) and/or a bounding `box`; it returns a PNG mask, pixel area, predictor score, and simplified boundaries. If runtime configuration is absent, the endpoint returns an explicit error.

The OpenCV change detector is a deterministic pixel-difference baseline, not a trained ChangeFormer model. It requires equal-sized, pre-aligned images; pixel differences are observations and not confirmed disaster damage.

Uploaded files and incident/asset metadata are stored under `backend/data/`; this directory is runtime state and should be mapped to durable storage in deployment. SQLite is the existing repository implementation; replace `DetectionRepository` with the shared project database implementation without changing the route contracts.

Detection jobs run in-process and model inference is serialized through one inference slot. Job states are persisted in SQLite; jobs left queued or running after an API restart are marked failed rather than silently retried. This lightweight implementation is suitable for a single API process, not a distributed worker queue.

## Development tests

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
```
