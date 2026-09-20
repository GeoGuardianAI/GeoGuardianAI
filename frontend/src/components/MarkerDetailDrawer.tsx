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
  marker, onClose, onDispatchDrone, onGenerateReport
}) => {
  const isOpen = marker !== null;

  return (
    <div className={`marker-drawer ${isOpen ? 'open' : ''}`}>
      {marker && (
        <>
          {/* Header */}
          <div className="marker-drawer-header">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--t3)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                {marker.type}
              </span>
              <button className="drawer-close" onClick={onClose}>✕</button>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 22 }}>{marker.icon}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--t1)' }}>{marker.label}</div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t3)', marginTop: 2 }}>
                  {marker.lat.toFixed(4)}°N, {marker.lng.toFixed(4)}°E
                </div>
              </div>
            </div>
          </div>

          {/* Body */}
          <div className="marker-drawer-body">
            {/* Status + Confidence */}
            <div className="md-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div>
                  <div className="md-label">STATUS</div>
                  <div className="status-badge" style={{ background: `${marker.statusColor}18`, borderColor: `${marker.statusColor}40`, color: marker.statusColor, border: '1px solid' }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: marker.statusColor, flexShrink: 0 }} />
                    {marker.status}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="md-label">CONFIDENCE</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 700, color: marker.statusColor }}>
                    {marker.confidence}%
                  </div>
                </div>
              </div>
              <div className="confidence-track">
                <div className="confidence-fill" style={{ width: `${marker.confidence}%`, background: marker.statusColor }} />
              </div>
            </div>

            {/* Sensor reading */}
            {marker.sensorReading && (
              <div className="md-section">
                <div className="md-label">LIVE SENSOR READING</div>
                <div className="sensor-reading">
                  <span className="sensor-val">{marker.sensorReading.value}</span>
                  <span className="sensor-unit">{marker.sensorReading.unit}</span>
                  <span className="sensor-status" style={{ color: marker.statusColor }}>{marker.sensorReading.trend}</span>
                </div>
              </div>
            )}

            {/* Info */}
            <div className="md-section">
              <div className="md-label">CURRENT STATE</div>
              <div style={{ fontSize: 11, color: 'var(--t2)', lineHeight: 1.5 }}>{marker.info}</div>
            </div>

            {/* Connected roads */}
            {marker.roads && (
              <div className="md-section">
                <div className="md-label">CONNECTED ROADS</div>
                <div className="roads-list">
                  {marker.roads.map((r, i) => (
                    <div key={i} className="road-item">
                      <div className="road-dot" style={{ background: r.color }} />
                      <span>{r.name}</span>
                      <span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 9, color: r.color }}>{r.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Nearby hospitals */}
            {marker.hospitals && (
              <div className="md-section">
                <div className="md-label">NEARBY HOSPITALS</div>
                <div className="hospitals-list">
                  {marker.hospitals.map((h, i) => (
                    <div key={i} className="hosp-item">
                      <div className="hosp-dot" style={{ background: h.color }} />
                      <span>{h.name}</span>
                      <span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t3)' }}>{h.distance}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Risk Paragraph */}
            <div className="md-section">
              <div className="md-label">AI RISK ASSESSMENT</div>
              <div style={{
                fontSize: 10, color: 'var(--t2)', lineHeight: 1.55,
                background: 'rgba(255,59,48,0.04)',
                padding: '8px 10px',
                borderLeft: '2px solid rgba(255,59,48,0.35)',
                borderRadius: '0 6px 6px 0'
              }}>
                {marker.riskParagraph}
              </div>
            </div>

            {/* Actions */}
            <div className="md-actions">
              <button className="btn btn-danger" style={{ fontSize: 11 }} onClick={() => onGenerateReport?.(marker.id)}>
                📋 Generate Damage Report
              </button>
              <button className="btn btn-primary" style={{ fontSize: 11 }} onClick={() => onDispatchDrone?.(marker.id)}>
                🚁 Dispatch Drone to Location
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
