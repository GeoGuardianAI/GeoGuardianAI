import React, { useState } from 'react';

const AGENTS = [
  { key: 'planner',     label: 'Planner',     icon: '🧠', desc: 'Orchestrates all agent workflows.' },
  { key: 'threat',      label: 'Threat',      icon: '⚠️', desc: 'Evaluates disaster severity index.' },
  { key: 'weather',     label: 'Weather',     icon: '🌧', desc: 'Processes meteorological forecasts.' },
  { key: 'document',    label: 'Document',    icon: '📄', desc: 'Retrieves SOP text and thresholds.' },
  { key: 'retriever',   label: 'Retriever',   icon: '🔍', desc: 'Hybrid vector + keyword search.' },
  { key: 'llm',         label: 'LLM',         icon: '💡', desc: 'Generates grounded response text.' },
  { key: 'verifier',    label: 'Verifier',    icon: '✅', desc: 'Validates groundedness & relevance.' },
  { key: 'report',      label: 'Report',      icon: '📋', desc: 'Compiles tactical dispatch report.' },
];

interface AgentStatusPanelProps {
  agentStates: Record<string, string>;
}

export const AgentStatusPanel: React.FC<AgentStatusPanelProps> = ({ agentStates }) => {
  const [selected, setSelected] = useState<string | null>(null);

  const getClass = (key: string) => {
    const s = agentStates[key];
    if (s === 'thinking') return 'agent-chip thinking';
    if (s === 'done')     return 'agent-chip done';
    if (s === 'error')    return 'agent-chip error';
    return 'agent-chip';
  };

  const getDotClass = (key: string) => {
    const s = agentStates[key];
    if (s === 'thinking') return 'agent-dot dot-think';
    if (s === 'done')     return 'agent-dot dot-done';
    if (s === 'error')    return 'agent-dot dot-error';
    return 'agent-dot dot-idle';
  };

  const getStatusText = (key: string) => {
    const s = agentStates[key];
    if (s === 'thinking') return 'Processing…';
    if (s === 'done')     return 'Complete ✓';
    if (s === 'error')    return 'Error ✗';
    return 'Idle';
  };

  const selectedAgent = AGENTS.find(a => a.key === selected);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="agent-grid">
        {AGENTS.map(a => (
          <div
            key={a.key}
            className={`${getClass(a.key)} ${selected === a.key ? 'active' : ''}`}
            onClick={() => setSelected(selected === a.key ? null : a.key)}
          >
            <div className={getDotClass(a.key)} />
            <span style={{ fontSize: 10, color: 'var(--txt)' }}>{a.icon} {a.label}</span>
          </div>
        ))}
      </div>

      {/* Agent detail card */}
      {selectedAgent && (
        <div style={{
          margin: '0 8px 8px',
          padding: '8px 10px',
          background: 'rgba(14,22,44,0.6)',
          border: '1px solid var(--border)',
          borderRadius: 7,
          animation: 'slide-in 0.2s ease-out',
          fontSize: 10,
          color: 'var(--txt2)'
        }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--cyan)', fontWeight: 700, marginBottom: 4 }}>
            {selectedAgent.icon} {selectedAgent.label.toUpperCase()} AGENT
          </div>
          <div style={{ marginBottom: 3 }}>{selectedAgent.desc}</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: agentStates[selectedAgent.key] === 'done' ? '#30d158' : 'var(--txt3)' }}>
            Status: {getStatusText(selectedAgent.key)}
          </div>
        </div>
      )}
    </div>
  );
};
