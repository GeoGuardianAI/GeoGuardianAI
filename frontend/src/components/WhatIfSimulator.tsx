import React, { useState } from 'react';

interface WhatIfResult {
  active: boolean;
  rainfall: number;
  riverLevel: number;
  bridgeFail: boolean;
  evacuees: number;
  boats: number;
  hoursUntil: number;
}

interface WhatIfSimulatorProps {
  onSimulate: (result: WhatIfResult) => void;
}

const HORIZONS = ['1h', '2h', '4h', '6h'] as const;
const DENSITIES = ['Low', 'Medium', 'High'] as const;

function compute(
  rainfall: number,
  riverLevel: number,
  wind: number,
  density: string,
  hours: string
): WhatIfResult {
  const densityFactor = density === 'High' ? 3 : density === 'Medium' ? 2 : 1;
  const hFactor = parseInt(hours, 10);
  const risePerHour = rainfall * 0.008 + wind * 0.001;
  const projectedLevel = riverLevel + risePerHour * hFactor;
  const bridgeFail = projectedLevel > 2.5 || wind > 120;
  const basePop = 8000 * densityFactor;
  const evacuees = bridgeFail ? Math.round(basePop * 1.4) : Math.round(basePop * 0.7);
  const boats = Math.max(4, Math.ceil(evacuees / 500));
  return { active: true, rainfall, riverLevel: projectedLevel, bridgeFail, evacuees, boats, hoursUntil: hFactor };
}

function getSeverity(evacuees: number) {
  if (evacuees > 20000) return { label: 'CATASTROPHIC', color: '#DC2626', bg: '#FEF2F2', border: '#FECACA' };
  if (evacuees > 10000) return { label: 'SEVERE',       color: '#D97706', bg: '#FFFBEB', border: '#FDE68A' };
  if (evacuees > 5000)  return { label: 'MODERATE',     color: '#D97706', bg: '#FFFBEB', border: '#FDE68A' };
  return { label: 'MANAGEABLE', color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0' };
}

interface SliderRowProps {
  icon: string;
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  valueColor?: string;
}

const SliderRow: React.FC<SliderRowProps> = ({ icon, label, unit, value, min, max, step = 1, onChange, valueColor }) => (
  <div style={{ marginBottom: 18 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
      <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
        {icon} {label}
      </label>
      <span style={{
        fontSize: 15, fontWeight: 700,
        color: valueColor || 'var(--primary)',
        background: '#EFF6FF', padding: '2px 10px',
        borderRadius: 20, fontFamily: 'var(--font-mono)'
      }}>
        {typeof value === 'number' && step < 1 ? value.toFixed(1) : value} {unit}
      </span>
    </div>
    <input
      type="range" min={min} max={max} step={step} value={value}
      onChange={e => onChange(+e.target.value)}
      style={{
        width: '100%', height: 6, appearance: 'none',
        background: `linear-gradient(to right, var(--primary) 0%, var(--primary) ${((value - min) / (max - min)) * 100}%, #E2E8F0 ${((value - min) / (max - min)) * 100}%, #E2E8F0 100%)`,
        borderRadius: 3, outline: 'none', cursor: 'pointer'
      }}
    />
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-light)', marginTop: 3 }}>
      <span>{min}{unit}</span>
      <span>{max}{unit}</span>
    </div>
  </div>
);

export const WhatIfSimulator: React.FC<WhatIfSimulatorProps> = ({ onSimulate }) => {
  const [rainfall, setRainfall] = useState(60);
  const [river,    setRiver]    = useState(1.9);
  const [wind,     setWind]     = useState(35);
  const [density,  setDensity]  = useState<string>('Medium');
  const [horizon,  setHorizon]  = useState<string>('2h');
  const [result,   setResult]   = useState<WhatIfResult | null>(null);
  const [running,  setRunning]  = useState(false);

  const handleRun = () => {
    setRunning(true);
    setTimeout(() => {
      const r = compute(rainfall, river, wind, density, horizon);
      setResult(r);
      onSimulate(r);
      setRunning(false);
    }, 900);
  };

  const handleClear = () => {
    setResult(null);
    onSimulate({ active: false } as WhatIfResult);
  };

  const sev = result ? getSeverity(result.evacuees) : null;

  return (
    <div>
      {/* Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>

        {/* LEFT: Scenario Inputs */}
        <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)', marginBottom: 16, paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
            ⚙️ Scenario Parameters
          </div>

          <SliderRow
            icon="🌧" label="Rainfall" unit=" mm/hr"
            value={rainfall} min={0} max={120}
            onChange={setRainfall}
            valueColor={rainfall > 80 ? '#DC2626' : rainfall > 50 ? '#D97706' : '#16A34A'}
          />
          <SliderRow
            icon="🌊" label="River Level" unit="m"
            value={river} min={0.5} max={5.0} step={0.1}
            onChange={setRiver}
            valueColor={river > 2.5 ? '#DC2626' : river > 1.8 ? '#D97706' : '#16A34A'}
          />
          <SliderRow
            icon="💨" label="Wind Speed" unit=" km/h"
            value={wind} min={0} max={200}
            onChange={setWind}
            valueColor={wind > 120 ? '#DC2626' : wind > 60 ? '#D97706' : '#16A34A'}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                Population Density
              </label>
              <select
                value={density} onChange={e => setDensity(e.target.value)}
                style={{
                  width: '100%', padding: '8px 10px', fontSize: 13,
                  border: '1px solid var(--border)', borderRadius: 6,
                  background: '#FFF', color: 'var(--text-main)', cursor: 'pointer'
                }}
              >
                {DENSITIES.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                Time Horizon
              </label>
              <select
                value={horizon} onChange={e => setHorizon(e.target.value)}
                style={{
                  width: '100%', padding: '8px 10px', fontSize: 13,
                  border: '1px solid var(--border)', borderRadius: 6,
                  background: '#FFF', color: 'var(--text-main)', cursor: 'pointer'
                }}
              >
                {HORIZONS.map(h => <option key={h}>{h}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={handleRun} disabled={running}
              className="btn-ent btn-ent-primary"
              style={{ flex: 1, justifyContent: 'center' }}
            >
              {running ? '⟳  Simulating…' : '▶  Run Simulation'}
            </button>
            {result && (
              <button onClick={handleClear} className="btn-ent btn-ent-secondary">
                ✕ Clear
              </button>
            )}
          </div>
        </div>

        {/* RIGHT: Current Situation */}
        <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)', marginBottom: 16, paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
            📊 Current Operational Situation
          </div>

          {[
            { label: 'River Level', value: '1.9 m', sub: 'Warning limit: 1.8 m', color: '#DC2626' },
            { label: 'Rainfall Rate', value: '40 mm/hr', sub: 'Heavy rain forecast (3h)', color: '#D97706' },
            { label: 'Population at Risk', value: '22,400', sub: 'Zone A sub-districts', color: '#D97706' },
            { label: 'Rescue Boats Deployed', value: '8 units', sub: '40% capacity available', color: '#16A34A' },
            { label: 'Hospital Capacity', value: '41 beds', sub: 'Sassoon General (free beds)', color: '#16A34A' },
            { label: 'Bridge Status', value: 'CLOSED', sub: 'Sangam Bridge — cracking detected', color: '#DC2626' },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: i < 5 ? '1px solid var(--border)' : 'none' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-main)' }}>{item.label}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.sub}</div>
              </div>
              <div style={{ fontSize: 15, fontWeight: 700, color: item.color, fontFamily: 'var(--font-mono)' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RESULTS CARD — shown after simulation */}
      {result && sev && (
        <div style={{
          background: sev.bg, border: `1px solid ${sev.border}`,
          borderLeft: `4px solid ${sev.color}`,
          borderRadius: 8, padding: 20
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16, color: sev.color }}>
                ⚡ Simulation Result: {sev.label}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                Projected conditions after +{horizon} with {rainfall} mm/hr rainfall
              </div>
            </div>
            <span className="badge" style={{ background: sev.bg, color: sev.color, border: `1px solid ${sev.border}`, fontSize: 13 }}>
              +{horizon} HORIZON
            </span>
          </div>

          {/* Before / After Comparison */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid var(--border)', borderRadius: 6, padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10, fontFamily: 'var(--font-mono)' }}>
                Current State
              </div>
              {[
                ['Risk Score', '87 / 100'],
                ['River Level', '1.9 m'],
                ['Population at Risk', '22,400'],
                ['Rescue Boats', '2 units'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{v}</span>
                </div>
              ))}
            </div>

            <div style={{ background: 'rgba(255,255,255,0.7)', border: `1px solid ${sev.border}`, borderRadius: 6, padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: sev.color, marginBottom: 10, fontFamily: 'var(--font-mono)' }}>
                After +{horizon} Simulation
              </div>
              {[
                ['Risk Score', `94 / 100 (${sev.label})`, sev.color],
                ['River Level', `${result.riverLevel.toFixed(2)} m`, result.riverLevel > 2.5 ? '#DC2626' : '#D97706'],
                ['Population at Risk', result.evacuees.toLocaleString(), '#D97706'],
                ['Rescue Boats Needed', `${result.boats} units`, '#2563EB'],
              ].map(([k, v, c]) => (
                <div key={k as string} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                  <span style={{ fontWeight: 700, color: (c as string) }}>{v}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Why did risk increase + SOP Evidence */}
          <div style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid var(--border)', borderRadius: 6, padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-main)', marginBottom: 8 }}>
              Why did risk increase?
            </div>
            <ol style={{ paddingLeft: 18, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7, margin: '0 0 10px' }}>
              <li>River level projected to rise by +{(result.riverLevel - 1.9).toFixed(2)}m above current 1.9m.</li>
              <li>Rainfall intensity of {rainfall} mm/hr accelerates run-off into Zone A flood plain.</li>
              {result.bridgeFail && <li>Sangam Bridge at risk of closure — escape corridors reduced to 1.</li>}
            </ol>
            <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 4, padding: '8px 12px', fontSize: 12, color: '#92400E' }}>
              <strong>Evidence:</strong> Flood Response SOP — Rule 4.2 · Rule 2.1 · NDMA Guidelines Section 6
              <br/>
              <strong>Recommendation:</strong> Deploy {result.boats} rescue boats and activate {result.evacuees.toLocaleString()} evacuee response protocol immediately.
            </div>
          </div>

        </div>
      )}
    </div>
  );
};
