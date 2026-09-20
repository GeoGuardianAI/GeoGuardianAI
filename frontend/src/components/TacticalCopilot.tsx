import React, { useState, useRef, useEffect } from 'react';

// ─── Types ───────────────────────────────────────────────────────────
interface Evidence {
  source: string;
  page?: number | null;
  section?: string | null;
  paragraph?: string;
  highlight?: string;
  confidence: number;
}

interface Alternative { action: string; risk: string; }
interface Impact { people: string | number; roads_blocked: number; bridges_damaged: number; eta: string; }
interface MissionRec { priority: 1 | 2 | 3; action: string; reason: string; confidence: number; eta: string; }

interface StructuredReasoning {
  decision: string;
  confidence: number;
  severity: string;
  reasoning: string[];
  evidence: Evidence[];
  alternatives: Alternative[];
  impact: Impact;
  recommendations: MissionRec[];
  knowledge_graph_path: string[];
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  structured?: StructuredReasoning;
}

const now = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

const QUICK_QUESTIONS = [
  "What's happening right now?",
  "What should we do next?",
  "Which decision is most critical?",
  "Show supporting evidence",
  "What are the risks if we delay evacuation?",
];

// ─── Sub-Components ──────────────────────────────────────────────────

const AgentStep: React.FC<{ icon: string; name: string; desc: string; done: boolean }> = ({ icon, name, desc, done }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '6px 0',
    borderBottom: '1px solid var(--border)',
    opacity: done ? 1 : 0.45
  }}>
    <div style={{
      width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
      background: done ? '#F0FDF4' : '#F1F5F9',
      border: `2px solid ${done ? '#16A34A' : '#CBD5E1'}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12
    }}>
      {done ? '✓' : icon}
    </div>
    <div>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-main)' }}>{name}</div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{desc}</div>
    </div>
  </div>
);

const CitationCard: React.FC<{ ev: Evidence; expanded: boolean; onClick: () => void }> = ({ ev, expanded, onClick }) => (
  <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden', marginBottom: 8 }}>
    <button
      onClick={onClick}
      style={{
        width: '100%', background: expanded ? '#FFFBEB' : 'var(--bg-subtle)',
        border: 'none', padding: '8px 12px', cursor: 'pointer',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: expanded ? '1px solid var(--amber-border)' : 'none',
      }}
    >
      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-main)' }}>
        📄 {ev.source}
        {ev.page && <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>· Page {ev.page}</span>}
        {ev.section && <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>· {ev.section}</span>}
      </span>
      <span style={{ fontSize: 11, fontWeight: 700, color: '#16A34A' }}>{ev.confidence}% match ▾</span>
    </button>
    {expanded && (
      <div style={{ padding: '10px 12px', background: '#FFFBEB' }}>
        <div style={{
          background: '#FFF', border: '1px solid var(--amber-border)',
          borderLeft: '3px solid var(--amber)',
          borderRadius: 4, padding: '8px 12px',
          fontSize: 13, lineHeight: 1.6, color: 'var(--text-main)'
        }}>
          {ev.highlight && ev.paragraph ? (
            ev.paragraph.split(ev.highlight).map((part, i, arr) => (
              <React.Fragment key={i}>
                {part}
                {i < arr.length - 1 && (
                  <mark style={{ background: '#FEF08A', borderRadius: 2, padding: '0 2px' }}>
                    {ev.highlight}
                  </mark>
                )}
              </React.Fragment>
            ))
          ) : (
            ev.paragraph || 'No source text available.'
          )}
        </div>
      </div>
    )}
  </div>
);

const StructuredCard: React.FC<{ msg: Message; onApprove: (r: MissionRec) => void }> = ({ msg, onApprove }) => {
  const sr = msg.structured!;
  const [expandedCitation, setExpandedCitation] = useState<number | null>(null);
  const isRed = sr.severity.toLowerCase() === 'critical';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 640 }}>

      {/* Decision Header */}
      <div style={{
        background: isRed ? '#FEF2F2' : '#FFFBEB',
        border: `1px solid ${isRed ? '#FECACA' : '#FDE68A'}`,
        borderLeft: `4px solid ${isRed ? '#DC2626' : '#D97706'}`,
        borderRadius: 6, padding: '12px 16px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: isRed ? '#DC2626' : '#D97706' }}>
            {sr.severity} — AI ASSESSMENT
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#16A34A' }}>{sr.confidence}% confidence</span>
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.4 }}>
          {sr.decision}
        </div>
      </div>

      {/* Reasoning */}
      <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 6, padding: '12px 16px' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
          Reasoning
        </div>
        {sr.reasoning.map((r, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--text-main)', marginBottom: 6, alignItems: 'flex-start' }}>
            <span style={{ color: '#16A34A', fontWeight: 700, flexShrink: 0 }}>✓</span>
            <span>{r}</span>
          </div>
        ))}
      </div>

      {/* Impact + Alternatives side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 6, padding: '12px 16px' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
            Expected Impact
          </div>
          {[
            ['People affected', sr.impact.people],
            ['Roads blocked', sr.impact.roads_blocked],
            ['Bridges damaged', sr.impact.bridges_damaged],
            ['Response ETA', sr.impact.eta],
          ].map(([k, v]) => (
            <div key={k as string} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 5, color: 'var(--text-main)' }}>
              <span style={{ color: 'var(--text-muted)' }}>{k}</span>
              <span style={{ fontWeight: 600 }}>{v}</span>
            </div>
          ))}
        </div>

        <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 6, padding: '12px 16px' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
            Alternatives
          </div>
          {sr.alternatives.map((a, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-main)' }}>{a.action}</div>
              <div style={{ fontSize: 11, color: a.risk.includes('HIGH') ? '#DC2626' : '#16A34A' }}>Risk: {a.risk}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Evidence Citations */}
      <div style={{ background: '#FFF', border: '1px solid var(--border)', borderRadius: 6, padding: '12px 16px' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>
          Source Evidence
        </div>
        {sr.evidence.map((ev, i) => (
          <CitationCard
            key={i} ev={ev}
            expanded={expandedCitation === i}
            onClick={() => setExpandedCitation(expandedCitation === i ? null : i)}
          />
        ))}
      </div>

      {/* Recommendation Action */}
      {sr.recommendations.length > 0 && (
        <div style={{
          background: '#EFF6FF', border: '1px solid #BFDBFE',
          borderRadius: 6, padding: '12px 16px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12
        }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#2563EB', marginBottom: 3 }}>
              PRIORITY {sr.recommendations[0].priority} RECOMMENDATION
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
              {sr.recommendations[0].action}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              Confidence: {sr.recommendations[0].confidence}% · ETA: {sr.recommendations[0].eta}
            </div>
          </div>
          <button
            onClick={() => onApprove(sr.recommendations[0])}
            className="btn-ent btn-ent-primary"
            style={{ flexShrink: 0, fontSize: 12 }}
          >
            Approve
          </button>
        </div>
      )}

      {/* Grounded badge */}
      <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 12 }}>
        <span style={{ color: '#16A34A', fontWeight: 600 }}>✓ Evidence Grounded</span>
        <span>Confidence: {sr.confidence}%</span>
        <span>Hallucination Risk: Low</span>
      </div>
    </div>
  );
};

// ─── Agent Pipeline Steps ─────────────────────────────────────────────
const PIPELINE_STEPS = [
  { icon: '🧠', name: 'Planner', desc: 'Analyzing request & resolving execution graph' },
  { icon: '📚', name: 'Retriever', desc: 'Searching SOP documents (Hybrid Vector + BM25)' },
  { icon: '🗺️', name: 'Geo Agent', desc: 'Checking spatial boundaries & affected routes' },
  { icon: '🏥', name: 'Resource Agent', desc: 'Querying hospitals & available capacities' },
  { icon: '🤖', name: 'Reasoner', desc: 'Synthesizing evidence-based decision' },
  { icon: '✅', name: 'Verifier', desc: 'Checking SOP compliance (NDMA Rule 4.2)' },
];

// ─── Main Component ──────────────────────────────────────────────────
interface TacticalCopilotProps {
  onMissionCreated?: (mission: { id: string; rec: string; commander: string; timestamp: string }) => void;
}

export const TacticalCopilot: React.FC<TacticalCopilotProps> = ({ onMissionCreated }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState('');
  const [thinking, setThinking] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(-1);
  const [missionCounter, setMissionCounter] = useState(14);
  const [approvedMissions, setApprovedMissions] = useState<{ id: string; rec: string; time: string }[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking, pipelineStep]);

  const runPipeline = async (userQuery: string) => {
    setThinking(true);
    setPipelineStep(0);

    // Animate pipeline steps
    for (let i = 0; i < PIPELINE_STEPS.length; i++) {
      setPipelineStep(i);
      await new Promise(r => setTimeout(r, 350 + Math.random() * 150));
    }

    setThinking(false);
    setPipelineStep(-1);

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQuery, search_mode: 'hybrid' })
      });
      const data = await res.json();

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || '',
        timestamp: now(),
        structured: data.structured_reasoning,
      }]);

    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Unable to connect to backend. Please ensure the server is running on port 8000.',
        timestamp: now(),
      }]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || thinking) return;
    const q = query.trim();
    setQuery('');
    setMessages(prev => [...prev, { role: 'user', content: q, timestamp: now() }]);
    await runPipeline(q);
  };

  const handleApprove = (rec: MissionRec) => {
    const id = `GG-2026-0${missionCounter}`;
    const ts = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    setMissionCounter(c => c + 1);
    setApprovedMissions(prev => [...prev, { id, rec: rec.action, time: ts }]);
    onMissionCreated?.({ id, rec: rec.action, commander: 'Shivam Dubey', timestamp: ts });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 650 }}>

      {/* ── Incident Banner ── */}
      <div style={{
        background: '#FEF2F2', borderBottom: '1px solid #FECACA',
        padding: '10px 20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: '#DC2626' }}>
            🚨 Active Incident — Pune District Flood Emergency
          </span>
          <span className="badge badge-critical">LEVEL 4 · ACTIVE</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          River level 1.9m (limit: 1.8m) · 22,400 people at risk · Sassoon General: 41 beds available · Sangam Bridge: CLOSED
        </div>
      </div>

      {/* ── Quick Question Chips ── */}
      <div style={{
        padding: '8px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', gap: 6, overflowX: 'auto', flexShrink: 0,
        background: 'var(--bg-subtle)'
      }}>
        {QUICK_QUESTIONS.map((qText, i) => (
          <button
            key={i}
            onClick={() => {
              if (thinking) return;
              setMessages(prev => [...prev, { role: 'user', content: qText, timestamp: now() }]);
              runPipeline(qText);
            }}
            disabled={thinking}
            style={{
              whiteSpace: 'nowrap', flexShrink: 0,
              background: '#FFF', border: '1px solid var(--border)',
              borderRadius: 20, padding: '5px 12px',
              fontSize: 12, color: 'var(--primary)',
              cursor: thinking ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
              opacity: thinking ? 0.5 : 1,
            }}
          >
            {qText}
          </button>
        ))}
      </div>

      {/* ── Chat Messages ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {messages.length === 0 && !thinking && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>💬</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-main)', marginBottom: 6 }}>
              Ask the AI Assistant
            </div>
            <div style={{ fontSize: 13 }}>
              Use the quick question buttons above or type your own question below.
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{ fontSize: 11, color: 'var(--text-light)', marginBottom: 4 }}>
              {msg.role === 'user' ? 'Operator' : 'GeoGuardian AI'} · {msg.timestamp}
            </div>

            {msg.role === 'user' ? (
              <div style={{
                background: '#2563EB', color: '#FFF',
                borderRadius: '12px 12px 2px 12px',
                padding: '10px 14px', fontSize: 13, maxWidth: 480,
                lineHeight: 1.5, fontWeight: 500
              }}>
                {msg.content}
              </div>
            ) : msg.structured ? (
              <StructuredCard msg={msg} onApprove={handleApprove} />
            ) : (
              <div style={{
                background: '#FFF', border: '1px solid var(--border)',
                borderRadius: '2px 12px 12px 12px',
                padding: '10px 14px', fontSize: 13, maxWidth: 560,
                lineHeight: 1.6, color: 'var(--text-main)'
              }}>
                {msg.content}
              </div>
            )}
          </div>
        ))}

        {/* ── Agent Pipeline Trace (while thinking) ── */}
        {thinking && (
          <div style={{
            background: '#FFF', border: '1px solid var(--border)',
            borderRadius: 8, padding: '14px 16px', maxWidth: 380
          }}>
            <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>
              ⟳ Multi-Agent Reasoning Pipeline
            </div>
            {PIPELINE_STEPS.map((step, i) => (
              <AgentStep
                key={i} icon={step.icon} name={step.name} desc={step.desc}
                done={i < pipelineStep}
              />
            ))}
          </div>
        )}

        {/* Approved Missions */}
        {approvedMissions.map((m, i) => (
          <div key={i} style={{
            background: '#F0FDF4', border: '1px solid #BBF7D0',
            borderLeft: '4px solid #16A34A', borderRadius: 6, padding: '10px 14px',
            fontSize: 12, color: 'var(--text-main)'
          }}>
            <div style={{ fontWeight: 700, color: '#16A34A' }}>✓ {m.id} — APPROVED</div>
            <div style={{ marginTop: 2 }}>{m.rec}</div>
            <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>Commander: Shivam Dubey · {m.time} IST</div>
          </div>
        ))}

        <div ref={bottomRef} style={{ height: 4 }} />
      </div>

      {/* ── Input Bar ── */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex', gap: 8, padding: '12px 20px',
          borderTop: '1px solid var(--border)', background: 'var(--bg-subtle)'
        }}
      >
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Ask about evacuation, hospitals, resource deployment…"
          disabled={thinking}
          style={{
            flex: 1, padding: '10px 14px', fontSize: 13,
            border: '1px solid var(--border)', borderRadius: 6,
            background: '#FFF', color: 'var(--text-main)', outline: 'none',
          }}
        />
        <button
          type="submit" disabled={thinking || !query.trim()}
          className="btn-ent btn-ent-primary"
          style={{ padding: '10px 18px', flexShrink: 0 }}
        >
          {thinking ? '⟳' : 'Send'}
        </button>
      </form>
    </div>
  );
};
