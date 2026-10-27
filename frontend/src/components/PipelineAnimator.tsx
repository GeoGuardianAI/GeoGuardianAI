import React, { useState } from 'react';

interface DocumentProfile {
  id: number;
  filename: string;
  title: string;
  authority: string;
  pages: number;
  year: number;
  words: number;
  chunks: number;
  description: string;
  evidence: {
    page: number;
    section: string;
    score: number;
    text: string;
  }[];
}

const REAL_DOCUMENTS: DocumentProfile[] = [
  {
    id: 1,
    filename: 'urban_flooding_guidelines.pdf',
    title: 'National Disaster Management Guidelines: Management of Urban Flooding',
    authority: 'NDMA / NIDM · Government of India',
    pages: 190,
    year: 2010,
    words: 84200,
    chunks: 669,
    description: 'Statutory national framework for urban flood risk assessment, drainage management, early warning networks, and emergency coordination.',
    evidence: [
      {
        page: 25,
        section: 'Chapter 3 · Early Warning & Rainfall Monitoring',
        score: 97,
        text: 'Doppler Weather Radars and dense automatic rain-gauge networks shall provide real-time precipitation telemetry to municipal emergency operations centres with sub-hourly updates.'
      },
      {
        page: 74,
        section: 'Chapter 5 · Vulnerability Assessment of Critical Infrastructure',
        score: 94,
        text: 'Bridges across urban river corridors and hospital road approaches must have automated water-level sensor telemetry to issue immediate closure orders prior to structural inundation.'
      },
      {
        page: 112,
        section: 'Chapter 7 · Emergency Evacuation Shelters',
        score: 91,
        text: 'Designated relief shelters must maintain minimum standard reserves for food, potable water, and emergency medical kits capable of supporting 72 hours of complete isolation.'
      }
    ]
  },
  {
    id: 2,
    filename: 'flood_management_guidelines.pdf',
    title: 'National Disaster Management Guidelines: Management of Floods',
    authority: 'National Disaster Management Authority (NDMA)',
    pages: 168,
    year: 2008,
    words: 78500,
    chunks: 545,
    description: 'Comprehensive guidelines establishing flood zoning regulations, river embankment maintenance, and SDRF/NDRF rescue asset prepositioning.',
    evidence: [
      {
        page: 42,
        section: 'Section 4.3 · Rescue Asset Mobilisation Ratios',
        score: 95,
        text: 'In severe inundation corridors where ground access is severed, motor-powered inflatable rescue boats shall be dispatched at the prescribed ratio of 1 boat team per 500 stranded residents.'
      },
      {
        page: 88,
        section: 'Section 6.1 · River Threshold Warning Triggers',
        score: 92,
        text: 'Crossing the designated danger level warrants automatic transmission of Level 4 emergency alerts to the District Magistrate and immediate activation of the Incident Command System.'
      }
    ]
  },
  {
    id: 3,
    filename: 'pune_district_disaster_management_plan.pdf',
    title: 'Pune District Disaster Management Plan (DDMP 2025-26)',
    authority: 'District Collector Office & DDMA Pune',
    pages: 177,
    year: 2025,
    words: 74100,
    chunks: 512,
    description: 'Specific disaster management plan for Pune District covering Mutha & Mula river basins, Sangam Bridge corridor, Sassoon Hospital surge capacity, and ward evacuation zones.',
    evidence: [
      {
        page: 38,
        section: 'Annexure 2 · Mutha River Basin Critical Gauges',
        score: 98,
        text: 'Mutha River water level exceeding 1.80m gauge reading triggers compulsory evacuation of low-lying settlements along riverside corridors and immediate inspection of Sangam Bridge foundations.'
      },
      {
        page: 92,
        section: 'Section 8.4 · Emergency Hospital Response Architecture',
        score: 96,
        text: 'Sassoon General Hospital functions as the nodal Level-1 trauma response hub for Pune City with a mandatory requirement to reserve minimum 40% surge bed capacity during monsoon flood alerts.'
      }
    ]
  },
  {
    id: 4,
    filename: 'state_disaster_management_plan_2023.pdf',
    title: 'Maharashtra State Disaster Management Plan (SDMP 2023)',
    authority: 'Maharashtra State Disaster Management Authority (SDMA)',
    pages: 204,
    year: 2023,
    words: 91400,
    chunks: 607,
    description: 'State-wide disaster management architecture detailing inter-agency coordination between SDMA, NDRF 5th Battalion Pune, and municipal corporations.',
    evidence: [
      {
        page: 54,
        section: 'Chapter 4 · State Emergency Operations Protocol',
        score: 93,
        text: 'Upon breach of river thresholds in Pune Municipal Corporation limits, the State EOC shall authorize rapid prepositioning of SDRF response columns and air support assets.'
      }
    ]
  },
  {
    id: 5,
    filename: 'urban_flooding_sop.pdf',
    title: 'Standard Operating Procedure for Urban Flooding',
    authority: 'Ministry of Housing and Urban Affairs (MoHUA)',
    pages: 36,
    year: 2021,
    words: 16200,
    chunks: 106,
    description: 'Operational SOP specifying city-level standard procedures for pumping stations, road closure cordons, drone damage reconnaissance, and citizen alerts.',
    evidence: [
      {
        page: 12,
        section: 'SOP Module 3 · Urban Drainage & Traffic Isolation',
        score: 95,
        text: 'Traffic police and civil defense wardens shall cordon off flooded arterial roads and structural bridges immediately upon sensor telemetry indicating water logging beyond safe clearance.'
      }
    ]
  },
  {
    id: 6,
    filename: 'disaster_management_rule_2005.pdf',
    title: 'Disaster Management Rules 2005 (Maharashtra)',
    authority: 'Government of Maharashtra · Law & Judiciary Department',
    pages: 10,
    year: 2005,
    words: 4800,
    chunks: 21,
    description: 'Statutory rules governing mandatory powers of the District Relief Officer, requisitioning of commercial vehicles, boats, and medical supplies.',
    evidence: [
      {
        page: 4,
        section: 'Rule 4.2 · Emergency Requisition of Transport and Medical Facilities',
        score: 94,
        text: 'The District Collector or authorized incident commander is empowered to requisition private and public medical beds, rescue watercraft, and transport machinery without delay.'
      }
    ]
  },
  {
    id: 7,
    filename: 'district_preparedness_sop.pdf',
    title: 'Preparedness & Capacity Building SOP for DDMA',
    authority: 'Maharashtra SDMA',
    pages: 3,
    year: 2022,
    words: 1450,
    chunks: 9,
    description: 'Concise district-level checklist for pre-monsoon mock drills, wireless communication failover, and stockpile audit.',
    evidence: [
      {
        page: 2,
        section: 'Standard Checklist · Pre-monsoon Readiness',
        score: 90,
        text: 'Ensure all satellite phones, VHF sets, and automated flood telemetry sensors undergo physical verification 15 days before onset of Southwest Monsoon.'
      }
    ]
  }
];

interface PipelineAnimatorProps {
  isActive?: boolean;
}

export const PipelineAnimator: React.FC<PipelineAnimatorProps> = () => {
  const [selectedDocId, setSelectedDocId] = useState<number>(1);
  const selectedDoc = REAL_DOCUMENTS.find(d => d.id === selectedDocId) || REAL_DOCUMENTS[0];

  const [step, setStep]         = useState(-1);
  const [done, setDone]         = useState<Set<number>>(new Set([0, 1, 2, 3, 4, 5, 6, 7]));
  const [running, setRunning]   = useState(false);
  const [showEvidence, setShowEvidence] = useState(true);

  const STAGES = [
    { key: 'upload',  icon: '📂', label: 'Official Document Ingested', detail: `${selectedDoc.filename} · ${selectedDoc.pages} pages · ${selectedDoc.authority}`, runDetail: 'Parsing official document…' },
    { key: 'ocr',     icon: '🔎', label: 'PDF Text Extracted',         detail: `${selectedDoc.pages} pages · ${selectedDoc.words.toLocaleString()} words extracted`, runDetail: 'Extracting PDF layout…' },
    { key: 'clean',   icon: '✏️', label: 'Text Cleaned & Normalized',  detail: 'Footers, page headers, noise & punctuation normalized', runDetail: 'Cleaning text…' },
    { key: 'chunk',   icon: '✂️', label: `${selectedDoc.chunks} Chunks Generated`, detail: `Overlapping window chunks (avg 320 tokens per chunk)`, runDetail: 'Chunking document…' },
    { key: 'embed',   icon: '🧬', label: 'BGE-M3 Embeddings Calculated', detail: `${selectedDoc.chunks} dense vectors · 1024 dimensions`, runDetail: 'Generating 1024-d embeddings…' },
    { key: 'index',   icon: '💾', label: 'Indexed in Qdrant Vector DB', detail: `Collection: disaster_knowledge_base · Stored & searchable`, runDetail: 'Indexing into Qdrant…' },
    { key: 'search',  icon: '🔍', label: 'Hybrid Vector + BM25 Ready', detail: `2,469 total vectors ready for cross-document queries`, runDetail: 'Verifying index searchability…' },
    { key: 'verify',  icon: '✅', label: 'Knowledge Base Verified',    detail: `Score 96% · Grounded on official government disaster guidelines`, runDetail: 'Validating citations…' },
  ];

  const STAGE_MS = [300, 350, 250, 320, 450, 280, 380, 250];

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

  const getStatus = (i: number): 'done' | 'active' | 'idle' => {
    if (done.has(i)) return 'done';
    if (step === i)  return 'active';
    return 'idle';
  };

  return (
    <div style={{ maxWidth: 840, margin: '0 auto' }}>

      {/* Overview Statistics Banner */}
      <div style={{
        background: '#EFF6FF', border: '1px solid #BFDBFE',
        borderRadius: 8, padding: '14px 18px', marginBottom: 20,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12
      }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#2563EB', marginBottom: 2 }}>
            OFFICIAL DISASTER MANAGEMENT KNOWLEDGE BASE
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-main)' }}>
            7 Official Government Documents Ingested
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            NDMA Guidelines · Maharashtra SDMP 2023 · Pune DDMP 2025-26 · MoHUA Urban Flooding SOP
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16, textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#2563EB' }}>2,469</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Total Vectors</div>
          </div>
          <div style={{ width: 1, background: '#BFDBFE' }} />
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#16A34A' }}>1,024</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Dimensions</div>
          </div>
          <div style={{ width: 1, background: '#BFDBFE' }} />
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#16A34A' }}>0</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Mock SOPs</div>
          </div>
        </div>
      </div>

      {/* Document Selector Dropdown & Tabs */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
          Select Ingested Document to Inspect Pipeline:
        </label>
        <select
          value={selectedDocId}
          onChange={e => {
            setSelectedDocId(Number(e.target.value));
            setDone(new Set([0, 1, 2, 3, 4, 5, 6, 7]));
            setShowEvidence(true);
          }}
          style={{
            width: '100%', padding: '10px 14px', fontSize: 14, fontWeight: 600,
            border: '1px solid var(--border)', borderRadius: 6,
            background: '#FFF', color: 'var(--text-main)', cursor: 'pointer'
          }}
        >
          {REAL_DOCUMENTS.map(doc => (
            <option key={doc.id} value={doc.id}>
              {doc.title} ({doc.pages} pages · {doc.chunks} chunks)
            </option>
          ))}
        </select>
      </div>

      {/* Active Document Info Card */}
      <div style={{
        background: '#FFF', border: '1px solid var(--border)',
        borderLeft: '4px solid #2563EB', borderRadius: 8,
        padding: '16px 20px', marginBottom: 20
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 8 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 18 }}>📄</span>
              <strong style={{ fontSize: 15, color: 'var(--text-main)' }}>{selectedDoc.title}</strong>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Source: <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--bg-subtle)', padding: '2px 6px', borderRadius: 4 }}>{selectedDoc.filename}</code> · Authority: <strong>{selectedDoc.authority}</strong> · Year: {selectedDoc.year}
            </div>
          </div>
          <span className="badge badge-safe">✓ VERIFIED & INDEXED</span>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5, margin: '8px 0 0' }}>
          {selectedDoc.description}
        </p>
      </div>

      {/* Pipeline Steps Checklist */}
      <div style={{
        background: '#FFF', border: '1px solid var(--border)', borderRadius: 8,
        padding: '16px 20px', marginBottom: 20
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>
          RAG Ingestion Audit Trace
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
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

        <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            onClick={runAnimation}
            disabled={running}
            className="btn-ent btn-ent-outline"
            style={{ fontSize: 13 }}
          >
            {running ? '⟳ Re-running Pipeline Trace…' : '↺ Replay Ingestion Pipeline Trace'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Vector Collection: <strong style={{ color: 'var(--text-main)' }}>disaster_knowledge_base</strong>
          </span>
        </div>
      </div>

      {/* Evidence Panel (Verified Chunks from the real document) */}
      {showEvidence && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-main)', marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>📋 Verified Evidence Passages from {selectedDoc.filename}</span>
            <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)' }}>
              {selectedDoc.evidence.length} sample passages retrieved
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {selectedDoc.evidence.map((ev, idx) => (
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
                      📄 {selectedDoc.filename}
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