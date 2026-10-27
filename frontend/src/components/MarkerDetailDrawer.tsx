import React from 'react';

export interface MarkerData {
  id: string;
  icon: string;
  label: string;
  type: string;
  status: string;
  statusColor: string;
  confidence: number;
  lat: number;
  lng: number;
  sensorReading?: { value: string; unit: string; trend: string };
  roads?: { name: string; status: string; color: string }[];
  hospitals?: { name: string; distance: string; color: string }[];
  info: string;
  riskParagraph: string;
}

interface MarkerDetailDrawerProps {
  marker: MarkerData | null;
  onClose: () => void;
  onDispatchDrone?: (markerId: string) => void;
  onGenerateReport?: (markerId: string) => void;
}

export const MarkerDetailDrawer: React.FC<MarkerDetailDrawerProps> = ({
  marker,
  onClose,
  onDispatchDrone,
  onGenerateReport,
}) => {
  if (!marker) return null;

  const isCritical =
    marker.status.toLowerCase().includes('critical') ||
    marker.status.toLowerCase().includes('alert');
  const isWarning = marker.status.toLowerCase().includes('risk');

  const statusBadgeClass = isCritical
    ? 'm-status-critical'
    : isWarning
    ? 'm-status-warning'
    : 'm-status-safe';

  return (
    <>
      {/* Dimmed backdrop to close on outside click */}
      <div className="marker-drawer-backdrop" onClick={onClose} />

      {/* Slide-over Right Drawer */}
      <aside className="marker-drawer-panel" aria-label="Asset Details">
        {/* Top Header */}
        <header className="marker-drawer-header">
          <div className="marker-header-top">
            <span className="marker-eyebrow">{marker.type}</span>
            <button
              className="marker-close-btn"
              onClick={onClose}
              title="Close Panel"
            >
              ✕
            </button>
          </div>

          <div className="marker-title-row">
            <span className="marker-main-icon">{marker.icon}</span>
            <div className="marker-title-info">
              <h2 className="marker-name">{marker.label}</h2>
              <p className="marker-coords">
                📍 {marker.lat.toFixed(4)}°N, {marker.lng.toFixed(4)}°E · Zone A
              </p>
            </div>
          </div>
        </header>

        {/* Scrollable Content Body */}
        <div className="marker-drawer-content">
          {/* Status & Confidence Card */}
          <section className="marker-section-card marker-metrics-row">
            <div className="marker-metric-box">
              <span className="marker-card-label">OPERATIONAL STATUS</span>
              <div className={`marker-status-pill ${statusBadgeClass}`}>
                <span className="marker-pulse-dot" />
                <strong>{marker.status}</strong>
              </div>
            </div>

            <div className="marker-metric-box" style={{ textAlign: 'right' }}>
              <span className="marker-card-label">EVIDENCE CONFIDENCE</span>
              <div className="marker-confidence-value">
                {marker.confidence}%
              </div>
              <div className="marker-progress-track">
                <div
                  className="marker-progress-fill"
                  style={{
                    width: `${marker.confidence}%`,
                    background: isCritical
                      ? '#dc2626'
                      : isWarning
                      ? '#d97706'
                      : '#16a34a',
                  }}
                />
              </div>
            </div>
          </section>

          {/* Live Sensor Telemetry (if available) */}
          {marker.sensorReading && (
            <section className="marker-section-card marker-telemetry-card">
              <div className="marker-card-header">
                <span className="marker-card-icon">📡</span>
                <span className="marker-card-title">LIVE SENSOR TELEMETRY</span>
                <span className="marker-live-tag">● LIVE FEED</span>
              </div>

              <div className="marker-telemetry-body">
                <div className="marker-telemetry-val">
                  <span className="telemetry-number">
                    {marker.sensorReading.value}
                  </span>
                  <span className="telemetry-unit">
                    {marker.sensorReading.unit}
                  </span>
                </div>

                <div
                  className={`marker-telemetry-trend ${
                    isCritical
                      ? 'trend-danger'
                      : isWarning
                      ? 'trend-warning'
                      : 'trend-safe'
                  }`}
                >
                  {marker.sensorReading.trend}
                </div>
              </div>
            </section>
          )}

          {/* Current State / Situation */}
          <section className="marker-section-card">
            <div className="marker-card-header">
              <span className="marker-card-icon">📋</span>
              <span className="marker-card-title">CURRENT SITUATION</span>
            </div>
            <p className="marker-info-text">{marker.info}</p>
          </section>

          {/* Connected Roads & Infrastructure */}
          {marker.roads && marker.roads.length > 0 && (
            <section className="marker-section-card">
              <div className="marker-card-header">
                <span className="marker-card-icon">🛣️</span>
                <span className="marker-card-title">CONNECTED ROUTES</span>
              </div>

              <div className="marker-list-group">
                {marker.roads.map((road, idx) => {
                  const isClosed =
                    road.status.includes('CLOSED') ||
                    road.status.includes('BLOCKED') ||
                    road.status.includes('FLOODED');

                  return (
                    <div className="marker-list-item" key={idx}>
                      <span className="marker-item-name">{road.name}</span>
                      <span
                        className={`marker-item-badge ${
                          isClosed ? 'badge-closed' : 'badge-open'
                        }`}
                      >
                        {road.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Nearby Hospitals & Reachability */}
          {marker.hospitals && marker.hospitals.length > 0 && (
            <section className="marker-section-card">
              <div className="marker-card-header">
                <span className="marker-card-icon">🏥</span>
                <span className="marker-card-title">NEARBY MEDICAL CENTERS</span>
              </div>

              <div className="marker-list-group">
                {marker.hospitals.map((hosp, idx) => (
                  <div className="marker-list-item" key={idx}>
                    <span className="marker-item-name">{hosp.name}</span>
                    <span className="marker-distance-pill">
                      {hosp.distance}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* AI Risk Assessment */}
          <section className="marker-section-card marker-risk-card">
            <div className="marker-card-header">
              <span className="marker-card-icon">⚠️</span>
              <span className="marker-card-title" style={{ color: '#b91c1c' }}>
                AI RISK ASSESSMENT & MANDATE
              </span>
            </div>
            <p className="marker-risk-text">{marker.riskParagraph}</p>
          </section>
        </div>

        {/* Footer Actions */}
        <footer className="marker-drawer-footer">
          <button
            type="button"
            className="marker-btn-action marker-btn-report"
            onClick={() => onGenerateReport?.(marker.id)}
          >
            📄 Generate Damage Report
          </button>

          <button
            type="button"
            className="marker-btn-action marker-btn-dispatch"
            onClick={() => onDispatchDrone?.(marker.id)}
          >
            🚁 Dispatch Drone to Location
          </button>
        </footer>
      </aside>
    </>
  );
};
