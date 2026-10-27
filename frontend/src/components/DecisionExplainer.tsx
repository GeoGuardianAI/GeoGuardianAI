import React from 'react';
import { initialIncidentState } from '../data/incidentState';

export const DecisionExplainer: React.FC = () => {
  const incident = initialIncidentState;
  const riverSensor = incident.sensors.find(sensor => sensor.type === 'Water Level');

  const CHAIN = [
    { icon: '🛰', label: 'Satellite Ingestion',  detail: 'SAM2 segmentation: 4.2 km² flood zone detected @ 10:02' },
    {
      icon: '📡',
      label: 'Sensor Corroboration',
      detail: riverSensor
        ? `${riverSensor.name}: ${incident.riverLevel}m > ${incident.criticalRiverLevel}m threshold — confidence boost +8%`
        : 'Water level sensor data unavailable'
    },
    { icon: '📄', label: 'SOP Retrieval',        detail: 'Flood_SOP.txt §3.2: Phase 2 criteria satisfied' },
    { icon: '🧠', label: 'Planner Decision',     detail: 'Orchestrator routes: evacuate + deploy boats' },
    { icon: '✅', label: 'Verification',         detail: 'Hallucination check: PASSED — 0 unsupported claims' },
    { icon: '📋', label: 'Recommendation',       detail: 'Evacuate 8,400 people via Highway 48 using 8 rescue boats' },
  ];

  return (
    <div className="decision-chain">
      {CHAIN.map((c, i) => (
        <div key={i} className="decision-step">
          <div className="decision-icon">{c.icon}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <div className="decision-label">{c.label}</div>
            <div className="decision-text">{c.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
};