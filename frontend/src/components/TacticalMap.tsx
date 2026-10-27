import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import type { MarkerData } from './MarkerDetailDrawer';
import { initialIncidentState, type IncidentState } from '../data/incidentState';

interface WhatIfResult {
  active: boolean;
  rainfall: number;
  riverLevel: number;
  bridgeFail: boolean;
  evacuees: number;
  boats: number;
  hoursUntil: number;
}

interface TacticalMapProps {
  whatIfResult?: WhatIfResult | null;
  onMarkerClick?: (marker: MarkerData) => void;
  onMapClick?: (lat: number, lng: number) => void;
  showHeatmap?: boolean;
  incident?: IncidentState;
}

// ─── Dynamic marker data builder ─────────────────────────
export const getMarkerData = (inc: IncidentState): MarkerData[] => {
  const h1 = inc.hospitals[0];
  const h2 = inc.hospitals[1] ?? inc.hospitals[0];
  const bridge = inc.infrastructure.find(item => item.type === 'Bridge');
  const sensor = inc.sensors[0];

  return [
    {
      id: 'hospital-1',
      lat: 18.5274,
      lng: 73.8633,
      icon: '🏥',
      label: h1.name,
      type: 'Medical Facility',
      status: h1.status === 'Operational' ? 'OPERATIONAL' : 'AT RISK',
      statusColor: h1.status === 'Operational' ? '#30d158' : '#ffb340',
      confidence: 98,
      info: `Primary medical hub. Available beds: ${h1.availableBeds} / ${h1.totalBeds}. Distance: ${h1.distance} km. Trauma team deployed via Ring Road NH-48 bypass.`,
      sensorReading: {
        value: String(h1.availableBeds),
        unit: `available beds (${Math.round((h1.availableBeds / h1.totalBeds) * 100)}% available)`,
        trend: '✓ Receiving',
      },
      roads: [
        { name: 'Ring Road NH-48', status: 'OPEN', color: '#30d158' },
        { name: `${bridge?.name ?? 'Sangam Bridge'} Rd`, status: 'BLOCKED', color: '#ff3b30' },
      ],
      hospitals: [
        { name: h2.name, distance: `${h2.distance} km`, color: '#ffb340' },
        { name: 'Deenanath Mangeshkar', distance: '3.8 km', color: '#30d158' },
      ],
      riskParagraph: `${h1.name} is located ${h1.distance} km from Zone A at safe elevation above flood level. AI Recommendation: Prepare emergency beds under Rule 4.2 (40% bed reservation). Evidence: Flood SOP Rule 4.2.`,
    },
    {
      id: 'hospital-2',
      lat: 18.5135,
      lng: 73.8820,
      icon: '🏥',
      label: h2.name,
      type: 'Medical Facility',
      status: h2.status === 'Operational' ? 'OPERATIONAL' : 'AT RISK',
      statusColor: h2.status === 'Operational' ? '#30d158' : '#ffb340',
      confidence: 87,
      info: `Capacity: ${Math.round(
        ((h2.totalBeds - h2.availableBeds) / h2.totalBeds) * 100
      )}% occupied. Partial patient relocation active. ${bridge?.name ?? 'Sangam Bridge'} closure cuts primary road access. Alternate route via NH-48.`,
      sensorReading: {
        value: String(Math.round(((h2.totalBeds - h2.availableBeds) / h2.totalBeds) * 100)),
        unit: '% capacity',
        trend: '⚠ Critical',
      },
      roads: [
        { name: `${bridge?.name ?? 'Sangam Bridge'} Rd`, status: 'BLOCKED', color: '#ff3b30' },
        { name: 'NH-48 Alternate', status: 'OPEN', color: '#30d158' },
      ],
      hospitals: [
        { name: h1.name, distance: `${h1.distance} km`, color: '#30d158' },
      ],
      riskParagraph: `${h2.name} sits within the secondary flood impact zone. If river level rises above 2.2m, access will be completely cut. AI recommends immediate non-critical patient transfer to ${h1.name} within 2 hours.`,
    },
    {
      id: 'bridge-1',
      lat: bridge?.latitude ?? 18.5360,
      lng: bridge?.longitude ?? 73.8562,
      icon: '🌉',
      label: bridge?.name ?? 'Sangam Bridge',
      type: 'Infrastructure',
      status: (bridge?.status ?? 'CRITICAL') as any,
      statusColor: '#ff3b30',
      confidence: bridge?.confidence ?? 97,
      info: `${bridge?.description ?? 'Severe structural crack detected by drone. Bridge closed to traffic.'} ${inc.assets.rescueBoats.total} rescue boats rerouted. Highway NH-48 is primary alternate.`,
      sensorReading: {
        value: String(bridge?.sensorReading?.value ?? 4.8),
        unit: bridge?.sensorReading?.unit ?? 'cm crack',
        trend: bridge?.sensorReading?.trend ?? 'Widening',
      },
      roads: [
        { name: `${bridge?.name ?? 'Sangam Bridge'} Rd`, status: 'CLOSED', color: '#ff3b30' },
        { name: 'NH-48 Bypass', status: 'ACTIVE', color: '#30d158' },
      ],
      hospitals: [
        { name: h1.name, distance: `${h1.distance} km`, color: '#30d158' },
        { name: h2.name, distance: `${h2.distance} km`, color: '#ffb340' },
      ],
      riskParagraph: `Drone Alpha-1 confirms ${bridge?.sensorReading?.value ?? 4.8}${bridge?.sensorReading?.unit ?? 'cm'} structural crack at pier 3. Load capacity reduced to 0%. ${bridge?.name ?? 'Bridge'} is CLOSED to all traffic. Risk of partial collapse within 4-6 hours if river level exceeds 2.5m. Dispatch structural engineers immediately.`,
    },
    {
      id: 'sensor-1',
      lat: 18.5230,
      lng: 73.8490,
      icon: '📡',
      label: sensor.name,
      type: 'IoT Sensor Node',
      status: (sensor.status ?? 'ALERT') as any,
      statusColor: '#ff3b30',
      confidence: 99,
      info: `Water level: ${sensor.value}${sensor.unit}. Threshold: ${sensor.criticalValue}${sensor.unit}. Rising at ${sensor.trend}. Alert active.`,
      sensorReading: {
        value: String(sensor.value),
        unit: `${sensor.unit} level`,
        trend: `↑ ${sensor.trend}`,
      },
      roads: [
        { name: 'Riverbank Road', status: 'FLOODED', color: '#ff3b30' },
      ],
      hospitals: [
        { name: h1.name, distance: `${h1.distance} km`, color: '#30d158' },
      ],
      riskParagraph: `Sensor reading of ${sensor.value}${sensor.unit} has exceeded critical threshold of ${sensor.criticalValue}${sensor.unit} by +${(sensor.value - sensor.criticalValue).toFixed(1)}${sensor.unit}. Rising trend (${sensor.trend}) confirmed. If current rate continues, flood conditions will worsen.`,
    },
    {
      id: 'shelter-1',
      lat: 18.5400,
      lng: 73.8750,
      icon: '🏕️',
      label: 'Sports Complex Shelter',
      type: 'Evacuation Shelter',
      status: 'ACTIVE',
      statusColor: '#30d158',
      confidence: 95,
      info: '120 beds total. 62 occupied (52% capacity). Supplies: adequate for 72h. Access: clear via NH-48.',
      sensorReading: { value: '62', unit: 'beds used', trend: '↑ Filling' },
      roads: [
        { name: 'NH-48', status: 'OPEN', color: '#30d158' },
        { name: 'Bypass Road 7', status: 'OPEN', color: '#30d158' },
      ],
      hospitals: [
        { name: h1.name, distance: `${h1.distance} km`, color: '#30d158' },
      ],
      riskParagraph: 'Primary evacuation shelter operating normally. Located at safe elevation above flood zone. Recommend pre-positioning 40 additional cots. At current intake rate, capacity will be reached within 6 hours.',
    },
    {
      id: 'drone-1',
      lat: 18.5320,
      lng: 73.8600,
      icon: '🚁',
      label: 'Drone Alpha-1',
      type: 'Aerial Asset',
      status: 'SURVEYING',
      statusColor: '#bf5af2',
      confidence: 93,
      info: `Altitude: 80m. Surveying ${bridge?.name ?? 'Sangam Bridge'} & flood zone. Battery: 68%. ETA return: 22 minutes.`,
      sensorReading: { value: '80', unit: 'm altitude', trend: '✓ Stable' },
      roads: [],
      hospitals: [],
      riskParagraph: `Drone Alpha-1 is providing real-time video feed of the primary flood zone and ${bridge?.name ?? 'Sangam Bridge'} structural status. Battery charge sufficient for 22 more minutes of operation. Recommend priority: confirm ${h2.name} access road status before returning.`,
    },
  ];
};

// ─── Flood polygon ────────────────────────────────────────
const FLOOD_POLYGON: [number, number][] = [
  [18.530, 73.845], [18.545, 73.852], [18.538, 73.868],
  [18.525, 73.860], [18.520, 73.848]
];
const WHATIF_POLYGON: [number, number][] = [
  [18.525, 73.840], [18.550, 73.855], [18.545, 73.878],
  [18.520, 73.870], [18.510, 73.850]
];

export const TacticalMap: React.FC<TacticalMapProps> = ({
  whatIfResult, onMarkerClick, onMapClick, showHeatmap = true, incident = initialIncidentState
}) => {
  const mapRef  = useRef<HTMLDivElement>(null);
  const mapInst = useRef<L.Map | null>(null);
  const heatRects  = useRef<L.Rectangle[]>([]);
  const whatIfPoly = useRef<L.Polygon | null>(null);
  const [clickToast, setClickToast] = useState<{ label: string; lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (!mapRef.current || mapInst.current) return;

    const map = L.map(mapRef.current, {
      center: [18.528, 73.857],
      zoom: 13,
      zoomControl: false,
      attributionControl: false,
    });
    mapInst.current = map;

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    L.control.zoom({ position: 'topright' }).addTo(map);

    // Flood zone polygon
    L.polygon(FLOOD_POLYGON, {
      color: '#ff3b30', fillColor: '#ff3b30', fillOpacity: 0.10,
      weight: 1.5, dashArray: '6,4', interactive: false
    }).addTo(map);

    // Add animated markers
    const markerData = getMarkerData(incident);
    markerData.forEach(m => {
      const icon = L.divIcon({
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        html: `<div style="
          width:28px;height:28px;
          border-radius:50%;
          background:rgba(6,12,26,0.92);
          border:2px solid ${m.statusColor};
          display:flex;align-items:center;justify-content:center;
          font-size:13px;
          box-shadow:0 0 10px ${m.statusColor}50;
          cursor:pointer;
          transition:transform 0.15s;
        " title="${m.label}">${m.icon}</div>`
      });

      L.marker([m.lat, m.lng], { icon })
        .addTo(map)
        .on('click', () => {
          setClickToast({ label: m.label, lat: m.lat, lng: m.lng });
          onMarkerClick?.(m);
          setTimeout(() => setClickToast(null), 3000);
        });
    });

    // Background map click
    map.on('click', (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      onMapClick?.(lat, lng);
    });

    return () => {
      if (mapInst.current) { mapInst.current.remove(); mapInst.current = null; }
    };
  }, [incident]);

  // Heatmap layer
  useEffect(() => {
    const map = mapInst.current;
    if (!map) return;
    heatRects.current.forEach(r => map.removeLayer(r));
    heatRects.current = [];
    if (!showHeatmap) return;

    const cells = [
      { bounds: [[18.530, 73.845], [18.545, 73.865]] as L.LatLngBoundsExpression, color: '#ff3b30', opacity: 0.15 },
      { bounds: [[18.520, 73.845], [18.530, 73.860]] as L.LatLngBoundsExpression, color: '#ff8c00', opacity: 0.12 },
      { bounds: [[18.510, 73.855], [18.520, 73.870]] as L.LatLngBoundsExpression, color: '#ffcc00', opacity: 0.09 },
      { bounds: [[18.515, 73.870], [18.535, 73.885]] as L.LatLngBoundsExpression, color: '#30d158', opacity: 0.07 },
    ];

    cells.forEach(c => {
      const r = L.rectangle(c.bounds, {
        color: c.color, fillColor: c.color, fillOpacity: c.opacity,
        weight: 0, interactive: false
      }).addTo(map);
      heatRects.current.push(r);
    });
  }, [showHeatmap]);

  // What-If polygon
  useEffect(() => {
    const map = mapInst.current;
    if (!map) return;
    if (whatIfPoly.current) { map.removeLayer(whatIfPoly.current); whatIfPoly.current = null; }

    if (whatIfResult?.active) {
      whatIfPoly.current = L.polygon(WHATIF_POLYGON, {
        color: '#bf5af2', fillColor: '#bf5af2', fillOpacity: 0.18,
        weight: 2, dashArray: '6,3'
      }).addTo(map);
      whatIfPoly.current.bindTooltip(
        `⚡ Predicted +${whatIfResult.hoursUntil}h — ${(whatIfResult.evacuees / 1000).toFixed(1)}k evacuees`,
        { permanent: true, direction: 'center', className: 'geo-tt' }
      );
      map.fitBounds(whatIfPoly.current.getBounds(), { padding: [40, 40] });
    }
  }, [whatIfResult]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />

      {/* Click toast */}
      {clickToast && (
        <div className="map-float map-click-toast">
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--cyan)' }}>📍 ASSET SELECTED</span>
          <strong style={{ fontSize: 12 }}>{clickToast.label}</strong>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t2)' }}>
            {clickToast.lat.toFixed(5)}°N · {clickToast.lng.toFixed(5)}°E
          </span>
        </div>
      )}
    </div>
  );
};
