import React, { useState } from 'react';
import { PipelineAnimator } from './PipelineAnimator';
import { WhatIfSimulator } from './WhatIfSimulator';
import { ExplainabilityDashboard } from './ExplainabilityDashboard';

interface WhatIfResult {
  active: boolean;
  rainfall: number;
  riverLevel: number;
  bridgeFail: boolean;
  evacuees: number;
  boats: number;
  hoursUntil: number;
}

interface BottomTabBarProps {
  onSimulate: (result: WhatIfResult) => void;
}

type TabId = 'pipeline' | 'timeline' | 'assets' | 'simulation' | 'reports' | 'xai';

interface TabDef {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: TabDef[] = [
  { id: 'pipeline',   label: 'Pipeline',   icon: '🔄' },
  { id: 'timeline',   label: 'Timeline',   icon: '📜' },
  { id: 'assets',     label: 'Assets',     icon: '🚤' },
  { id: 'simulation', label: 'Simulation', icon: '⚡' },
  { id: 'reports',    label: 'Reports',    icon: '📋' },
  { id: 'xai',        label: 'XAI (Brain)',icon: '🧠' },
];

const RESOURCES = [
  { icon: '🚤', label: 'Rescue Boats', total: 12, available: 8 },
  { icon: '🚑', label: 'Ambulances',   total: 16, available: 10 },
  { icon: '🚁', label: 'Helicopters',  total: 3,  available: 2 },
  { icon: '👨‍⚕️', label: 'Medical Teams',total: 8,  available: 5 },
];

const REPORTS = [
  { id: 'GG-2026-013', status: 'APPROVED', rec: 'Evacuate Zone A — 8 boats deployed', time: '21:42', commander: 'Shivam Dubey' },
  { id: 'GG-2026-012', status: 'COMPLETED', rec: 'Medical teams at Sassoon General', time: '21:31', commander: 'System' },
  { id: 'GG-2026-011', status: 'COMPLETED', rec: 'Sangam Bridge closed, rerouted traffic', time: '21:15', commander: 'Shivam Dubey' },
];

export const BottomTabBar: React.FC<BottomTabBarProps> = ({ onSimulate }) => {
  const [activeTab, setActiveTab] = useState<TabId | null>(null);

  const handleTabClick = (id: TabId) => {
    setActiveTab(prev => prev === id ? null : id);
  };

  return (
    <div className="bottom-zone">
      {/* Tab strip */}
      <div className="tab-strip">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => handleTabClick(t.id)}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', paddingRight: 8 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t3)' }}>
            Click any tab to expand
          </span>
        </div>
      </div>

      {/* Content panel */}
      <div className={`tab-content ${activeTab ? 'open' : ''}`}>
        <div className="tab-inner">

          {/* Pipeline */}
          {activeTab === 'pipeline' && <PipelineAnimator />}

          {/* Timeline */}
          {activeTab === 'timeline' && (
            <div className="timeline-scroll">
              {[
                { time: '10:02', title: 'River exceeded 1.8m threshold', detail: 'Mutha gauge — Sensor', color: '#ff3b30' },
                { time: '10:03', title: 'Satellite flood zone detected', detail: 'SAM2 — 4.2 km² inundated', color: '#ff3b30' },
                { time: '10:05', title: 'Sangam Bridge structural damage', detail: 'Drone Alpha-1 — 4.8cm crack', color: '#ff3b30' },
                { time: '10:06', title: 'AI recommended evacuation', detail: 'Planner Agent — Phase 2', color: '#30d158' },
                { time: '10:07', title: 'Report #GG-2026-013 generated', detail: 'Report Agent — Auto', color: '#00e1ff' },
                { time: '10:08', title: 'Rescue Team A dispatched', detail: '8 boats — Highway 48', color: '#30d158' },
                { time: '10:12', title: 'IMD weather alert: 45mm/hr incoming', detail: 'Weather API — +3h', color: '#ffb340' },
                { time: '10:15', title: 'Noble Hospital at risk — relocation active', detail: '92% capacity', color: '#ffb340' },
                { time: '10:22', title: 'Sports Complex shelter activated', detail: '62 occupants — 120 beds', color: '#30d158' },
                { time: '10:30', title: 'Drone Alpha-1 — video feed live', detail: 'Bridge + flood zone', color: '#bf5af2' },
              ].map((ev, i) => (
                <div key={i} className="tl-row">
                  <span className="tl-time">{ev.time}</span>
                  <div className="tl-dot" style={{ background: ev.color }} />
                  <div>
                    <div className="tl-text">{ev.title}</div>
                    <div className="tl-sub">{ev.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Assets */}
          {activeTab === 'assets' && (
            <div className="assets-tab-inner">
              <div className="assets-grid">
                {RESOURCES.map(r => {
                  const busy = r.total - r.available;
                  const pct  = (r.available / r.total) * 100;
                  return (
                    <div key={r.label} className="asset-cell">
                      <span className="asset-icon">{r.icon}</span>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                          <span className="asset-count">{r.available}</span>
                          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--t3)' }}>/{r.total}</span>
                        </div>
                        <div className="asset-label">{r.label}</div>
                        <div className="asset-sub">
                          <span className="asset-avail">✓ {r.available} avail</span>
                          {'  '}
                          <span className="asset-busy">⊙ {busy} active</span>
                        </div>
                        <div style={{ height: 2, background: 'rgba(255,255,255,0.07)', borderRadius: 1, marginTop: 5, overflow: 'hidden', width: 80 }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: pct > 50 ? '#30d158' : pct > 25 ? '#ffb340' : '#ff3b30', borderRadius: 1 }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="ai-deploy-suggestion">
                <div className="deploy-title">🤖 AI DEPLOYMENT SUGGESTION</div>
                <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--t3)', marginBottom: 6 }}>
                  Grounded on live telemetry + Flood SOP Rule 4.2
                </div>
                {[
                  { n: '2', asset: 'Rescue Boats', dest: 'Mutha River crossing', reason: '22,400 population at risk + water level 1.9m + 2 sub-zones', conf: 94 },
                  { n: '1', asset: 'Helicopter',   dest: 'Aerial recon — flood zone', reason: 'Sangam Bridge 4.8cm structural crack + aerial survey', conf: 92 },
                  { n: '3', asset: 'Ambulances',   dest: 'Sports Complex shelter', reason: 'Predicted evacuation load + medical surge capacity', conf: 89 },
                  { n: '2', asset: 'Medical Teams',dest: 'Sassoon General Hospital', reason: 'Trauma team pre-positioning under Rule 4.2 (40% surge beds)', conf: 96 },
                ].map((d, i) => (
                  <div key={i} className="deploy-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 2, marginBottom: 8, padding: 6, background: 'rgba(255,255,255,0.02)', borderRadius: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%' }}>
                      <span className="deploy-num" style={{ color: 'var(--cyan)', fontWeight: 700 }}>{d.n}×</span>
                      <strong style={{ fontSize: 11 }}>{d.asset}</strong>
                      <span style={{ fontSize: 9, color: 'var(--t3)', fontFamily: 'var(--mono)', marginLeft: 'auto' }}>→ {d.dest}</span>
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--t2)', paddingLeft: 18 }}>
                      <strong>Reason:</strong> {d.reason}
                    </div>
                    <div style={{ fontSize: 8, color: 'var(--green)', fontFamily: 'var(--mono)', paddingLeft: 18 }}>
                      Confidence: {d.conf}%
                    </div>
                  </div>
                ))}
                <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                  <button
                    className="btn btn-primary"
                    style={{ flex: 1, fontSize: 10 }}
                    onClick={() => alert("DEPLOYMENT PLAN GENERATED:\n• 2× Rescue Boats\n• 1× Helicopter\n• 3× Ambulances\n• 2× Medical Teams\n\nSTATUS: READY FOR COMMANDER AUTHORIZATION")}
                  >
                    Generate Deployment Plan
                  </button>
                  <button className="btn btn-ghost" style={{ flex: 1, fontSize: 10 }}>Confirm Simulation</button>
                </div>
              </div>
            </div>
          )}

          {/* Simulation */}
          {activeTab === 'simulation' && (
            <div style={{ height: '100%', overflow: 'auto' }}>
              <WhatIfSimulator onSimulate={onSimulate} />
            </div>
          )}

          {/* Reports */}
          {activeTab === 'reports' && (
            <div className="timeline-scroll">
              {REPORTS.map(r => (
                <div
                  key={r.id}
                  className="tl-row"
                  style={{ alignItems: 'center', gap: 14, cursor: 'pointer' }}
                  onClick={() => alert(`REPORT AUDIT DETAILS: ${r.id}\n────────────────────────────────\nRecommendation: ${r.rec}\nStatus: ${r.status}\nCommander: ${r.commander}\nTime: ${r.time} IST\n\nAI REASONING PARAMETERS:\n• River level: 1.9m (Limit: 1.8m)\n• Population at risk: 22,400\n• Affected roads: 2\n• Supporting SOP: Flood Response SOP — Rule 4.2 [SOP-001:p7:c03]\n• Recommendation Confidence: 94%\n• Grounded Verification: PASSED`)}
                >
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--cyan)', fontWeight: 700 }}>{r.id}</span>
                  <div style={{ flex: 1 }}>
                    <div className="tl-text">{r.rec}</div>
                    <div className="tl-sub">Commander: {r.commander} · {r.time} IST · <span style={{ color: 'var(--cyan)' }}>[Click for AI Evidence]</span></div>
                  </div>
                  <span style={{
                    fontFamily: 'var(--mono)', fontSize: 9, fontWeight: 700,
                    color: r.status === 'APPROVED' ? '#30d158' : '#00e1ff',
                    background: r.status === 'APPROVED' ? 'rgba(48,209,88,0.1)' : 'rgba(0,225,255,0.1)',
                    padding: '2px 8px', borderRadius: 10,
                    border: `1px solid ${r.status === 'APPROVED' ? 'rgba(48,209,88,0.3)' : 'rgba(0,225,255,0.3)'}`
                  }}>
                    {r.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* XAI (Explainability) */}
          {activeTab === 'xai' && (
            <ExplainabilityDashboard />
          )}

        </div>
      </div>
    </div>
  );
};
