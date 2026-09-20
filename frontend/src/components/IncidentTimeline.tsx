import React, { useEffect, useRef, useState } from 'react';

interface TimelineEvent {
  id: number;
  time: string;
  title: string;
  detail: string;
  type: 'sensor' | 'weather' | 'danger' | 'ai';
  icon: string;
  lat?: number;
  lng?: number;
}

const SEED_EVENTS: TimelineEvent[] = [
  { id:1, time:'10:02', title:'River Threshold Crossed',   detail:'Mutha gauge: 1.9m (limit: 1.8m)',    type:'sensor',  icon:'📡' },
  { id:2, time:'10:03', title:'Satellite Flood Detected',  detail:'SAM2 masks 4.2 km² inundated',       type:'danger',  icon:'🛰' },
  { id:3, time:'10:05', title:'Sangam Bridge Damaged',     detail:'Structural crack detected by drone',  type:'danger',  icon:'🌉' },
  { id:4, time:'10:06', title:'AI Recommends Evacuation',  detail:'Flood SOP Phase 2 triggered',         type:'ai',      icon:'🤖' },
  { id:5, time:'10:08', title:'Rescue Team A Dispatched',  detail:'8 boats mobilised via Highway 48',    type:'ai',      icon:'🚤' },
  { id:6, time:'10:12', title:'Weather Alert: 3h Rain',    detail:'IMD forecast: 45mm/hr incoming',      type:'weather', icon:'🌧' },
  { id:7, time:'10:15', title:'Noble Hospital at Risk',    detail:'Occupancy 92%, partial relocation',   type:'danger',  icon:'🏥' },
];

const LIVE_EVENTS: TimelineEvent[] = [
  { id:100, time:'', title:'IoT Sensor Update',       detail:'Water level rising +0.1m/5min',       type:'sensor',  icon:'📡' },
  { id:101, time:'', title:'Drone Alpha-1 Report',    detail:'Highway 48 partially accessible',     type:'ai',      icon:'🚁' },
  { id:102, time:'', title:'Rainfall Intensifying',   detail:'Current: 38mm/hr — rising',           type:'weather', icon:'🌧' },
  { id:103, time:'', title:'Medical Team Deployed',   detail:'2 trauma units at Sassoon Hospital',  type:'ai',      icon:'🚑' },
  { id:104, time:'', title:'Shelter Capacity Update', detail:'Sports Complex: 62 beds filled',      type:'sensor',  icon:'🏕️' },
];

const getColor = (type: TimelineEvent['type']) => ({
  sensor: '#00f0ff', weather: '#ffb340', danger: '#ff3b30', ai: '#30d158'
})[type];

const tickTime = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

export const IncidentTimeline: React.FC = () => {
  const [events, setEvents] = useState<TimelineEvent[]>(SEED_EVENTS);
  const listRef = useRef<HTMLDivElement>(null);
  const liveIdx = useRef(0);

  // Auto-add live events every 15 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const ev = { ...LIVE_EVENTS[liveIdx.current % LIVE_EVENTS.length], time: tickTime(), id: Date.now() };
      setEvents(prev => [ev, ...prev].slice(0, 25));
      liveIdx.current++;
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [events.length]);

  return (
    <div ref={listRef} className="panel-body timeline-list" style={{ height: '100%', overflowY: 'auto' }}>
      {events.map(ev => (
        <div key={ev.id} className={`timeline-event`} title="Click to zoom map">
          <div className="timeline-dot" style={{ background: getColor(ev.type) }} />
          <span className="timeline-time">{ev.time}</span>
          <div style={{ flex: 1 }}>
            <div className="timeline-text" style={{ display: 'flex', gap: 4 }}>
              <span>{ev.icon}</span>
              <strong style={{ color: 'var(--txt)' }}>{ev.title}</strong>
            </div>
            <div className="timeline-src">{ev.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
};
