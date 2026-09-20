import React, { useEffect, useState } from 'react';

interface Notification {
  id: number;
  type: 'sensor' | 'weather' | 'danger' | 'ai';
  text: string;
  time: string;
  icon: string;
}

const SEED: Notification[] = [
  { id:1,  type:'danger',  icon:'🌉', text:'Sangam Bridge — structural alert!',          time:'10:05' },
  { id:2,  type:'sensor',  icon:'📡', text:'Mutha sensor: 1.9m — threshold breached',    time:'10:06' },
  { id:3,  type:'ai',      icon:'🤖', text:'AI: Evacuation Phase 2 recommended',         time:'10:07' },
  { id:4,  type:'weather', icon:'🌧', text:'IMD: 45mm/hr storm arriving in 3h',          time:'10:12' },
];

const LIVE: Notification[] = [
  { id:0, type:'sensor',  icon:'📡', text:'IoT Level +0.05m in last 5 min',              time:'' },
  { id:0, type:'ai',      icon:'🤖', text:'AI updated risk score: 87/100',               time:'' },
  { id:0, type:'danger',  icon:'⚠️', text:'Highway 48 partially flooded',               time:'' },
  { id:0, type:'weather', icon:'🌧', text:'Wind speed increasing: now 42 km/h',          time:'' },
  { id:0, type:'ai',      icon:'📋', text:'Rescue report auto-generated',               time:'' },
];

const nowStr = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

export const NotificationCenter: React.FC = () => {
  const [notifs, setNotifs] = useState<Notification[]>(SEED);
  const liveIdx = React.useRef(0);

  useEffect(() => {
    const interval = setInterval(() => {
      const base = LIVE[liveIdx.current % LIVE.length];
      const notif: Notification = { ...base, id: Date.now(), time: nowStr() };
      setNotifs(prev => [notif, ...prev].slice(0, 12));
      liveIdx.current++;
    }, 18000);
    return () => clearInterval(interval);
  }, []);

  const dismiss = (id: number) => setNotifs(prev => prev.filter(n => n.id !== id));

  return (
    <div className="notif-list" style={{ overflowY: 'auto', height: '100%' }}>
      {notifs.map(n => (
        <div key={n.id} className={`notif-item ${n.type}`} onClick={() => dismiss(n.id)}>
          <span style={{ fontSize: 12, flexShrink: 0 }}>{n.icon}</span>
          <div style={{ flex: 1 }}>
            <div className="notif-text">{n.text}</div>
            <div className="notif-time">{n.time}</div>
          </div>
          <button onClick={() => dismiss(n.id)} style={{
            background: 'none', border: 'none', cursor: 'pointer', color: 'var(--txt3)',
            fontSize: 10, padding: 0, flexShrink: 0
          }}>✕</button>
        </div>
      ))}
    </div>
  );
};
