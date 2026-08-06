# Disaster Detection & Monitoring API

This is the Member 1 boundary for geospatial perception. It owns uploads, visual analysis, change analysis, video tracking, detection history, and GIS-ready heatmap features. Downstream modules should consume the structured response from `POST /detect`, `GET /detections`, and `GET /heatmap`; they must not read the local upload store.

## Run locally

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload
```

The client is a Vite application and proxies `/api` to the FastAPI server:

```bash
cd frontend
npm install
npm run dev
```

## API flow

1. `POST /upload-image` or `POST /upload-video` as multipart form data (`file`). Keep the returned `asset_id`.
2. Send `asset_id`, optional `coordinates`, and optional `location` to `POST /detect` or `POST /segment`.
3. Send two image asset IDs to `POST /change-detection`; send a video asset ID to `POST /track`.
4. Consume persisted incidents via `GET /detections` and Leaflet-compatible GeoJSON via `GET /heatmap`.

## Model configuration

`YoloService` loads an Ultralytics-compatible trained model only when `GEOGUARDIAN_YOLO_WEIGHTS` points to its weights. `SamService` is intentionally an adapter boundary and reports a useful validation error until a SAM2 runtime and `GEOGUARDIAN_SAM2_CHECKPOINT` are configured. The OpenCV change detector is a working deterministic baseline with the same response boundary planned for ChangeFormer.

Uploaded paths and incident payloads are stored under `backend/data/`; this directory is runtime state and should be mapped to durable storage in deployment. Replace `DetectionRepository` with the shared project database implementation without changing the route contracts.
