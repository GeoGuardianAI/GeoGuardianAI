import React from 'react';

export interface CitationData {
  document: string;
  rule?: string;
  page: number;
  section?: string;
  text: string;
  highlight?: string;
  score: number;
  retrievedBecause?: string;
  sourceType?: string;
}

interface DocumentCitationDrawerProps {
  citation: CitationData | null;
  onClose: () => void;
}

export const DocumentCitationDrawer: React.FC<DocumentCitationDrawerProps> = ({ citation, onClose }) => {
  if (!citation) return null;

  const renderHighlighted = (text: string, highlight?: string): React.ReactNode => {
    if (!highlight) return <span>"{text}"</span>;
    const parts = text.split(highlight);
    if (parts.length < 2) return <span>"{text}"</span>;
    return (
      <>
        "{parts[0]}
        <mark style={{ background: '#FEF08A', borderRadius: 2, padding: '0 2px', fontWeight: 700 }}>
          {highlight}
        </mark>
        {parts.slice(1).join(highlight)}"
      </>
    );
  };

  return (
    /* Backdrop */
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'rgba(15,23,42,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      {/* Drawer panel — stop propagation so clicking inside doesn't close */}
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#FFF', borderRadius: 10,
          border: '1px solid var(--border)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.18)',
          width: '100%', maxWidth: 540,
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '14px 20px',
          background: 'var(--bg-subtle)',
          borderBottom: '1px solid var(--border)',
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)' }}>
              📄 {citation.document}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
              Page {citation.page}{citation.section ? ` · ${citation.section}` : ''}{citation.rule ? ` · ${citation.rule}` : ''}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{
              fontSize: 12, fontWeight: 700, color: '#16A34A',
              background: '#F0FDF4', padding: '3px 10px',
              borderRadius: 20, border: '1px solid #BBF7D0'
            }}>
              {citation.score}% match
            </span>
            <button
              onClick={onClose}
              style={{
                background: 'none', border: 'none',
                fontSize: 18, color: 'var(--text-muted)',
                cursor: 'pointer', lineHeight: 1, padding: 0
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Quoted text */}
        <div style={{ padding: '20px 20px 0' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
            Source Text
          </div>
          <div style={{
            background: '#FFFBEB', border: '1px solid #FDE68A',
            borderLeft: '4px solid #D97706', borderRadius: 6,
            padding: '14px 16px', fontSize: 14, lineHeight: 1.7,
            color: 'var(--text-main)', fontStyle: 'italic'
          }}>
            {renderHighlighted(citation.text, citation.highlight)}
          </div>
        </div>

        {/* Retrieved because */}
        {citation.retrievedBecause && (
          <div style={{ padding: '14px 20px 0' }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>
              Retrieved Because
            </div>
            <div style={{
              background: '#EFF6FF', border: '1px solid #BFDBFE',
              borderRadius: 6, padding: '10px 14px',
              fontSize: 13, color: '#1D4ED8'
            }}>
              {citation.retrievedBecause}
            </div>
          </div>
        )}

        {/* Footer meta */}
        <div style={{
          display: 'flex', gap: 20,
          padding: '14px 20px',
          marginTop: 14,
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-subtle)',
          fontSize: 12, color: 'var(--text-muted)'
        }}>
          <div>
            <div style={{ fontSize: 10, textTransform: 'uppercase', fontWeight: 600, marginBottom: 2 }}>Retrieval Score</div>
            <div style={{ fontWeight: 700, color: '#16A34A' }}>{citation.score}%</div>
          </div>
          <div>
            <div style={{ fontSize: 10, textTransform: 'uppercase', fontWeight: 600, marginBottom: 2 }}>Source Type</div>
            <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{citation.sourceType || 'Official SOP'}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, textTransform: 'uppercase', fontWeight: 600, marginBottom: 2 }}>Method</div>
            <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>Hybrid Search (BGE-M3 + BM25)</div>
          </div>
        </div>
      </div>
    </div>
  );
};
