import React, { useEffect, useState } from 'react';

const MODULES = [
  { key: 'flood',    label: 'Flood Detection',     icon: '🛰', baseScore: 94 },
  { key: 'ocr',      label: 'Document OCR',        icon: '📄', baseScore: 89 },
  { key: 'retriever',label: 'RAG Retriever',       icon: '🔍', baseScore: 96 },
  { key: 'llm',      label: 'LLM Response',        icon: '💡', baseScore: 92 },
  { key: 'guardrail',label: 'Guardrails',          icon: '🛡', baseScore: 100 },
];

const getColor = (pct: number) => {
  if (pct >= 90) return '#30d158';
  if (pct >= 70) return '#ffb340';
  return '#ff3b30';
};

export const ConfidencePanel: React.FC = () => {
  const [scores, setScores] = useState(MODULES.map(m => m.baseScore));

  // Slight fluctuation every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setScores(MODULES.map(m => Math.max(70, Math.min(100, m.baseScore + (Math.random() * 4 - 2)))));
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="conf-list">
      {MODULES.map((m, i) => {
        const score = scores[i];
        const color = getColor(score);
        return (
          <div key={m.key} className="conf-row">
            <div className="conf-meta">
              <span className="conf-name">{m.icon} {m.label}</span>
              <span className="conf-pct" style={{ color }}>{score.toFixed(1)}%</span>
            </div>
            <div className="conf-track">
              <div className="conf-fill" style={{ width: `${score}%`, background: color }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};
