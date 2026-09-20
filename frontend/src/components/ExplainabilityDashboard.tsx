import React, { useState } from 'react';
import { DocumentCitationDrawer, type CitationData } from './DocumentCitationDrawer';

// ─── Data ─────────────────────────────────────────────────────────────

const CRITICAL_FACTORS = [
  {
    icon: '🌊',
    label: 'River Level',
    value: '1.90 m',
    detail: '+0.10 m above 1.80 m warning threshold',
    impact: 'HIGH IMPACT',
    impactColor: '#DC2626',
    impactBg: '#FEF2F2',
  },
  {
    icon: '👥',
    label: 'Population Exposure',
    value: '22,400',
    detail: 'Affected Zone A requires evacuation planning',
    impact: 'HIGH IMPACT',
    impactColor: '#DC2626',
    impactBg: '#FEF2F2',
  },
  {
    icon: '🌉',
    label: 'Infrastructure',
    value: 'Sangam Bridge',
    detail: 'Structural crack of 4.8 cm detected by drone',
    impact: 'MED-HIGH IMPACT',
    impactColor: '#D97706',
    impactBg: '#FFFBEB',
  },
  {
    icon: '🏥',
    label: 'Hospital Capacity',
    value: '41 beds',
    detail: 'Emergency surge capacity remains limited at Sassoon General',
    impact: 'MEDIUM IMPACT',
    impactColor: '#D97706',
    impactBg: '#FFFBEB',
  },
];

const EVIDENCE_ITEMS: {
  type: 'DOCUMENT' | 'SENSOR' | 'DRONE';
  icon: string;
  title: string;
  subtitle: string;
  lines: { label: string; value: string; highlight?: boolean }[];
  score?: number;
  live?: boolean;
  citation?: CitationData;
}[] = [
  {
    type: 'DOCUMENT',
    icon: '📄',
    title: 'Flood Response SOP',
    subtitle: 'Rule 4.2 · Page 7',
    lines: [
      { label: 'Source', value: 'NDMA Official SOP 2026' },
      { label: 'Relevance', value: '96% match' },
    ],
    score: 96,
    citation: {
      document: 'Flood Response SOP 2026',
      rule: 'Rule 4.2',
      page: 7,
      section: 'Hospital Surge Capacity & Evacuation Trigger',
      text: 'All hospitals must prepare emergency beds equivalent to 40% of total capacity during flood events. When river water exceeds 1.8 metres, immediate evacuation of low-lying Zone A must begin.',
      highlight: 'When river water exceeds 1.8 metres, immediate evacuation of low-lying Zone A must begin.',
      score: 96,
      retrievedBecause: 'River level = 1.90 m, which exceeds the 1.8 m threshold defined in Rule 4.2.',
      sourceType: 'Official NDMA SOP',
    },
  },
  {
    type: 'DOCUMENT',
    icon: '📄',
    title: 'Disaster Equipment Manual',
    subtitle: 'Section 2.1 · Page 12',
    lines: [
      { label: 'Source', value: 'NDMA Equipment Guidelines' },
      { label: 'Relevance', value: '91% match' },
    ],
    score: 91,
    citation: {
      document: 'Disaster Equipment Manual',
      rule: 'Section 2.1',
      page: 12,
      section: 'Rescue Boat Deployment',
      text: 'Deploy at least 5 rescue boats per affected district and provide life jackets for all response personnel during Level 4 flood alerts.',
      highlight: 'Deploy at least 5 rescue boats per affected district',
      score: 91,
      retrievedBecause: 'Level 4 flood alert active in Pune District.',
      sourceType: 'Official Equipment Manual',
    },
  },
  {
    type: 'SENSOR',
    icon: '📡',
    title: 'Mutha River Sensor',
    subtitle: 'Real-time telemetry · Live',
    lines: [
      { label: 'Current level', value: '1.90 m', highlight: true },
      { label: 'Warning threshold', value: '1.80 m' },
      { label: 'Overflow', value: '+0.10 m above limit', highlight: true },
      { label: 'Timestamp', value: '12:15 IST' },
    ],
    live: true,
  },
  {
    type: 'DRONE',
    icon: '🚁',
    title: 'Drone Observation — Alpha-1',
    subtitle: 'Sangam Bridge · 12:08 IST',
    lines: [
      { label: 'Finding', value: 'Structural crack detected', highlight: true },
      { label: 'Crack width', value: '4.8 cm' },
      { label: 'Access status', value: 'RESTRICTED', highlight: true },
    ],
  },
];

const REASONING_STEPS = [
  { name: 'Planner', desc: 'Identified flood response objective for Pune District' },
  { name: 'Retriever', desc: 'Retrieved 3 relevant SOP sections (96%, 91%, 88%)' },
  { name: 'Reasoner', desc: 'Combined sensor data, infrastructure status, and population exposure' },
  { name: 'Verifier', desc: 'Confirmed recommendation against NDMA SOP Rule 4.2' },
  { name: 'Decision', desc: 'Immediate response recommended — CRITICAL severity' },
];

const KG_NODES = ['Flood', 'River Level', 'Evacuation Zone', 'Rescue Boats', 'Shelter'];

// ─── Sub-components ───────────────────────────────────────────────────

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{
    fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
    letterSpacing: '0.08em', color: 'var(--text-muted)',
    paddingBottom: 8, marginBottom: 16,
    borderBottom: '1px solid var(--border)'
  }}>
    {children}
  </div>
);

// ─── Main Component ───────────────────────────────────────────────────

interface ExplainabilityDashboardProps {
  onViewMap?: () => void;
}

export const ExplainabilityDashboard: React.FC<ExplainabilityDashboardProps> = ({ onViewMap }) => {
  const [openCitation, setOpenCitation] = useState<CitationData | null>(null);
  const [techOpen, setTechOpen] = useState(false);
  const [kgOpen, setKgOpen] = useState(false);

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>

      {/* ══ 1. PAGE HEADER ══════════════════════════════════════════════ */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          AI-supported incident assessment and decision evidence
        </div>
      </div>

      {/* ══ 2. DECISION HEADER CARD ═════════════════════════════════════ */}
      <div style={{
        background: '#FFF', border: '1px solid var(--border)',
        borderLeft: '4px solid #DC2626', borderRadius: 8,
        padding: '18px 20px', marginBottom: 24,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 16
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className="badge badge-critical">CRITICAL</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              INC-2026-PUNE-01
            </span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)', marginBottom: 4 }}>
            Pune District Flood Emergency
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Immediate response recommended · Active since 21:00 IST
          </div>
        </div>

        <div style={{ display: 'flex', gap: 24, textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
              Risk Score
            </div>
            <div style={{ fontSize: 30, fontWeight: 800, color: '#DC2626', lineHeight: 1 }}>87</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>/100</div>
          </div>
          <div style={{ width: 1, background: 'var(--border)' }} />
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
              Evidence Confidence
            </div>
            <div style={{ fontSize: 30, fontWeight: 800, color: '#16A34A', lineHeight: 1 }}>96%</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Grounded</div>
          </div>
        </div>
      </div>

      {/* ══ 3. WHY IS THIS CRITICAL ═════════════════════════════════════ */}
      <div style={{ marginBottom: 28 }}>
        <SectionTitle>Why is this incident critical?</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {CRITICAL_FACTORS.map((f, i) => (
            <div key={i} style={{
              background: '#FFF', border: '1px solid var(--border)',
              borderRadius: 8, padding: '14px 16px',
              display: 'flex', gap: 12, alignItems: 'flex-start'
            }}>
              <div style={{ fontSize: 22, flexShrink: 0, lineHeight: 1 }}>{f.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 2 }}>
                  {f.label}
                </div>
                <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-main)', marginBottom: 4 }}>
                  {f.value}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.4 }}>
                  {f.detail}
                </div>
                <span style={{
                  display: 'inline-block', fontSize: 10, fontWeight: 700,
                  padding: '2px 8px', borderRadius: 20,
                  background: f.impactBg, color: f.impactColor,
                  border: `1px solid ${f.impactColor}22`
                }}>
                  {f.impact}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══ 4. EVIDENCE ═════════════════════════════════════════════════ */}
      <div style={{ marginBottom: 28 }}>
        <SectionTitle>Evidence supporting the decision</SectionTitle>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {EVIDENCE_ITEMS.map((ev, i) => (
            <div key={i} style={{
              background: '#FFF', border: '1px solid var(--border)',
              borderRadius: 8, overflow: 'hidden'
            }}>
              {/* Card header */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px',
                background: 'var(--bg-subtle)',
                borderBottom: '1px solid var(--border)'
              }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <span style={{ fontSize: 18 }}>{ev.icon}</span>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)' }}>
                      {ev.title}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{ev.subtitle}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {ev.live && (
                    <span style={{
                      fontSize: 11, fontWeight: 700, color: '#2563EB',
                      background: '#EFF6FF', padding: '2px 8px',
                      borderRadius: 20, border: '1px solid #BFDBFE'
                    }}>
                      ● LIVE
                    </span>
                  )}
                  {ev.score && (
                    <span style={{
                      fontSize: 12, fontWeight: 700, color: '#16A34A',
                      background: '#F0FDF4', padding: '2px 8px',
                      borderRadius: 20, border: '1px solid #BBF7D0'
                    }}>
                      {ev.score}%
                    </span>
                  )}
                  {/* Source type badge */}
                  <span style={{
                    fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                    color: ev.type === 'DOCUMENT' ? '#D97706' : ev.type === 'SENSOR' ? '#2563EB' : '#7C3AED',
                    background: ev.type === 'DOCUMENT' ? '#FFFBEB' : ev.type === 'SENSOR' ? '#EFF6FF' : '#F5F3FF',
                    padding: '2px 8px', borderRadius: 20,
                    border: `1px solid ${ev.type === 'DOCUMENT' ? '#FDE68A' : ev.type === 'SENSOR' ? '#BFDBFE' : '#DDD6FE'}`
                  }}>
                    {ev.type}
                  </span>
                </div>
              </div>

              {/* Card body */}
              <div style={{
                padding: '12px 16px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 12
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
                  {ev.lines.map((line, li) => (
                    <div key={li} style={{ display: 'flex', gap: 8, alignItems: 'baseline', fontSize: 13 }}>
                      <span style={{ color: 'var(--text-muted)', minWidth: 120 }}>{line.label}</span>
                      <span style={{
                        fontWeight: line.highlight ? 700 : 500,
                        color: line.highlight ? 'var(--text-main)' : 'var(--text-muted)'
                      }}>
                        {line.value}
                      </span>
                    </div>
                  ))}
                </div>

                {ev.citation && (
                  <button
                    onClick={() => setOpenCitation(ev.citation!)}
                    className="btn-ent btn-ent-outline"
                    style={{ fontSize: 12, flexShrink: 0 }}
                  >
                    View Source →
                  </button>
                )}
              </div>

              {/* Document: show quoted text inline */}
              {ev.citation?.text && (
                <div style={{
                  padding: '0 16px 14px',
                  fontSize: 13, color: 'var(--text-main)',
                  fontStyle: 'italic', lineHeight: 1.6
                }}>
                  <div style={{
                    background: '#FFFBEB', border: '1px solid #FDE68A',
                    borderLeft: '3px solid #D97706', borderRadius: 4,
                    padding: '8px 12px'
                  }}>
                    "{ev.citation.highlight || ev.citation.text}"
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ══ 5. AI RECOMMENDATION ════════════════════════════════════════ */}
      <div style={{ marginBottom: 28 }}>
        <SectionTitle>AI recommended response</SectionTitle>
        <div style={{
          background: '#EFF6FF', border: '1px solid #BFDBFE',
          borderLeft: '4px solid #2563EB', borderRadius: 8, padding: '18px 20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#2563EB', marginBottom: 4 }}>
                Recommendation 01 · Priority Critical
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)' }}>
                Deploy 5 rescue boats to Zone A
              </div>
            </div>
            <span className="badge badge-critical">94% CONFIDENCE</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div style={{ background: 'rgba(255,255,255,0.7)', borderRadius: 6, padding: '10px 14px', border: '1px solid #BFDBFE' }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Why</div>
              <div style={{ fontSize: 13, color: 'var(--text-main)', lineHeight: 1.4 }}>
                River level is 0.10 m above the critical threshold and Zone A is under evacuation planning.
              </div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.7)', borderRadius: 6, padding: '10px 14px', border: '1px solid #BFDBFE' }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Evidence</div>
              <div style={{ fontSize: 13, color: 'var(--text-main)' }}>
                Flood Response SOP — Rule 4.2
              </div>
              <button
                onClick={() => setOpenCitation(EVIDENCE_ITEMS[0].citation!)}
                style={{ background: 'none', border: 'none', color: '#2563EB', fontSize: 12, cursor: 'pointer', padding: '4px 0 0', fontWeight: 600 }}
              >
                View source →
              </button>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.7)', borderRadius: 6, padding: '10px 14px', border: '1px solid #BFDBFE' }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Priority</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#DC2626' }}>CRITICAL</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Immediate action</div>
            </div>
          </div>

          <button
            onClick={onViewMap}
            className="btn-ent btn-ent-primary"
            style={{ fontSize: 13 }}
          >
            View on Map →
          </button>
        </div>
      </div>

      {/* ══ 6. REASONING TRACE ══════════════════════════════════════════ */}
      <div style={{ marginBottom: 28 }}>
        <SectionTitle>AI reasoning trace</SectionTitle>
        <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
          {REASONING_STEPS.map((step, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 14,
              padding: '13px 18px',
              borderBottom: i < REASONING_STEPS.length - 1 ? '1px solid var(--border)' : 'none',
              background: i === REASONING_STEPS.length - 1 ? '#F0FDF4' : '#FFF',
            }}>
              <div style={{
                width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                background: '#F0FDF4', border: '2px solid #16A34A',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, color: '#16A34A'
              }}>
                ✓
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-main)', marginBottom: 2 }}>
                  {step.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{step.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══ 7. RELATED KNOWLEDGE (collapsed KG) ════════════════════════ */}
      <div style={{ marginBottom: 28 }}>
        <SectionTitle>Related knowledge</SectionTitle>
        <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, flexWrap: 'wrap' }}>
            {KG_NODES.map((node, i) => (
              <React.Fragment key={i}>
                <span style={{
                  background: 'var(--bg-subtle)', border: '1px solid var(--border)',
                  borderRadius: 6, padding: '5px 12px',
                  fontSize: 12, fontWeight: 500, color: 'var(--text-main)'
                }}>
                  {node}
                </span>
                {i < KG_NODES.length - 1 && (
                  <span style={{ color: 'var(--text-light)', fontWeight: 700, margin: '0 6px', fontSize: 14 }}>→</span>
                )}
              </React.Fragment>
            ))}
          </div>
          {kgOpen && (
            <div style={{ marginTop: 14, padding: 14, background: 'var(--bg-subtle)', borderRadius: 6, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <div><strong style={{ color: 'var(--text-main)' }}>Flood</strong> conditions triggered when Mutha River exceeded 1.8 m threshold.</div>
              <div><strong style={{ color: 'var(--text-main)' }}>River Level</strong> sensor reporting 1.90 m as of 12:15 IST.</div>
              <div><strong style={{ color: 'var(--text-main)' }}>Evacuation Zone</strong> A contains 22,400 residents, per district GIS data.</div>
              <div><strong style={{ color: 'var(--text-main)' }}>Rescue Boats</strong> required: 5 units per SOP Section 2.1.</div>
              <div><strong style={{ color: 'var(--text-main)' }}>Shelter</strong> capacity at District Hall: 2,400 people available.</div>
            </div>
          )}
          <button
            onClick={() => setKgOpen(v => !v)}
            style={{
              background: 'none', border: 'none', color: '#2563EB',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              marginTop: 12, padding: 0
            }}
          >
            {kgOpen ? '▲ Hide details' : '▼ Explore relationships'}
          </button>
        </div>
      </div>

      {/* ══ 8. TECHNICAL DETAILS (collapsed by default) ═════════════════ */}
      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => setTechOpen(v => !v)}
          style={{
            width: '100%', background: '#FFF',
            border: '1px solid var(--border)', borderRadius: 8,
            padding: '12px 18px', cursor: 'pointer', textAlign: 'left',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
          }}
        >
          <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-main)' }}>
            🔧 Technical Details
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {techOpen ? '▲ Hide' : '▼ Show AI system metrics'}
          </span>
        </button>

        {techOpen && (
          <div style={{
            background: '#FFF', border: '1px solid var(--border)',
            borderTop: 'none', borderRadius: '0 0 8px 8px',
            padding: '18px 20px'
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              {/* Retrieval */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
                  Retrieval Quality
                </div>
                {[
                  ['Dense Vector Match', '96%', '#16A34A'],
                  ['Sparse BM25 Match', '81%', '#D97706'],
                  ['Final RRF Score', '92%', '#16A34A'],
                ].map(([label, value, color]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                    <span style={{ fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>{value}</span>
                  </div>
                ))}
              </div>

              {/* Latency */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
                  Processing Latency
                </div>
                {[
                  ['OCR Extraction', '220 ms'],
                  ['Embedding', '50 ms'],
                  ['Retrieval', '32 ms'],
                  ['LLM Generation', '520 ms'],
                  ['Verification', '18 ms'],
                ].map(([label, value]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>{value}</span>
                  </div>
                ))}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, paddingTop: 8, borderTop: '1px solid var(--border)', marginTop: 4 }}>
                  <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>Total End-to-End</span>
                  <span style={{ fontWeight: 800, color: '#2563EB', fontFamily: 'var(--font-mono)' }}>840 ms</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Citation Modal ── */}
      <DocumentCitationDrawer
        citation={openCitation}
        onClose={() => setOpenCitation(null)}
      />
    </div>
  );
};
