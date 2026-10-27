import React, { useState, useCallback, useEffect } from 'react';
import './index.css';
import { TacticalMap } from './components/TacticalMap';
import { TacticalCopilot } from './components/TacticalCopilot';
import { MarkerDetailDrawer, type MarkerData } from './components/MarkerDetailDrawer';
import { WhatIfSimulator } from './components/WhatIfSimulator';
import { ExplainabilityDashboard } from './components/ExplainabilityDashboard';
import { PipelineAnimator } from './components/PipelineAnimator';
import { ResourceManagement } from './components/ResourceManagement';
import { initialIncidentState, type IncidentState } from './data/incidentState';

interface WhatIfResult {
  active: boolean;
  rainfall: number;
  riverLevel: number;
  bridgeFail: boolean;
  evacuees: number;
  boats: number;
  hoursUntil: number;
}

const LiveClock: React.FC = () => {
  const [t, setT] = useState(new Date());
  useEffect(() => { const iv = setInterval(() => setT(new Date()), 1000); return () => clearInterval(iv); }, []);
  return <span>{t.toLocaleTimeString('en-GB')}</span>;
};

const REPORTS = [
  { id: 'GG-2026-013', rec: 'Evacuate Zone A — 8 boats deployed', commander: 'Shivam Dubey', time: '21:42', status: 'APPROVED' },
  { id: 'GG-2026-012', rec: 'Medical response teams at Sassoon General', commander: 'Priya Sharma', time: '21:31', status: 'COMPLETED' },
  { id: 'GG-2026-011', rec: 'Sangam Bridge closed, rerouted traffic via NH-48', commander: 'Amit Verma', time: '21:15', status: 'COMPLETED' },
];

export default function App() {
  const [incident, setIncident] = useState<IncidentState>(initialIncidentState);
  const riverExcess = Number((incident.riverLevel - incident.criticalRiverLevel).toFixed(2));
  const bridge = incident.infrastructure.find(item => item.type === 'Bridge');
  const [activeNav, setActiveNav] = useState<'dashboard' | 'map' | 'simulation' | 'resources' | 'documents' | 'assistant' | 'reports' | 'evidence'>('dashboard');
  const [markerData, setMarkerData] = useState<MarkerData | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null);

  const handleMarkerClick = useCallback((m: MarkerData) => {
    setMarkerData(m);
  }, []);

  const handleSimulate = useCallback((result: WhatIfResult) => {
    setWhatIfResult(result.active ? result : null);
    if (result.active) {
      setIncident(prev => {
        const excess = result.riverLevel - prev.criticalRiverLevel;
        const newRisk = Math.min(99, Math.max(20, Math.round(50 + excess * 30 + (result.rainfall / 100) * 20)));
        const newSeverity = result.riverLevel >= 2.0 || result.bridgeFail ? 'CRITICAL' : (result.riverLevel >= prev.criticalRiverLevel ? 'HIGH' : 'MODERATE');
        return {
          ...prev,
          riverLevel: Number(result.riverLevel.toFixed(2)),
          rainfall: result.rainfall,
          populationAtRisk: result.evacuees,
          riskScore: newRisk,
          severity: newSeverity,
          simulationActive: true,
          assets: {
            ...prev.assets,
            rescueBoats: {
              ...prev.assets.rescueBoats,
              required: result.boats,
              available: Math.max(0, prev.assets.rescueBoats.total - result.boats),
            }
          },
          infrastructure: prev.infrastructure.map(inf => {
            if (inf.type === 'Bridge') {
              return {
                ...inf,
                status: result.bridgeFail ? 'COLLAPSED' : (result.riverLevel >= 1.8 ? 'CRITICAL' : 'OPERATIONAL'),
                description: result.bridgeFail ? 'Bridge structurally compromised. Complete traffic closure.' : inf.description
              };
            }
            return inf;
          }),
          sensors: prev.sensors.map(s => {
            if (s.type === 'Water Level') {
              return {
                ...s,
                value: Number(result.riverLevel.toFixed(2)),
                status: result.riverLevel >= s.criticalValue ? 'CRITICAL' : 'NORMAL'
              };
            }
            return s;
          })
        };
      });
    } else {
      setIncident(initialIncidentState);
    }
  }, []);

  return (
    <div className="enterprise-shell">

      {/* ═══════════════════════════════════════════
          HEADER & TOP NAVIGATION
      ═══════════════════════════════════════════ */}
      <header className="top-nav-header">
        <div className="header-top-row">
          <div className="brand-title">
            <span>🛡</span> GeoGuardian AI
            <span className="brand-sub">Disaster Response & Infrastructure Intelligence</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div className="location-tag">
              <span>📍</span> {incident.location} District, Maharashtra
            </div>
            <div style={{ fontSize: 12, color: '#94A3B8', fontFamily: 'var(--font-mono)' }}>
              <LiveClock /> IST
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="top-nav-tabs">
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'map', label: 'Live Map' },
            { id: 'simulation', label: 'Incidents & Simulation' },
            { id: 'resources', label: 'Resources' },
            { id: 'documents', label: 'Documents & Processing' },
            { id: 'assistant', label: 'AI Assistant' },
            { id: 'reports', label: 'Reports' },
            { id: 'evidence', label: 'Assessment & Evidence' }
          ].map(tab => (
            <button
              key={tab.id}
              className={`nav-tab-btn ${activeNav === tab.id ? 'active' : ''}`}
              onClick={() => setActiveNav(tab.id as any)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* ═══════════════════════════════════════════
          SCROLLABLE PAGE CONTENT
      ═══════════════════════════════════════════ */}
      <main className="page-content-container">

        {/* ── 1. DASHBOARD VIEW ───────────────────────────────── */}
        {activeNav === 'dashboard' && (
          <>
            {/* Active Incident Banner */}
            <div className="ent-card" style={{ borderLeft: '4px solid var(--red)', background: '#FFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="badge badge-critical">LEVEL 4 FLOOD · ACTIVE</span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Incident ID: {incident.incidentId}</span>
                  </div>
                  <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)' }}>{incident.location} District {incident.disasterType} Emergency</h2>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>OVERALL RISK SCORE</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--red)' }}>{incident.riskScore} / 100</div>
                </div>
              </div>
            </div>

            {/* Current Situation Metrics Grid */}
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-card-label">🌊 River Water Level</div>
                <div className="metric-card-value" style={{ color: 'var(--red)' }}>
                  {incident.riverLevel} m
                </div>
                <div className="metric-card-sub">Warning Limit: {incident.criticalRiverLevel} m (+{riverExcess}m overflow)</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-label">🌧 Precipitation Rate</div>
                <div className="metric-card-value" style={{ color: 'var(--amber)' }}>{incident.rainfall} mm/hr</div>
                <div className="metric-card-sub">Forecast: Heavy rain next 3 hours</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-label">👥 Population Exposure</div>
                <div className="metric-card-value" style={{ color: 'var(--amber)' }}>{incident.populationAtRisk.toLocaleString()}</div>
                <div className="metric-card-sub">Inundated Zone A sub-districts</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-label">🚤 Active Rescue Units</div>
                <div className="metric-card-value" style={{ color: 'var(--green)' }}>{incident.assets.rescueBoats.available} Boats</div>
                <div className="metric-card-sub">40% capacity available for dispatch</div>
              </div>
            </div>

            {/* Live Disaster Map Hero */}
            <div className="ent-card" style={{ height: 440, padding: 0, overflow: 'hidden', position: 'relative' }}>
              <div style={{ padding: '12px 16px', background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: 14 }}>📍 Live Disaster Map</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Click markers for operational hospital & bridge status</span>
              </div>
              <div style={{ height: 390 }}>
                <TacticalMap
                  incident={incident}
                  whatIfResult={whatIfResult}
                  onMarkerClick={handleMarkerClick}
                  showHeatmap={true}
                />
              </div>
            </div>

            {/* Situation Assessment & Recommendations */}
            <div className="ent-card">
              <div className="ent-card-title">
                <span>📋 Operational Situation Assessment</span>
                <span className="badge badge-info">
                  EVIDENCE GROUNDED {incident.groundedScore}%
                </span>
              </div>
              <p style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: 16 }}>
                Flood risk remains critical because the river level of {incident.riverLevel}m exceeds the defined {incident.criticalRiverLevel}m threshold.
                {bridge?.name} road access is blocked due to drone-detected structural cracking ({bridge?.sensorReading?.value}{bridge?.sensorReading?.unit}).
                Trauma response capacity at {incident.hospitals[0].name} remains healthy with{' '}
                {incident.hospitals[0].availableBeds} available beds.
              </p>

              <div style={{ background: 'var(--primary-subtle)', border: '1px solid #BFDBFE', padding: 14, borderRadius: 6, marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: 'var(--primary)', fontSize: 13, marginBottom: 4 }}>
                  Recommended Action Plan:
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-main)' }}>
                  • Prepare Phase 1 evacuation resources in Zone A.<br/>
                  • Lock surge bed capacity at {incident.hospitals[0].name} under NDMA SOP Rule 4.2.<br/>
                  • Dispatch {incident.assets.rescueBoats.required} rescue boats to affected flood zones.
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12 }}>
                <button className="btn-ent btn-ent-primary" onClick={() => setActiveNav('evidence')}>
                  View Supporting Evidence
                </button>
                <button className="btn-ent btn-ent-secondary" onClick={() => setActiveNav('assistant')}>
                  Open AI Assistant
                </button>
              </div>
            </div>

            {/* Recent Reports Table */}
            <div className="ent-card">
              <div className="ent-card-title">
                <span>📄 Recent Incident Reports</span>
                <button className="btn-ent btn-ent-outline" style={{ fontSize: 12 }} onClick={() => setActiveNav('reports')}>
                  View All Reports
                </button>
              </div>
              <table className="ent-table">
                <thead>
                  <tr>
                    <th>Report ID</th>
                    <th>Action Summary</th>
                    <th>Commander</th>
                    <th>Timestamp</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {REPORTS.map(r => (
                    <tr key={r.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{r.id}</td>
                      <td>{r.rec}</td>
                      <td>{r.commander}</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{r.time} IST</td>
                      <td>
                        <span className={`badge ${r.status === 'APPROVED' ? 'badge-safe' : 'badge-info'}`}>
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* ── 2. LIVE MAP VIEW ───────────────────────────────── */}
        {activeNav === 'map' && (
          <div className="ent-card" style={{ height: 700, padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '12px 20px', background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>🗺 Fullscreen GIS Emergency Disaster Map</span>
              <span className="badge badge-safe">LIVE SENSOR TELEMETRY</span>
            </div>
            <div style={{ height: 645, position: 'relative' }}>
              <TacticalMap
                incident={incident}
                whatIfResult={whatIfResult}
                onMarkerClick={handleMarkerClick}
                showHeatmap={true}
              />
            </div>
          </div>
        )}

        {/* ── 3. INCIDENTS & SIMULATION VIEW ──────────────────── */}
        {activeNav === 'simulation' && (
          <div className="ent-card">
            <div className="ent-card-title">
              <span>⚡ Scenario Simulation & What-If Analysis</span>
              <span className="badge badge-info">PREDICTIVE MODELLING</span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
              Adjust environmental parameters below to model flood progression over time and evaluate resource demand changes.
            </p>
            <WhatIfSimulator incident={incident} onSimulate={handleSimulate} />
          </div>
        )}

        {/* ── 4. RESOURCES VIEW ──────────────────────────────── */}
        {activeNav === 'resources' && (
          <div className="ent-card">
            <div className="ent-card-title">
              <span>🚑 Emergency Resources & Deployment Recommendations</span>
            </div>
            <ResourceManagement incident={incident} />
          </div>
        )}

        {/* ── 5. DOCUMENTS & PROCESSING VIEW ────────────────── */}
        {activeNav === 'documents' && (
          <div className="ent-card">
            <div className="ent-card-title">
              <span>📚 Document Ingestion & RAG AI Processing Pipeline</span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
              Visual audit trace of disaster standard operating procedures ingestion, vector storage, and evidence retrieval.
            </p>
            <PipelineAnimator />
          </div>
        )}

        {/* ── 6. ASSISTANT VIEW ───────────────────────────────── */}
        {activeNav === 'assistant' && (
          <div className="ent-card" style={{ minHeight: 650, padding: 0, overflow: 'hidden' }}>
            <TacticalCopilot incident={incident} />
          </div>
        )}

        {/* ── 7. REPORTS VIEW ─────────────────────────────────── */}
        {activeNav === 'reports' && (
          <div className="ent-card">
            <div className="ent-card-title">
              <span>📄 Official Disaster Incident Reports</span>
            </div>
            <table className="ent-table">
              <thead>
                <tr>
                  <th>Report ID</th>
                  <th>Action Summary</th>
                  <th>Commander</th>
                  <th>Timestamp</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {REPORTS.map(r => (
                  <tr
                    key={r.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => alert(`REPORT AUDIT DETAILS: ${r.id}
────────────────────────────────
Recommendation: ${r.rec}
Status: ${r.status}
Commander: ${r.commander}
Time: ${r.time} IST

REASONING PARAMETERS:
• River level: ${incident.riverLevel}m (Limit: ${incident.criticalRiverLevel}m)
• Population at risk: ${incident.populationAtRisk.toLocaleString()}
• Affected roads: ${incident.infrastructure.filter(item => item.type === 'Road').length}
• Supporting SOP: Flood Response SOP — Rule 4.2
• Confidence: ${incident.aiAssessment.confidence}%`)}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{r.id}</td>
                    <td>{r.rec}</td>
                    <td>{r.commander}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{r.time} IST</td>
                    <td>
                      <span className={`badge ${r.status === 'APPROVED' ? 'badge-safe' : 'badge-info'}`}>
                        {r.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── 8. ASSESSMENT & EVIDENCE VIEW ───────────────────── */}
        {activeNav === 'evidence' && (
          <div className="ent-card">
            <ExplainabilityDashboard onViewMap={() => setActiveNav('map')} incident={incident} />
          </div>
        )}

      </main>

      {/* Marker Detail Drawer */}
      <MarkerDetailDrawer
        marker={markerData}
        onClose={() => setMarkerData(null)}
        onDispatchDrone={() => {
          setMarkerData(null);
          setActiveNav('assistant');
        }}
        onGenerateReport={() => {
          setMarkerData(null);
          setActiveNav('reports');
        }}
      />
    </div>
  );
}
