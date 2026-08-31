// frontend/src/data/scenario.js
// Static seed data matching real backend camera IDs (CAM-001..CAM-005).
// Live REST data is fetched and merged by useAPIData hook.

export const CAMERAS = [
  {
    camera_id: 'CAM-001',
    name: 'BOP Main Gate',
    location: 'Border Outpost Alpha',
    lat: 28.6139,
    lng: 77.2090,
  },
  {
    camera_id: 'CAM-002',
    name: 'Checkpost Alpha',
    location: 'Checkpost Sector 1',
    lat: 28.6205,
    lng: 77.2165,
  },
  {
    camera_id: 'CAM-003',
    name: 'Perimeter Fence North',
    location: 'Northern Perimeter',
    lat: 28.6250,
    lng: 77.2100,
  },
  {
    camera_id: 'CAM-004',
    name: 'Night Surveillance Post',
    location: 'Observation Post Delta',
    lat: 28.6180,
    lng: 77.2040,
  },
  {
    camera_id: 'CAM-005',
    name: 'Secondary Transit Gate',
    location: 'Transit Sector 2',
    lat: 28.6110,
    lng: 77.2150,
  },
];

// Default zone for demo
export const ZONE = {
  zone_id: 'ZONE-01',
  zone_name: 'Restricted Perimeter Area',
  camera_id: 'CAM-001',
  severity: 'HIGH',
  polygon: [
    [28.6148, 77.2078],
    [28.6148, 77.2102],
    [28.6130, 77.2102],
    [28.6130, 77.2078],
  ],
};

export const SCENARIO_EVENTS = [];

export const SEVERITY_COLOR = {
  CRITICAL: '#ff2244',
  HIGH:     '#ff6633',
  MEDIUM:   '#ffaa00',
  LOW:      '#34d9b4',
};

