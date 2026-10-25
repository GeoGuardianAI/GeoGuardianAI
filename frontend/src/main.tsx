import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './styles.css';

type Coordinates = { lat: number; lng: number };
type DetectionObject = { class: string; confidence: number; bbox?: { x1: number; y1: number; x2: number; y2: number } | null; track_id?: number | null };
type Incident = {
  incident_id: string;
  disaster: string;
  confidence: number;
  affected_area_sqkm: number;
  damaged_buildings: number;
  coordinates: Coordinates | null;
  timestamp: string;
  detected_objects: DetectionObject[];
  source_asset_id?: string | null;
  source_file?: string | null;
  model_name?: string;
  processing_status?: string;
};
type GeoFeature = { geometry: { type: string; coordinates: number[] } | null; properties: { incident_id: string; risk: number; disaster: string; timestamp: string } };
type Screen = 'overview' | 'satellite' | 'drone' | 'history' | 'heatmap' | 'compare' | 'segment';

const api = async <T,>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch { /* Keep the HTTP status when the response isn't JSON. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
};

const uploadFile = <T,>(path: string, file: File, onProgress: (progress: number) => void): Promise<T> =>
  new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', `/api${path}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100));
    };
    request.onerror = () => reject(new Error('Network error while uploading file.'));
    request.onload = () => {
      let body: { detail?: string } & T;
      try { body = JSON.parse(request.responseText) as { detail?: string } & T; }
      catch { reject(new Error(`Upload failed (${request.status}).`)); return; }
      if (request.status < 200 || request.status >= 300) reject(new Error(body.detail ?? `Upload failed (${request.status}).`));
      else resolve(body);
    };
    const form = new FormData();
    form.append('file', file);
    request.send(form);
  });

function App() {
  const [screen, setScreen] = useState<Screen>('overview');
  const [selected, setSelected] = useState<string>();
  const incidents = useQuery({ queryKey: ['detections'], queryFn: () => api<Incident[]>('/detections'), refetchInterval: 15000 });
  const heatmap = useQuery({ queryKey: ['heatmap'], queryFn: () => api<{ features: GeoFeature[] }>('/heatmap'), enabled: screen === 'heatmap' });
  const list = incidents.data ?? [];
  const active = list.filter((item) => item.disaster !== 'No significant disaster');
  const pageTitle: Record<Screen, string> = {
    overview: 'Incident overview',
    satellite: 'Satellite image analysis',
    drone: 'Drone video monitoring',
    history: 'Detection history',
    heatmap: 'Risk heatmap',
    compare: 'Before-and-after comparison',
    segment: 'Affected-area segmentation',
  };
  return <main>
    <aside>
      <div className="brand"><span>◈</span> GeoGuardian <b>AI</b></div>
      <div className="workspace">OPERATIONS WORKSPACE</div>
      <NavButton active={screen === 'overview'} onClick={() => setScreen('overview')}>Overview</NavButton>
      <NavButton active={screen === 'satellite'} onClick={() => setScreen('satellite')}>Satellite analysis</NavButton>
      <NavButton active={screen === 'drone'} onClick={() => setScreen('drone')}>Drone monitoring</NavButton>
      <div className="nav-section">INTELLIGENCE</div>
      <NavButton active={screen === 'history'} onClick={() => setScreen('history')}>Detection history</NavButton>
      <NavButton active={screen === 'heatmap'} onClick={() => setScreen('heatmap')}>Risk heatmap</NavButton>
      <NavButton active={screen === 'compare'} onClick={() => setScreen('compare')}>Image comparison</NavButton>
      <NavButton active={screen === 'segment'} onClick={() => setScreen('segment')}>Area segmentation</NavButton>
      <div className="status"><i/> API status<br/><small>{incidents.isError ? 'Connection failed' : incidents.isLoading ? 'Connecting…' : 'Connected'}</small></div>
    </aside>
    <div className="content">
      <header><div><div className="eyebrow">DISASTER DETECTION & MONITORING</div><h1>{pageTitle[screen]}</h1></div><div className="time">LIVE STATUS<br/><b>{incidents.isError ? 'API unavailable' : incidents.isFetching ? 'Syncing intelligence' : 'Monitoring active'}</b></div></header>
      {incidents.isError && <div className="error-banner" role="alert">{incidents.error.message}. Start the backend at <code>http://localhost:8000</code>.</div>}
      {screen === 'overview' && <Overview incidents={list} active={active} loading={incidents.isLoading} onSelect={(id) => { setSelected(id); setScreen('history'); }} />}
      {screen === 'satellite' && <UploadPanel kind="image" onIncident={(incident) => { void incidents.refetch(); setSelected(incident.incident_id); setScreen('history'); }} />}
      {screen === 'drone' && <UploadPanel kind="video" />}
      {screen === 'history' && <History incidents={list} selected={selected} onSelect={setSelected} />}
      {screen === 'heatmap' && <Heatmap features={heatmap.data?.features ?? []} loading={heatmap.isLoading} error={heatmap.error?.message} />}
      {screen === 'compare' && <ComparePanel />}
      {screen === 'segment' && <SegmentPanel />}
    </div>
  </main>;
}

function NavButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button className={`nav${active ? ' active' : ''}`} onClick={onClick}>{children}</button>;
}

function Overview({ incidents, active, loading, onSelect }: { incidents: Incident[]; active: Incident[]; loading: boolean; onSelect: (id: string) => void }) {
  const located = incidents.filter((incident) => incident.coordinates !== null);
  const average = incidents.length ? Math.round(incidents.reduce((sum, item) => sum + item.confidence, 0) / incidents.length * 100) : null;
  return <>
    <section className="metrics">
      <Metric label="Active incidents" value={String(active.length).padStart(2, '0')} tone="red"/>
      <Metric label="Assets analyzed" value={String(incidents.length).padStart(2, '0')} tone="blue"/>
      <Metric label="Mean confidence" value={average === null ? '—' : `${average}%`} tone="amber"/>
      <Metric label="Damaged structures" value={String(incidents.reduce((sum, item) => sum + item.damaged_buildings, 0)).padStart(2, '0')} tone="purple"/>
    </section>
    <section className="map-card">
      <div className="map-header"><div><h2>Incident map</h2><p>Locations from detections with known coordinates</p></div><span className="legend">{located.length} mapped · {incidents.length - located.length} unlocated</span></div>
      <MapContainer center={[20.5937, 78.9629]} zoom={5} scrollWheelZoom className="map"><TileLayer attribution="© OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>{located.map((incident) => <CircleMarker key={incident.incident_id} center={[incident.coordinates!.lat, incident.coordinates!.lng]} radius={9} pathOptions={{ color: incident.disaster === 'No significant disaster' ? '#35b6d5' : '#f16565', fillOpacity: 0.7 }}><Popup><b>{incident.disaster}</b><br/>{Math.round(incident.confidence * 100)}% confidence<br/><button className="text-button" onClick={() => onSelect(incident.incident_id)}>View incident</button></Popup></CircleMarker>)}</MapContainer>
    </section>
    <section className="activity"><div className="section-heading"><h2>Recent detection history</h2><span>{loading ? 'Loading…' : `${incidents.length} records`}</span></div><IncidentTable incidents={incidents.slice(0, 8)} onSelect={onSelect}/></section>
  </>;
}

function UploadPanel({ kind, onIncident }: { kind: 'image' | 'video'; onIncident?: (incident: Incident) => void }) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File>();
  const [asset, setAsset] = useState<string>();
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [frameStride, setFrameStride] = useState(10);
  const [maxFrames, setMaxFrames] = useState(300);
  const [tracking, setTracking] = useState<{ frames_processed: number; detections: DetectionObject[] }>();
  const [preview, setPreview] = useState<string>();
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const selectFile = (selected?: File) => {
    if (!selected) return;
    setFile(selected);
    setAsset(undefined);
    setTracking(undefined);
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(selected);
    });
    setNotice('');
  };
  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setProgress(0);
    try {
      const result = await uploadFile<{ asset_id: string; metadata?: { width: number; height: number; coordinates: Coordinates | null } }>(`/upload-${kind}`, file, setProgress);
      setAsset(result.asset_id);
      setNotice(result.metadata ? `Uploaded ${file.name} · ${result.metadata.width} × ${result.metadata.height}${result.metadata.coordinates ? ' · geospatial center found' : ' · no geospatial coordinates'}` : `Uploaded ${file.name}`);
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Upload failed'); }
    finally { setBusy(false); }
  };
  const analyze = async () => {
    if (!asset) return;
    setBusy(true);
    setNotice(kind === 'image' ? 'Running configured object detector…' : 'Sampling video frames for tracking…');
    try {
      if (kind === 'image') {
        if ((latitude.trim() === '') !== (longitude.trim() === '')) throw new Error('Provide both latitude and longitude, or leave both blank.');
        const coordinates = latitude.trim() ? { lat: Number(latitude), lng: Number(longitude) } : undefined;
        if (coordinates && (!Number.isFinite(coordinates.lat) || !Number.isFinite(coordinates.lng) || coordinates.lat < -90 || coordinates.lat > 90 || coordinates.lng < -180 || coordinates.lng > 180)) throw new Error('Coordinates must be valid latitude (-90 to 90) and longitude (-180 to 180).');
        const incident = await api<Incident>('/detect', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ asset_id: asset, coordinates }) });
        setNotice(`Detection complete · ${incident.detected_objects.length} objects · ${incident.model_name ?? 'model not specified'}`);
        await queryClient.invalidateQueries({ queryKey: ['detections'] });
        onIncident?.(incident);
      } else {
        const result = await api<{ frames_processed: number; detections: DetectionObject[] }>('/track', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ asset_id: asset, max_frames: maxFrames, frame_stride: frameStride }) });
        setTracking(result);
        setNotice(`Tracking complete · ${result.frames_processed} sampled frames · ${result.detections.length} observations`);
      }
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Processing failed'); }
    finally { setBusy(false); }
  };
  const image = kind === 'image';
  return <section className="upload-panel">
    <div className="eyebrow">{image ? 'SATELLITE INTAKE' : 'DRONE INTAKE'}</div>
    <h2>{image ? 'Analyze satellite imagery' : 'Track drone footage'}</h2>
    <p>Uploads are validated by file extension and media signature. No location is assumed when metadata is absent.</p>
    <label className="drop" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]); }}><input type="file" accept={image ? 'image/jpeg,image/png,image/tiff,.tif,.tiff' : 'video/mp4,video/quicktime,video/x-msvideo'} onChange={(event) => selectFile(event.target.files?.[0])}/><span>{file?.name ?? 'Choose a file or drop it here'}</span><small>{image ? 'GeoTIFF, TIFF, PNG, JPG' : 'MP4, MOV, AVI'} · 2 GB maximum</small></label>
    {preview && (image ? <img className="upload-preview" src={preview} alt="Selected image preview"/> : <video className="upload-preview video-preview" src={preview} controls aria-label="Selected video preview"/>)}
    {image && <div className="location-fields"><label>Latitude<input type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} placeholder="Optional"/></label><label>Longitude<input type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} placeholder="Optional"/></label><small>Leave both blank to use GeoTIFF metadata when available.</small></div>}
    {!image && <div className="location-fields"><label>Frame stride<input type="number" min="1" max="300" value={frameStride} onChange={(event) => setFrameStride(Math.max(1, Math.min(300, Number(event.target.value))))}/></label><label>Max frames to decode<input type="number" min="1" max="3000" value={maxFrames} onChange={(event) => setMaxFrames(Math.max(1, Math.min(3000, Number(event.target.value))))}/></label><small>Tracker samples every Nth decoded frame to reduce unnecessary inference.</small></div>}
    <div><button onClick={() => void upload()} disabled={!file || busy}>Upload asset{busy && progress > 0 ? ` · ${progress}%` : ''}</button><button className="quiet" onClick={() => void analyze()} disabled={!asset || busy}>{busy ? 'Processing…' : image ? 'Run detection' : 'Run tracking'}</button></div>
    {notice && <div className={notice.toLowerCase().includes('complete') || notice.toLowerCase().includes('uploaded') ? 'notice' : 'notice warning'} role="status">{notice}</div>}
    {tracking && <section className="result-card"><h3>Sampled video observations</h3><p>Model: {tracking.detections.length ? 'configured YOLO + ByteTrack' : 'No objects detected in sampled frames'}</p><ObjectTable objects={tracking.detections}/></section>}
  </section>;
}

function History({ incidents, selected, onSelect }: { incidents: Incident[]; selected?: string; onSelect: (id: string) => void }) {
  const [filter, setFilter] = useState('All categories');
  const categories = useMemo(() => ['All categories', ...new Set(incidents.map((incident) => incident.disaster))], [incidents]);
  const visible = filter === 'All categories' ? incidents : incidents.filter((incident) => incident.disaster === filter);
  const current = incidents.find((incident) => incident.incident_id === selected);
  return <section className="activity history-page">
    <div className="section-heading"><div><h2>Detection records</h2><p>Persisted analysis results from the backend.</p></div><label className="filter-label">Filter<select value={filter} onChange={(event) => setFilter(event.target.value)}>{categories.map((category) => <option key={category}>{category}</option>)}</select></label></div>
    {visible.length ? <IncidentTable incidents={visible} onSelect={onSelect}/> : <Empty>No detections match this filter.</Empty>}
    {current && <div className="result-card"><div className="section-heading"><div><h3>{current.disaster} · {current.incident_id}</h3><p>{current.source_file ?? current.source_asset_id ?? 'Source not recorded'}</p></div><button className="quiet" onClick={() => onSelect('')}>Close details</button></div><div className="detail-grid"><span>Confidence<strong>{Math.round(current.confidence * 100)}%</strong></span><span>Model<strong>{current.model_name ?? 'Not recorded'}</strong></span><span>Observed<strong>{new Date(current.timestamp).toLocaleString()}</strong></span><span>Location<strong>{current.coordinates ? `${current.coordinates.lat.toFixed(5)}, ${current.coordinates.lng.toFixed(5)}` : 'Unknown'}</strong></span></div><h4>Detected objects</h4><ObjectTable objects={current.detected_objects}/></div>}
  </section>;
}

function Heatmap({ features, loading, error }: { features: GeoFeature[]; loading: boolean; error?: string }) {
  const points = features.filter((feature) => feature.geometry?.type === 'Point');
  return <section className="map-card"><div className="map-header"><div><h2>Detection risk points</h2><p>Point intensity reflects backend detection confidence; no interpolated surface is fabricated.</p></div><span className="legend">{points.length} located observations</span></div>{error ? <div className="error-banner">{error}</div> : loading ? <Empty>Loading geospatial detections…</Empty> : <MapContainer center={[20.5937, 78.9629]} zoom={5} scrollWheelZoom className="map map-tall"><TileLayer attribution="© OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>{points.map((feature) => { const [lng, lat] = feature.geometry!.coordinates; const weight = Math.max(0, Math.min(1, feature.properties.risk)); return <CircleMarker key={feature.properties.incident_id} center={[lat, lng]} radius={7 + weight * 11} pathOptions={{ color: '#df605d', fillColor: '#f16c61', fillOpacity: 0.25 + weight * 0.6, weight: 1 }}><Popup><b>{feature.properties.disaster}</b><br/>{Math.round(weight * 100)}% confidence<br/>{feature.properties.incident_id}</Popup></CircleMarker>; })}</MapContainer>}</section>;
}

function ComparePanel() {
  const [before, setBefore] = useState<File>();
  const [after, setAfter] = useState<File>();
  const [result, setResult] = useState<{ changed_pixel_ratio: number; model: string; change_preview: string; width: number; height: number }>();
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const run = async () => {
    if (!before || !after) return;
    setBusy(true); setMessage('');
    try {
      const upload = async (file: File) => { const form = new FormData(); form.append('file', file); return api<{ asset_id: string }>('/upload-image', { method: 'POST', body: form }); };
      const [beforeAsset, afterAsset] = await Promise.all([upload(before), upload(after)]);
      const comparison = await api<{ changed_pixel_ratio: number; model: string; change_preview: string; width: number; height: number }>('/change-detection', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ before_asset_id: beforeAsset.asset_id, after_asset_id: afterAsset.asset_id }) });
      setResult(comparison);
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Comparison failed'); }
    finally { setBusy(false); }
  };
  return <section className="upload-panel compare-panel"><div className="eyebrow">CHANGE ANALYSIS</div><h2>Before-and-after comparison</h2><p>Compare two images. The current implementation is an OpenCV pixel-difference baseline, not a trained ChangeFormer model or a confirmation of damage.</p><div className="compare-inputs"><FileChoice label="Before image" file={before} setFile={setBefore}/><FileChoice label="After image" file={after} setFile={setAfter}/></div><button onClick={() => void run()} disabled={!before || !after || busy}>{busy ? 'Comparing…' : 'Compare images'}</button>{message && <div className="notice warning" role="alert">{message}</div>}{result && <div className="result-card"><div className="section-heading"><div><h3>Change analysis result</h3><p>Baseline: {result.model} · {result.width} × {result.height}</p></div><strong>{(result.changed_pixel_ratio * 100).toFixed(2)}% changed pixels</strong></div><img className="change-preview" src={result.change_preview} alt="Thresholded image difference preview"/></div>}</section>;
}

function SegmentPanel() {
  const imageRef = useRef<HTMLImageElement>(null);
  const [file, setFile] = useState<File>();
  const [asset, setAsset] = useState<string>();
  const [preview, setPreview] = useState<string>();
  const [point, setPoint] = useState<{ x: number; y: number }>();
  const [mask, setMask] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const upload = async (selected: File) => {
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setMask(undefined);
    setPoint(undefined);
    setAsset(undefined);
    setMessage('');
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', selected);
      const result = await api<{ asset_id: string }>('/upload-image', { method: 'POST', body: form });
      setAsset(result.asset_id);
      setMessage('Image uploaded. Click the region to segment.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Upload failed'); }
    finally { setBusy(false); }
  };
  const choosePoint = (event: React.MouseEvent<HTMLImageElement>) => {
    const image = imageRef.current;
    if (!image) return;
    const bounds = image.getBoundingClientRect();
    setPoint({
      x: (event.clientX - bounds.left) / bounds.width * image.naturalWidth,
      y: (event.clientY - bounds.top) / bounds.height * image.naturalHeight,
    });
    setMask(undefined);
  };
  const segment = async () => {
    if (!asset || !point) return;
    setBusy(true);
    setMessage('Running SAM 2 segmentation…');
    try {
      const result = await api<{ mask_png: string; area_pixels: number; confidence: number }>('/segment', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ asset_id: asset, points: [{ ...point, label: 1 }] }),
      });
      setMask(result.mask_png);
      setMessage(`Mask generated · ${result.area_pixels.toLocaleString()} pixels · ${Math.round(result.confidence * 100)}% predictor score`);
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Segmentation failed'); }
    finally { setBusy(false); }
  };
  return <section className="upload-panel segment-panel"><div className="eyebrow">PROMPT-BASED SEGMENTATION</div><h2>Mark an affected region</h2><p>Select an image, upload it, then click a foreground point in the area to segment. Requires the optional SAM 2 runtime and configured checkpoint.</p><label className="file-choice"><strong>Satellite or drone image</strong><input type="file" accept="image/jpeg,image/png,image/tiff,.tif,.tiff" onChange={(event) => { const selected = event.target.files?.[0]; if (selected) void upload(selected); }}/><span>{file?.name ?? 'Choose image'}</span></label>{preview && <div className="segment-preview" onClick={choosePoint}><img ref={imageRef} src={preview} alt="Selected image for segmentation"/>{mask && <img className="mask-overlay" src={mask} alt="SAM 2 predicted mask overlay"/>}{point && <span className="prompt-point" style={{ left: `${point.x / (imageRef.current?.naturalWidth || 1) * 100}%`, top: `${point.y / (imageRef.current?.naturalHeight || 1) * 100}%` }}/>}</div>}<button onClick={() => void segment()} disabled={!asset || !point || busy}>{busy ? 'Processing…' : 'Segment clicked region'}</button>{message && <div className="notice warning" role="status">{message}</div>}</section>;
}

function FileChoice({ label, file, setFile }: { label: string; file?: File; setFile: (file?: File) => void }) {
  return <label className="file-choice"><strong>{label}</strong><input type="file" accept="image/jpeg,image/png,image/tiff,.tif,.tiff" onChange={(event) => setFile(event.target.files?.[0])}/><span>{file?.name ?? 'Choose image'}</span></label>;
}

function IncidentTable({ incidents, onSelect }: { incidents: Incident[]; onSelect: (id: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>INCIDENT</th><th>CLASSIFICATION</th><th>CONFIDENCE</th><th>LOCATION</th><th>OBSERVED</th></tr></thead><tbody>{incidents.map((incident) => <tr key={incident.incident_id} onClick={() => onSelect(incident.incident_id)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(incident.incident_id); }}><td>{incident.incident_id}</td><td><span className="tag">{incident.disaster}</span></td><td>{Math.round(incident.confidence * 100)}%</td><td>{incident.coordinates ? `${incident.coordinates.lat.toFixed(3)}, ${incident.coordinates.lng.toFixed(3)}` : 'Unknown'}</td><td>{new Date(incident.timestamp).toLocaleString()}</td></tr>)}</tbody></table></div>;
}

function ObjectTable({ objects }: { objects: DetectionObject[] }) {
  if (!objects.length) return <p className="muted">No objects returned by this analysis.</p>;
  return <div className="table-wrap"><table><thead><tr><th>CLASS</th><th>CONFIDENCE</th><th>BOUNDING BOX</th><th>TRACK ID</th></tr></thead><tbody>{objects.map((object, index) => <tr key={`${object.class}-${index}`}><td>{object.class}</td><td>{Math.round(object.confidence * 100)}%</td><td>{object.bbox ? `${Math.round(object.bbox.x1)}, ${Math.round(object.bbox.y1)} – ${Math.round(object.bbox.x2)}, ${Math.round(object.bbox.y2)}` : '—'}</td><td>{object.track_id ?? '—'}</td></tr>)}</tbody></table></div>;
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className={`metric ${tone}`}><small>{label.toUpperCase()}</small><strong>{value}</strong><span>●</span></div>;
}

function Empty({ children }: { children: React.ReactNode }) { return <div className="empty">{children}</div>; }

const queryClient = new QueryClient();
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><App/></QueryClientProvider>);
