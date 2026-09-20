import React from 'react';
import { TacticalCopilot } from './TacticalCopilot';

interface RightDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onMissionCreated?: (mission: { id: string; rec: string; commander: string; timestamp: string }) => void;
}

export const RightDrawer: React.FC<RightDrawerProps> = ({ isOpen, onClose, onMissionCreated }) => {
  return (
    <div className={`right-drawer ${isOpen ? 'open' : ''}`}>
      <div className="drawer-header">
        <div className="drawer-title">🤖 AI TACTICAL COPILOT</div>
        <button className="drawer-close" onClick={onClose} title="Close drawer">✕</button>
      </div>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <TacticalCopilot onMissionCreated={onMissionCreated} />
      </div>
    </div>
  );
};
