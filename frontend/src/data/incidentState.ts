export interface HospitalState {
  id: string;
  name: string;
  availableBeds: number;
  totalBeds: number;
  distance: number;
  status: 'Operational' | 'At Risk' | 'Full';
}

export interface InfrastructureState {
  id: string;
  name: string;
  type: 'Bridge' | 'Road' | 'Building';
  status: string;
  confidence: number;
  latitude?: number;
  longitude?: number;
  description: string;
  sensorReading?: {
    value: number;
    unit: string;
    trend: string;
  };
}

export interface SensorState {
  id: string;
  name: string;
  type: string;
  value: number;
  unit: string;
  criticalValue: number;
  trend: string;
  status: string;
}

export interface ResourceState {
  available: number;
  total: number;
  required: number;
  reasoning: string;
  confidence: number;
}

export interface IncidentState {
  incidentId: string;
  location: string;
  disasterType: string;
  severity: string;

  rainfall: number;
  riverLevel: number;
  criticalRiverLevel: number;
  windSpeed: number;
  populationAtRisk: number;

  riskScore: number;
  groundedScore: number;

  hospitals: HospitalState[];

  infrastructure: InfrastructureState[];

  sensors: SensorState[];

  assets: {
    rescueBoats: ResourceState;
    ambulances: ResourceState;
    helicopters: ResourceState;
    medicalTeams: ResourceState;
  };

  aiAssessment: {
    priority: string;
    summary: string;
    recommendations: string[];
    confidence: number;
  };

  simulationActive: boolean;
}

/**
 * Temporary demo incident.
 *
 * This represents the data that will eventually come from
 * the Detection, Prediction, Sensor, Weather, AI and
 * Resource Management APIs.
 */
export const initialIncidentState: IncidentState = {
  incidentId: 'INC-2026-PUNE-01',

  location: 'Pune',
  disasterType: 'Flood',
  severity: 'CRITICAL',

  rainfall: 40,
  riverLevel: 1.9,
  criticalRiverLevel: 1.8,
  windSpeed: 35,
  populationAtRisk: 22400,

  riskScore: 87,
  groundedScore: 96,

  hospitals: [
    {
      id: 'h1',
      name: 'Sassoon General Hospital',
      availableBeds: 41,
      totalBeds: 120,
      distance: 2.4,
      status: 'Operational',
    },
    {
      id: 'h2',
      name: 'Noble Hospital',
      availableBeds: 8,
      totalBeds: 100,
      distance: 4.1,
      status: 'At Risk',
    },
  ],

  infrastructure: [
    {
      id: 'bridge-1',
      name: 'Sangam Bridge',
      type: 'Bridge',
      status: 'CRITICAL',
      confidence: 97,
      latitude: 18.5360,
      longitude: 73.8562,
      description:
        'Severe structural crack detected by drone. Bridge closed to traffic.',
      sensorReading: {
        value: 4.8,
        unit: 'cm crack',
        trend: 'Widening',
      },
    },
    {
      id: 'road-1',
      name: 'NH-48',
      type: 'Road',
      status: 'FLOODED',
      confidence: 94,
      description: 'Road access affected by flood conditions.',
    },
  ],

  sensors: [
    {
      id: 'sensor-1',
      name: 'Mutha River Sensor',
      type: 'Water Level',
      value: 1.9,
      unit: 'm',
      criticalValue: 1.8,
      trend: '+0.1 m / 5 min',
      status: 'CRITICAL',
    },
  ],

  assets: {
    rescueBoats: {
      available: 8,
      total: 12,
      required: 4,
      reasoning:
        'Population at risk and Mutha River level across affected zones.',
      confidence: 94,
    },

    ambulances: {
      available: 10,
      total: 16,
      required: 5,
      reasoning:
        'Predicted evacuation load and medical capacity requirement.',
      confidence: 89,
    },

    helicopters: {
      available: 2,
      total: 3,
      required: 1,
      reasoning:
        'Aerial reconnaissance and critical airlift over flooded areas.',
      confidence: 92,
    },

    medicalTeams: {
      available: 5,
      total: 8,
      required: 3,
      reasoning:
        'Pre-position trauma teams based on emergency medical requirements.',
      confidence: 96,
    },
  },

  aiAssessment: {
    priority: 'CRITICAL',

    summary:
      'Flood conditions have exceeded the defined river threshold and critical infrastructure is affected.',

    recommendations: [
      'Begin evacuation in affected zones.',
      'Close damaged bridge access.',
      'Prepare emergency hospital capacity.',
      'Deploy rescue resources to affected areas.',
    ],

    confidence: 94,
  },

  simulationActive: false,
};
