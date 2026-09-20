import React, { useEffect, useState } from 'react';

interface Stage {
  key: string;
  icon: string;
  label: string;
  detail: string;
  runDetail: string;
}

const STAGES: Stage[] = [
  { key: 'upload',  icon: '📂', label: 'Document Uploaded',      detail: 'Flood_Response_SOP.pdf · 3 pages',  runDetail: 'Reading file…' },
  { key: 'ocr',     icon: '🔎', label: 'Text Extracted',          detail: '3 pages · 1,847 words',             runDetail: 'Extracting text…' },
  { key: 'clean',   icon: '✏️', label: 'Text Cleaned',            detail: 'Headers, footers & noise removed',  runDetail: 'Cleaning…' },
  { key: 'chunk',   icon: '✂️', label: '84 Chunks Created',       detail: 'Avg 220 tokens per chunk',          runDetail: 'Splitting into chunks…' },
  { key: 'embed',   icon: '🧬', label: 'BGE-M3 Embeddings',       detail: '84 vectors · 1024 dimensions',      runDetail: 'Encoding chunks…' },
  { key: 'index',   icon: '💾', label: 'Indexed in Qdrant',       detail: 'Collection: flood_sop · 84 docs',   runDetail: 'Storing in vector DB…' },
  { key: 'search',  icon: '🔍', label: '6 Chunks Retrieved',      detail: 'Hybrid Vector + BM25 search',       runDetail: 'Retrieving relevant chunks…' },
  { key: 'verify',  icon: '✅', label: 'Evidence Verified',        detail: 'Score 95% · 0 hallucinations',     runDetail: 'Cross-checking sources…' },
];

const STAGE_MS = [350, 400, 300, 380, 550, 300, 450, 280];

interface PipelineAnimatorProps {
  isActive?: boolean;
}

export const PipelineAnimator: React.FC<PipelineAnimatorProps> = ({ isActive }) => {
  const [step, setStep]     = useState(-1);
  const [done, setDone]     = useState<Set<number>>(new Set());
  const [running, setRunning] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  const runAnimation = () => {
    if (running) return;
    setRunning(true);
    setDone(new Set());
    setStep(0);
    setShowEvidence(false);

    let i = 0;
    const advance = () => {
      setStep(i);
      setTimeout(() => {
        setDone(prev => new Set([...prev, i]));
        i++;
        if (i < STAGES.length) advance();
        else { setStep(-1); setRunning(false); setShowEvidence(true); }
      }, STAGE_MS[i]);
    };
    advance();
  };

  // Auto-demo on mount, repeat every 25s
  useEffect(() => {
    const t = setTimeout(runAnimation, 300);
    const interval = setInterval(runAnimation, 25000);
    return () => { clearTimeout(t); clearInterval(interval); };
  }, []);

  useEffect(() => {
    if (isActive) runAnimation();
  }, [isActive]);

  const getStatus = (i: number): 'done' | 'active' | 'idle' => {
    if (done.has(i)) return 'done';
    if (step === i)  return 'active';
    return 'idle';
  };

  const EVIDENCE = [
    {
      source: 'Flood_Response_SOP.pdf',
      page: 7,
      section: 'Rule 4.2 — Hospital Surge Capacity',
      score: 96,
      text: 'All hospitals must prepare emergency beds equivalent to 40% of total capacity during flood events.'
    },
    {
      source: 'Flood_Response_SOP.pdf',
      page: 3,
      section: 'Rule 2.1 — Evacuation Trigger',
      score: 91,
      text: 'When river water exceeds 1.8 metres, immediate evacuation of low-lying Zone A must begin.'
    },
    {
      source: 'NDMA_Guidelines_2023.pdf',
      page: 12,
      section: 'Section 6 — Resource Allocation',
      score: 88,
      text: 'Rescue boat deployment ratio: minimum 1 boat per 500 evacuees in Level 4 flood scenarios.'
    },
  ];

  return (
    <div style={{ maxWidth: 740, margin: '0 auto' }}>

      {/* Document info bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'var(--bg-subtle)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '10px 16px', marginBottom: 20
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 22 }}>📄</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)' }}>Flood_Response_SOP.pdf</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>NDMA Standard Operating Procedure · 3 pages · Uploaded 21:30 IST</div>
          </div>
        </div>
        {done.size === STAGES.length && !running && (
          <span className="badge badge-safe">✓ Processing Complete</span>
        )}
        {running && (
          <span className="badge badge-warning">⟳ Processing…</span>
        )}
      </div>

      {/* Pipeline Steps Checklist */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginBottom: 20 }}>
        {STAGES.map((s, i) => {
          const status = getStatus(i);
          return (
            <div key={s.key} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '10px 0', borderBottom: i < STAGES.length - 1 ? '1px solid var(--border)' : 'none' }}>

              {/* Status icon */}
              <div style={{
                width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700,
                background: status === 'done' ? 'var(--green-bg)' : status === 'active' ? '#EFF6FF' : 'var(--bg-subtle)',
                border: `2px solid ${status === 'done' ? 'var(--green)' : status === 'active' ? 'var(--primary)' : 'var(--border)'}`,
                color: status === 'done' ? 'var(--green)' : status === 'active' ? 'var(--primary)' : 'var(--text-light)',
                transition: 'all 0.25s ease',
              }}>
                {status === 'done' ? '✓' : status === 'active' ? (
                  <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
                ) : (i + 1)}
              </div>

              {/* Label + detail */}
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: 14, fontWeight: status === 'idle' ? 400 : 600,
                  color: status === 'idle' ? 'var(--text-light)' : 'var(--text-main)',
                  marginBottom: 2
                }}>
                  {s.label}
                </div>
                <div style={{ fontSize: 12, color: status === 'active' ? 'var(--primary)' : 'var(--text-muted)' }}>
                  {status === 'active' ? s.runDetail : status === 'done' ? s.detail : '—'}
                </div>
              </div>

              {/* Right timing */}
              {status === 'done' && (
                <div style={{ fontSize: 11, color: 'var(--text-light)', fontFamily: 'var(--font-mono)', flexShrink: 0, alignSelf: 'center' }}>
                  {(STAGE_MS[i] / 1000).toFixed(2)}s
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Replay Button */}
      {!running && (
        <button
          onClick={runAnimation}
          className="btn-ent btn-ent-outline"
          style={{ marginBottom: 24, fontSize: 13 }}
        >
          ↺ Replay Pipeline
        </button>
      )}

      {/* Evidence Panel (appears after completion) */}
      {showEvidence && (
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-main)', marginBottom: 12 }}>
            📋 Retrieved Evidence Chunks
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {EVIDENCE.map((ev, idx) => (
              <div key={idx} style={{
                background: '#FFF', border: '1px solid var(--border)',
                borderRadius: 8, overflow: 'hidden'
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 16px', background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border)'
                }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-main)' }}>
                      📄 {ev.source}
                    </span>
                    <span style={{ marginLeft: 10, fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Page {ev.page} · {ev.section}
                    </span>
                  </div>
                  <span style={{
                    fontSize: 12, fontWeight: 700, color: 'var(--green)',
                    background: 'var(--green-bg)', padding: '2px 8px', borderRadius: 12,
                    border: '1px solid var(--green-border)'
                  }}>
                    {ev.score}% match
                  </span>
                </div>
                <div style={{ padding: '12px 16px' }}>
                  <div style={{
                    background: '#FFFBEB', border: '1px solid var(--amber-border)',
                    borderLeft: '4px solid var(--amber)', borderRadius: 4,
                    padding: '10px 14px', fontSize: 13, lineHeight: 1.6, color: 'var(--text-main)'
                  }}>
                    "{ev.text}"
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
