import React from 'react';

const CHAIN = [
  { icon: '🛰', label: 'Satellite Ingestion',  detail: 'SAM2 segmentation: 4.2 km² flood zone detected @ 10:02' },
  { icon: '📡', label: 'Sensor Corroboration', detail: 'Mutha gauge: 1.9m > 1.8m threshold — confidence boost +8%' },
  { icon: '📄', label: 'SOP Retrieval',        detail: 'Flood_SOP.txt §3.2: Phase 2 criteria satisfied' },
  { icon: '🧠', label: 'Planner Decision',     detail: 'Orchestrator routes: evacuate + deploy boats' },
  { icon: '✅', label: 'Verification',         detail: 'Hallucination check: PASSED — 0 unsupported claims' },
  { icon: '📋', label: 'Recommendation',       detail: 'Evacuate 8,400 people via Highway 48 using 8 rescue boats' },
];

export const DecisionExplainer: React.FC = () => {
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
