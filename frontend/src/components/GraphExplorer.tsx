import React, { useState } from 'react';

interface Node {
  id: string;
  label: string;
  type: string;
  status?: string;
  x: number;
  y: number;
  details?: Record<string, any>;
}

interface Edge {
  source: string;
  target: string;
  type: string;
}

export const GraphExplorer: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Hardcode coordinate points for nodes to guarantee a beautiful layout
  const nodes: Node[] = [
    { id: "State:MH", label: "Maharashtra", type: "State", x: 50, y: 70, details: { governor: "MH Government", risk_index: "Moderate" } },
    { id: "Dist:Pune", label: "Pune District", type: "District", x: 130, y: 120, details: { population: "9.4M", area: "15,643 sq km" } },
    { id: "City:Pune_City", label: "Pune City", type: "City", x: 220, y: 170, details: { main_river: "Mutha River", status: "Flood Advisory" } },
    { id: "Disaster:Flood", label: "Mutha Flood", type: "Disaster", x: 340, y: 70, details: { severity: "Severe (Level 4)", triggers: "Heavy Inundation" } },
    { id: "Sensor:WaterLevel", label: "Mutha Sensor", type: "Sensor", x: 300, y: 220, details: { telemetry: "1.9m water level", status: "Warning Triggered" } },
    { id: "Hospital:Sassoon", label: "Sassoon Hospital", type: "Hospital", x: 140, y: 240, status: "Active", details: { capacity: "Normal (78% occupied)", medical_kits: "Available" } },
    { id: "Hospital:Noble", label: "Noble Hospital", type: "Hospital", x: 230, y: 270, status: "At Risk", details: { capacity: "Strained (92% occupied)", evacuation_needed: "Partial" } },
    { id: "Bridge:Sangam", label: "Sangam Bridge", type: "Bridge", x: 420, y: 180, status: "Blocked", details: { damage: "Severe structural crack", closed_by: "Pune Police" } },
    { id: "Shelter:SportsComplex", label: "Sports Complex", type: "Shelter", x: 440, y: 260, status: "Active", details: { beds_available: "120 beds", capacity_percent: "40%" } }
  ];

  const edges: Edge[] = [
    { source: "Dist:Pune", target: "State:MH", type: "LOCATED_IN" },
    { source: "City:Pune_City", target: "Dist:Pune", type: "LOCATED_IN" },
    { source: "City:Pune_City", target: "Disaster:Flood", type: "AFFECTED_BY" },
    { source: "Hospital:Sassoon", target: "City:Pune_City", type: "LOCATED_IN" },
    { source: "Hospital:Noble", target: "City:Pune_City", type: "LOCATED_IN" },
    { source: "Bridge:Sangam", target: "City:Pune_City", type: "CONNECTS" },
    { source: "Sensor:WaterLevel", target: "City:Pune_City", type: "MONITORS" },
    { source: "Sensor:WaterLevel", target: "Disaster:Flood", type: "TRIGGERS_ON" },
    { source: "Hospital:Noble", target: "Disaster:Flood", type: "THREATENED_BY" },
    { source: "Bridge:Sangam", target: "Disaster:Flood", type: "DAMAGED_BY" },
    { source: "Shelter:SportsComplex", target: "City:Pune_City", type: "LOCATED_IN" }
  ];

  const getNodeColor = (node: Node) => {
    switch (node.type) {
      case "Disaster": return "#ff3b30";
      case "Hospital": return node.status === "Active" ? "#34c759" : "#ffcc00";
      case "Sensor": return "#00f0ff";
      case "Bridge": return node.status === "Blocked" ? "#ff3b30" : "#34c759";
      case "Shelter": return "#34c759";
      default: return "#94a3b8";
    }
  };

  const getNodeRadius = (type: string) => {
    if (type === "Disaster" || type === "City") return 14;
    return 10;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 h-full select-none">
      {/* SVG Canvas (Left 2 columns) */}
      <div className="md:col-span-2 relative border border-slate-800 rounded-lg bg-slate-950/80 overflow-hidden h-[300px] md:h-full">
        <svg className="w-full h-full" viewBox="0 0 500 320">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
            </marker>
          </defs>
          
          {/* Draw Edges */}
          {edges.map((edge, idx) => {
            const src = nodes.find(n => n.id === edge.source);
            const tgt = nodes.find(n => n.id === edge.target);
            if (!src || !tgt) return null;
            return (
              <g key={`edge-${idx}`}>
                <line 
                  x1={src.x} y1={src.y} 
                  x2={tgt.x} y2={tgt.y} 
                  stroke="#334155" 
                  strokeWidth="1.5"
                  markerEnd="url(#arrow)"
                />
                {/* Relationship label */}
                <text 
                  x={(src.x + tgt.x) / 2} 
                  y={(src.y + tgt.y) / 2 - 3} 
                  fill="#64748b" 
                  fontSize="7" 
                  textAnchor="middle"
                  className="bg-slate-950"
                >
                  {edge.type}
                </text>
              </g>
            );
          })}

          {/* Draw Nodes */}
          {nodes.map(node => {
            const color = getNodeColor(node);
            const r = getNodeRadius(node.type);
            const isSelected = selectedNode?.id === node.id;
            return (
              <g 
                key={node.id} 
                className="cursor-pointer" 
                onClick={() => setSelectedNode(node)}
              >
                <circle 
                  cx={node.x} cy={node.y} 
                  r={r} 
                  fill="#0f172a" 
                  stroke={color} 
                  strokeWidth={isSelected ? 3.5 : 2}
                  className="transition-all duration-200"
                  style={{
                    filter: isSelected ? `drop-shadow(0 0 6px ${color})` : 'none'
                  }}
                />
                {/* Node Label Text */}
                <text 
                  x={node.x} y={node.y + r + 12} 
                  fill={isSelected ? "#fff" : "#cbd5e1"} 
                  fontSize="8" 
                  fontWeight={isSelected ? "bold" : "normal"}
                  textAnchor="middle"
                >
                  {node.label}
                </text>
                {/* Node Type tag */}
                <text 
                  x={node.x} y={node.y - r - 3} 
                  fill="#64748b" 
                  fontSize="6" 
                  textAnchor="middle"
                >
                  {node.type}
                </text>
              </g>
            );
          })}
        </svg>
        <span className="absolute bottom-2 left-2 text-[9px] text-slate-500 font-mono">
          Neo4j Relational Graph Sim v1.0 • Click nodes to query
        </span>
      </div>

      {/* Details Side Panel (Right 1 column) */}
      <div className="border border-slate-800 bg-slate-950/40 rounded-lg p-3 flex flex-col justify-between text-xs min-h-[120px] md:min-h-0">
        {selectedNode ? (
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
              <span className="font-bold text-slate-200">{selectedNode.label}</span>
              <span 
                className="px-1.5 py-0.5 rounded text-[8px] font-bold" 
                style={{ 
                  backgroundColor: getNodeColor(selectedNode) + '20', 
                  color: getNodeColor(selectedNode),
                  border: `1px solid ${getNodeColor(selectedNode)}30` 
                }}
              >
                {selectedNode.type}
              </span>
            </div>
            
            <div className="space-y-1.5 font-mono text-slate-400 text-[11px] overflow-y-auto max-h-[160px]">
              <p><strong className="text-slate-500">Node ID:</strong> {selectedNode.id}</p>
              {selectedNode.status && (
                <p><strong className="text-slate-500">Status:</strong> <span className={selectedNode.status === 'Active' ? 'text-green-400' : 'text-red-400'}>{selectedNode.status}</span></p>
              )}
              {Object.entries(selectedNode.details || {}).map(([k, v]) => (
                <p key={k} className="capitalize">
                  <strong className="text-slate-500">{k.replace('_', ' ')}:</strong> {String(v)}
                </p>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 py-6 text-center">
            <span className="text-[20px] mb-1">🔍</span>
            <span>Click any graph node to inspect topological relations.</span>
          </div>
        )}
      </div>
    </div>
  );
};
