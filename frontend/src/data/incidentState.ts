export interface HospitalState {
  id: string;
  name: string;
  availableBeds: number;
  totalBeds: number;
  distance: number;
  status: 'Operational' | 'At Risk' | 'Full';
}

export interface IncidentState {
  incidentId: string;
  location: string;
  disasterType: string;
  rainfall: number; // mm/hr
  riverLevel: number; // m
  criticalRiverLevel: number; // m
  windSpeed: number; // km/h
  populationAtRisk: number;
  riskScore: number; // e.g. 87 / 100
  groundedScore: number; // e.g. 96%
  hospitals: HospitalState[];
  assets: {
    rescueBoats: { available: number; total: number; required: number; reasoning: string; confidence: number };
    ambulances: { available: number; total: number; required: number; reasoning: string; confidence: number };
    helicopters: { available: number; total: number; required: number; reasoning: string; confidence: number };
    medicalTeams: { available: number; total: number; required: number; reasoning: string; confidence: number };
  };
  simulationActive: boolean;
}

export const initialIncidentState: IncidentState = {
  incidentId: 'INC-2026-PUNE-01',
  location: 'Pune',
  disasterType: 'Flood',
  rainfall: 40,
  riverLevel: 1.9,
  criticalRiverLevel: 1.8,
  windSpeed: 35,
  populationAtRisk: 22400,
  riskScore: 87,
  groundedScore: 96,
  hospitals: [
    { id: 'h1', name: 'Sassoon General Hospital', availableBeds: 41, totalBeds: 120, distance: 2.4, status: 'Operational' },
    { id: 'h2', name: 'Noble Hospital', availableBeds: 8, totalBeds: 100, distance: 4.1, status: 'At Risk' }
  ],
  assets: {
    rescueBoats: {
      available: 8, total: 12, required: 4,
      reasoning: 'Population at risk (22,400) + Mutha River level (1.9m) across 2 inundated sub-zones.',
      confidence: 94
    },
    ambulances: {
      available: 10, total: 16, required: 5,
      reasoning: 'Predicted evacuation load + medical capacity requirement via Ring Road bypass.',
      confidence: 89
    },
    helicopters: {
      available: 2, total: 3, required: 1,
      reasoning: 'Aerial reconnaissance & critical airlift over flooded Highway 48.',
      confidence: 92
    },
    medicalTeams: {
      available: 5, total: 8, required: 3,
      reasoning: 'Pre-positioning trauma teams under NDMA SOP Rule 4.2 bed reservation.',
      confidence: 96
    }
  },
  simulationActive: false
};
