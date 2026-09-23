import { useEffect, useState } from 'react'
import './App.css'
import 'leaflet/dist/leaflet.css'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'

const missionStatusActions = {
  ASSIGNED: [
    { label: 'Deploy', status: 'DEPLOYED' },
    { label: 'Cancel', status: 'CANCELLED' },
  ],
  DEPLOYED: [
    { label: 'En Route', status: 'EN_ROUTE' },
    { label: 'Cancel', status: 'CANCELLED' },
  ],
  EN_ROUTE: [
    { label: 'Arrived', status: 'ARRIVED' },
    { label: 'Cancel', status: 'CANCELLED' },
  ],
  ARRIVED: [
    { label: 'Complete', status: 'COMPLETED' },
    { label: 'Cancel', status: 'CANCELLED' },
  ],
}

const navigationItems = [
  { id: 'dashboard', label: 'Main Dashboard', icon: '⌂' },
  { id: 'hospital', label: 'Nearest Hospital', icon: '✚' },
  { id: 'resources', label: 'Recommended Resources', icon: '◈' },
  { id: 'route', label: 'Rescue Route Planning', icon: '⌁' },
  { id: 'teams', label: 'Available Rescue Teams', icon: '♙' },
  { id: 'deployment', label: 'Team Deployment', icon: '↗' },
  { id: 'vehicles', label: 'Vehicle Tracking', icon: '▣' },
  { id: 'shelters', label: 'Shelter Management', icon: '⌂' },
  { id: 'allocation', label: 'Resource Allocation', icon: '＋' },
]

function Icon({ children }) {
  return <span className="icon" aria-hidden="true">{children}</span>
}

function PanelHeader({ eyebrow, title, action }) {
  return <div className="panel-header"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{action && <button className="text-button" type="button">{action} <span aria-hidden="true">↗</span></button>}</div>
}

function ModuleHeader({ moduleId }) {
  const item = navigationItems.find((navigationItem) => navigationItem.id === moduleId)
  const headers = {
    hospital: ['MEDICAL DISPATCH', 'Locate the nearest hospital for an active response.'],
    resources: ['RESOURCE RECOMMENDATION', 'Rank nearby supplies before committing inventory.'],
    route: ['RISK-AWARE DISPATCH', 'Evaluate route distance, duration, and operational risk.'],
    teams: ['FIELD PERSONNEL', 'Review team readiness and current mission assignments.'],
    deployment: ['MISSION OPERATIONS', 'Assign a response team and coordinate the mission.'],
    vehicles: ['FLEET OPERATIONS', 'Monitor vehicle readiness, location, and mission status.'],
    shelters: ['EVACUATION NETWORK', 'Coordinate shelter capacity and evacuation support.'],
    allocation: ['RESOURCE CONTROL', 'Recommend, allocate, release, or cancel mission resources.'],
  }
  const [eyebrow, description] = headers[moduleId] || ['OPERATIONS', 'Manage emergency response operations.']
  return <section className="module-header"><div><span className="eyebrow">{eyebrow}</span><h1>{item?.label}</h1><p>{description}</p></div><span className="module-status"><i className="pulse-dot" /> ACTIVE WORKSPACE</span></section>
}

function MetricCard({ label, value, detail, icon, tone }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}><Icon>{icon}</Icon></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div><span className="metric-trend">↗</span></article>
}

const resourceTypes = [
  'FOOD',
  'WATER',
  'MEDICAL_SUPPLIES',
  'RESCUE_EQUIPMENT',
  'TEMPORARY_SHELTER_SUPPLIES',
]

function RecommendedResources({ latitude, longitude, resourceType, onLatitudeChange, onLongitudeChange, onResourceTypeChange, onRecommend, loading, error, resources }) {
  return (
    <section className="panel recommendation-panel" aria-labelledby="recommended-resources-title">
      <div className="panel-header"><div><span className="eyebrow">READ-ONLY ROUTING</span><h2 id="recommended-resources-title">Recommended Resources</h2></div><span className="recommendation-status">{resources.length ? `${resources.length} ranked` : 'Awaiting query'}</span></div>
      <p className="recommendation-copy">Find available supplies near a response location before committing inventory.</p>
      <form className="recommendation-controls" onSubmit={(event) => { event.preventDefault(); onRecommend() }}>
        <label htmlFor="recommendation-latitude">Latitude<input id="recommendation-latitude" type="number" step="any" min="-90" max="90" value={latitude} onChange={(event) => onLatitudeChange(event.target.value)} /></label>
        <label htmlFor="recommendation-longitude">Longitude<input id="recommendation-longitude" type="number" step="any" min="-180" max="180" value={longitude} onChange={(event) => onLongitudeChange(event.target.value)} /></label>
        <label htmlFor="recommendation-type">Type<select id="recommendation-type" value={resourceType} onChange={(event) => onResourceTypeChange(event.target.value)}><option value="">Any type</option>{resourceTypes.map((type) => <option value={type} key={type}>{type.replaceAll('_', ' ')}</option>)}</select></label>
        <button className="inventory-allocation-button" type="submit" disabled={loading}>{loading ? 'Searching...' : 'Find resources'}</button>
      </form>
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {!loading && !error && resources.length === 0 && <span className="muted">Enter a location to see ranked emergency resources.</span>}
      {!loading && !error && resources.length > 0 && <div className="recommended-resource-list">{resources.map((resource, index) => { const distance = resource.distance_km ?? resource.distance ?? resource.estimated_distance_km; return <article className="recommended-resource" key={resource.resource_id}><span className="recommendation-rank">{String(index + 1).padStart(2, '0')}</span><div className="compact-main"><strong>{resource.name}</strong><span>{resource.resource_id} · {resource.resource_type}</span></div><div className="recommended-resource-meta"><b>{resource.available_quantity}</b><small>available</small>{distance !== undefined && <small>{Number(distance).toFixed(1)} km</small>}</div></article>})}</div>}
    </section>
  )
}

function NearestHospital({ latitude, longitude, onLatitudeChange, onLongitudeChange, onFind, loading, error, result }) {
  const distanceInKilometers = result
    ? 2 * 6371 * Math.asin(Math.sqrt(
      Math.sin(((result.latitude - Number(latitude)) * Math.PI / 180) / 2) ** 2
      + Math.cos(Number(latitude) * Math.PI / 180) * Math.cos(result.latitude * Math.PI / 180)
      * Math.sin(((result.longitude - Number(longitude)) * Math.PI / 180) / 2) ** 2,
    ))
    : null

  return (
    <section className="panel nearest-hospital-panel" aria-labelledby="nearest-hospital-title">
      <div className="panel-header"><div><span className="eyebrow">MEDICAL DISPATCH</span><h2 id="nearest-hospital-title">Nearest Hospital</h2></div><span className="recommendation-status">{result ? 'Hospital located' : 'Ready to search'}</span></div>
      <p className="recommendation-copy">Locate the closest hospital to a disaster or response location.</p>
      <form className="nearest-hospital-controls" onSubmit={(event) => { event.preventDefault(); onFind() }}>
        <label htmlFor="nearest-hospital-latitude">Disaster latitude<input id="nearest-hospital-latitude" type="number" step="any" min="-90" max="90" value={latitude} onChange={(event) => onLatitudeChange(event.target.value)} /></label>
        <label htmlFor="nearest-hospital-longitude">Disaster longitude<input id="nearest-hospital-longitude" type="number" step="any" min="-180" max="180" value={longitude} onChange={(event) => onLongitudeChange(event.target.value)} /></label>
        <button className="inventory-allocation-button" type="submit" disabled={loading}>{loading ? 'Searching...' : 'Find nearest hospital'}</button>
      </form>
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {loading && <span className="muted">Searching the medical network...</span>}
      {result && !loading && !error && <div className="nearest-hospital-result"><div className="nearest-hospital-heading"><div className="facility-icon"><Icon>✚</Icon></div><div><strong>{result.name}</strong><span>{distanceInKilometers.toFixed(1)} km from disaster location</span></div></div><div className="hospital-detail-grid">{Object.entries(result).map(([field, value]) => <div key={field}><small>{field.replaceAll('_', ' ')}</small><strong>{typeof value === 'boolean' ? (value ? 'Available' : 'Unavailable') : String(value)}</strong></div>)}</div></div>}
      {!loading && !error && !result && <span className="muted">Enter a location to locate the nearest hospital.</span>}
    </section>
  )
}

function AvailableRescueTeams({ teams, loading, error, onRefresh }) {
  return (
    <section className="panel available-teams-panel" aria-labelledby="available-teams-title">
      <div className="panel-header"><div><span className="eyebrow">FIELD PERSONNEL</span><h2 id="available-teams-title">Available Rescue Teams</h2></div><button className="inventory-allocation-button" type="button" onClick={onRefresh} disabled={loading}>{loading ? 'Loading...' : 'Refresh teams'}</button></div>
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {loading && <span className="muted">Loading available rescue teams...</span>}
      {!loading && !error && teams.length === 0 && <span className="muted">No available rescue teams found near the response center.</span>}
      {!loading && !error && teams.length > 0 && <div className="available-team-list">{teams.map((team) => <article className="available-team-card" key={team.team_id}><div className="available-team-summary"><div className="avatar">{(team.name || 'Team').split(' ').map((part) => part[0]).join('').slice(0, 2)}</div><div className="compact-main"><strong>{team.name}</strong><span>{team.team_id} · {team.team_type}</span></div><span className="availability"><i />{team.availability}</span></div><div className="available-team-details">{Object.entries(team).map(([field, value]) => <div key={field}><small>{field.replaceAll('_', ' ')}</small><strong>{Array.isArray(value) ? value.join(' · ') || 'None' : value === null ? 'None' : String(value)}</strong></div>)}</div></article>)}</div>}
    </section>
  )
}

function ResourceAllocationDashboard({ missions, selectedMissionId, onMissionChange, allocations, loading, error, onRefresh, onRelease, onCancel, releasingId, cancellingId, releaseError, cancellationError }) {
  return (
    <section className="panel resource-allocation-dashboard" aria-labelledby="resource-allocation-dashboard-title">
      <div className="panel-header"><div><span className="eyebrow">RESOURCE AUDIT</span><h2 id="resource-allocation-dashboard-title">Resource Allocation Dashboard</h2></div><button className="inventory-allocation-button" type="button" onClick={onRefresh} disabled={!selectedMissionId || loading}>{loading ? 'Refreshing...' : 'Refresh history'}</button></div>
      <div className="allocation-dashboard-controls"><label htmlFor="allocation-dashboard-mission">Mission<select id="allocation-dashboard-mission" value={selectedMissionId} onChange={(event) => onMissionChange(event.target.value)}><option value="">Select a mission</option>{missions.map((mission) => <option value={mission.mission_id} key={mission.mission_id}>{mission.mission_id} · {mission.disaster_id}</option>)}</select></label></div>
      {releaseError && <span className="inventory-feedback inventory-feedback-error">{releaseError}</span>}
      {cancellationError && <span className="inventory-feedback inventory-feedback-error">{cancellationError}</span>}
      {loading && <span className="muted">Loading allocation history...</span>}
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {!selectedMissionId && <span className="muted">Select a mission to view its resource allocations.</span>}
      {selectedMissionId && !loading && !error && allocations.length === 0 && <span className="muted">No resource allocations for this mission.</span>}
      {selectedMissionId && !loading && !error && allocations.length > 0 && <div className="allocation-dashboard-list">{allocations.map((allocation) => <article className="allocation-dashboard-row" key={allocation.allocation_id}><div className="allocation-dashboard-fields"><div><small>ALLOCATION ID</small><strong>{allocation.allocation_id}</strong></div><div><small>RESOURCE ID</small><strong>{allocation.resource_id}</strong></div><div><small>QUANTITY</small><strong>{allocation.quantity}</strong></div><div><small>DISASTER ID</small><strong>{allocation.disaster_id}</strong></div><div><small>ALLOCATED TIME</small><strong>{allocation.allocated_at}</strong></div><div><small>STATUS</small><strong className={`allocation-status ${allocation.status.toLowerCase()}`}>{allocation.status}</strong></div></div>{allocation.status === 'ALLOCATED' && <div className="allocation-actions"><button className="allocation-release-button" type="button" onClick={() => onRelease(allocation.allocation_id)} disabled={releasingId === allocation.allocation_id || cancellingId === allocation.allocation_id}>{releasingId === allocation.allocation_id ? 'Releasing...' : 'Release'}</button><button className="allocation-cancel-button" type="button" onClick={() => onCancel(allocation.allocation_id)} disabled={releasingId === allocation.allocation_id || cancellingId === allocation.allocation_id}>{cancellingId === allocation.allocation_id ? 'Cancelling...' : 'Cancel'}</button></div>}</article>)}</div>}
    </section>
  )
}

function ResourceAllocationWorkspace({ resources, missions, selectedResourceId, allocationQuantity, onResourceChange, onQuantityChange, onAllocateInventory, onAllocateMission, inventoryAllocationDisabled, missionAllocationDisabled, inventoryLoading, missionLoading, inventoryError, missionError, inventoryResult, missionResult, selectedMissionId, onMissionChange, children }) {
  const selectedMission = missions.find((mission) => mission.mission_id === selectedMissionId)
  return <div className="resource-workspace">
    <section className="resource-control-strip"><div className="workflow-step"><span>01</span><div><strong>RECOMMEND</strong><small>Review available supplies</small></div></div><div className="workflow-step"><span>02</span><div><strong>ALLOCATE</strong><small>Commit to this mission</small></div></div><div className="workflow-step"><span>03</span><div><strong>RELEASE / CANCEL</strong><small>Manage mission resources</small></div></div></section>
    <section className="resource-selection-grid"><div><span className="eyebrow">MISSION CONTEXT</span><label htmlFor="workspace-allocation-mission">Mission<select id="workspace-allocation-mission" value={selectedMissionId} onChange={(event) => onMissionChange(event.target.value)}><option value="">Select a mission</option>{missions.map((mission) => <option value={mission.mission_id} key={mission.mission_id}>{mission.mission_id} · {mission.disaster_id}</option>)}</select></label>{selectedMission ? <div className="selected-mission-strip"><strong>{selectedMission.disaster_id}</strong><span>{selectedMission.team_id} · {selectedMission.status} · {selectedMission.priority}</span></div> : <span className="muted">Select a mission to connect resource actions to an operation.</span>}</div><div><span className="eyebrow">AVAILABLE INVENTORY</span><div className="inventory-allocation-controls workspace-inventory-controls"><label htmlFor="workspace-allocation-resource">Resource<select id="workspace-allocation-resource" value={selectedResourceId} onChange={(event) => onResourceChange(event.target.value)}><option value="">Select a resource</option>{resources.map((resource) => <option value={resource.resource_id} key={resource.resource_id}>{resource.name} ({resource.available_quantity} available)</option>)}</select></label><label htmlFor="workspace-allocation-quantity">Quantity<input id="workspace-allocation-quantity" type="number" min="1" value={allocationQuantity} onChange={(event) => onQuantityChange(event.target.value)} /></label><button className="inventory-allocation-button" type="button" onClick={onAllocateInventory} disabled={inventoryAllocationDisabled || inventoryLoading}>{inventoryLoading ? 'Allocating...' : 'Allocate inventory'}</button><button className="inventory-allocation-button" type="button" onClick={onAllocateMission} disabled={missionAllocationDisabled || missionLoading}>{missionLoading ? 'Assigning...' : 'Allocate to mission'}</button></div>{inventoryError && <span className="inventory-feedback inventory-feedback-error">{inventoryError}</span>}{missionError && <span className="inventory-feedback inventory-feedback-error">{missionError}</span>}{inventoryResult && <span className="inventory-feedback inventory-feedback-success">{inventoryResult.quantity} units allocated from inventory.</span>}{missionResult && <span className="inventory-feedback inventory-feedback-success">Resource linked to {missionResult.mission_id}.</span>}</div></section>
    {children}
  </div>
}

const vehicleStatuses = ['AVAILABLE', 'ASSIGNED', 'IN_TRANSIT', 'MAINTENANCE', 'UNAVAILABLE']

function EmergencyVehicleTracking({ vehicles, loading, error, selectedVehicleId, onVehicleChange, latitude, longitude, onLatitudeChange, onLongitudeChange, status, onStatusChange, onRefresh, onUpdateLocation, onUpdateStatus, updateLoading, success, updateError }) {
  return (
    <section className="panel vehicle-tracking-panel" aria-labelledby="vehicle-tracking-title">
      <div className="panel-header"><div><span className="eyebrow">FLEET OPERATIONS</span><h2 id="vehicle-tracking-title">Emergency Vehicle Tracking</h2></div><button className="inventory-allocation-button" type="button" onClick={onRefresh} disabled={loading}>{loading ? 'Loading...' : 'Refresh vehicles'}</button></div>
      {loading && <span className="muted">Loading emergency vehicles...</span>}
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {!loading && !error && vehicles.length === 0 && <span className="muted">No emergency vehicles are currently registered.</span>}
      {!loading && !error && vehicles.length > 0 && <><div className="vehicle-tracking-list">{vehicles.map((vehicle) => <article className={`vehicle-tracking-card ${vehicle.vehicle_id === selectedVehicleId ? 'selected' : ''}`} key={vehicle.vehicle_id}><button type="button" className="vehicle-select-button" onClick={() => onVehicleChange(vehicle.vehicle_id)}><div><strong>{vehicle.name || vehicle.registration_number || vehicle.vehicle_id}</strong><span>{vehicle.vehicle_id} · {vehicle.vehicle_type}</span></div><span className={`availability ${vehicle.status === 'AVAILABLE' ? 'available' : 'standby'}`}><i />{vehicle.status}</span></button><div className="vehicle-tracking-details"><span>LAT <b>{vehicle.latitude}</b></span><span>LON <b>{vehicle.longitude}</b></span><span>MISSION <b>{vehicle.current_mission_id || vehicle.assigned_mission_id || 'Unassigned'}</b></span></div></article>)}</div><div className="vehicle-update-form"><label htmlFor="vehicle-location-latitude">Latitude<input id="vehicle-location-latitude" type="number" step="any" min="-90" max="90" value={latitude} onChange={(event) => onLatitudeChange(event.target.value)} disabled={!selectedVehicleId} /></label><label htmlFor="vehicle-location-longitude">Longitude<input id="vehicle-location-longitude" type="number" step="any" min="-180" max="180" value={longitude} onChange={(event) => onLongitudeChange(event.target.value)} disabled={!selectedVehicleId} /></label><button className="inventory-allocation-button" type="button" onClick={onUpdateLocation} disabled={!selectedVehicleId || updateLoading}>{updateLoading ? 'Updating...' : 'Update location'}</button><label htmlFor="vehicle-status">Status<select id="vehicle-status" value={status} onChange={(event) => onStatusChange(event.target.value)} disabled={!selectedVehicleId}>{vehicleStatuses.map((option) => <option value={option} key={option}>{option}</option>)}</select></label><button className="inventory-allocation-button" type="button" onClick={onUpdateStatus} disabled={!selectedVehicleId || updateLoading}>{updateLoading ? 'Updating...' : 'Update status'}</button></div></>}
      {success && <span className="inventory-feedback inventory-feedback-success">{success}</span>}
      {updateError && <span className="inventory-feedback inventory-feedback-error">{updateError}</span>}
      {!selectedVehicleId && !loading && vehicles.length > 0 && <span className="muted">Select a vehicle to update its location or status.</span>}
    </section>
  )
}

function EmergencyShelterManagement({ shelters, loading, error, selectedShelterId, onShelterChange, capacity, onCapacityChange, nearestLatitude, nearestLongitude, onNearestLatitudeChange, onNearestLongitudeChange, nearestShelter, nearestLoading, nearestError, onFindNearest, onRefresh, onUpdateCapacity, updateLoading, success, updateError }) {
  return (
    <section className="panel shelter-management-panel" aria-labelledby="shelter-management-title">
      <div className="panel-header"><div><span className="eyebrow">EVACUATION NETWORK</span><h2 id="shelter-management-title">Emergency Shelter Management</h2></div><button className="inventory-allocation-button" type="button" onClick={onRefresh} disabled={loading}>{loading ? 'Loading...' : 'Refresh shelters'}</button></div>
      {loading && <span className="muted">Loading emergency shelters...</span>}
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {!loading && !error && shelters.length === 0 && <span className="muted">No emergency shelters are currently registered.</span>}
      {!loading && !error && shelters.length > 0 && <div className="shelter-list">{shelters.map((shelter) => <article className={`shelter-card ${shelter.shelter_id === selectedShelterId ? 'selected' : ''}`} key={shelter.shelter_id}><button type="button" className="shelter-select-button" onClick={() => onShelterChange(shelter.shelter_id)}><div><strong>{shelter.name}</strong><span>{shelter.shelter_id}</span></div><span className={`availability ${shelter.status === 'ACCEPTING_EVACUEES' || shelter.status === 'AVAILABLE' ? 'available' : 'standby'}`}><i />{shelter.status}</span></button><div className="shelter-details"><span>LAT <b>{shelter.latitude}</b></span><span>LON <b>{shelter.longitude}</b></span><span>CAPACITY <b>{shelter.capacity}</b></span><span>AVAILABLE <b>{shelter.available_capacity}</b></span></div></article>)}</div>}
      <div className="shelter-operations"><div className="shelter-operation-block"><span className="eyebrow">NEAREST SHELTER</span><form className="shelter-nearest-controls" onSubmit={(event) => { event.preventDefault(); onFindNearest() }}><label htmlFor="nearest-shelter-latitude">Latitude<input id="nearest-shelter-latitude" type="number" step="any" min="-90" max="90" value={nearestLatitude} onChange={(event) => onNearestLatitudeChange(event.target.value)} /></label><label htmlFor="nearest-shelter-longitude">Longitude<input id="nearest-shelter-longitude" type="number" step="any" min="-180" max="180" value={nearestLongitude} onChange={(event) => onNearestLongitudeChange(event.target.value)} /></label><button className="inventory-allocation-button" type="submit" disabled={nearestLoading}>{nearestLoading ? 'Searching...' : 'Find nearest shelter'}</button></form>{nearestLoading && <span className="muted">Searching available shelters...</span>}{nearestError && <span className="inventory-feedback inventory-feedback-error">{nearestError}</span>}{nearestShelter && !nearestLoading && !nearestError && <div className="nearest-shelter-result"><strong>{nearestShelter.name}</strong><span>{nearestShelter.shelter_id} · {Number(nearestShelter.distance_km).toFixed(1)} km away</span></div>}</div><div className="shelter-operation-block"><span className="eyebrow">CAPACITY CONTROL</span><div className="shelter-capacity-controls"><label htmlFor="shelter-selection">Shelter<select id="shelter-selection" value={selectedShelterId} onChange={(event) => onShelterChange(event.target.value)}><option value="">Select a shelter</option>{shelters.map((shelter) => <option value={shelter.shelter_id} key={shelter.shelter_id}>{shelter.shelter_id} · {shelter.name}</option>)}</select></label><label htmlFor="shelter-available-capacity">Available capacity<input id="shelter-available-capacity" type="number" min="0" value={capacity} onChange={(event) => onCapacityChange(event.target.value)} disabled={!selectedShelterId} /></label><button className="inventory-allocation-button" type="button" onClick={onUpdateCapacity} disabled={!selectedShelterId || updateLoading}>{updateLoading ? 'Updating...' : 'Update capacity'}</button></div></div></div>
      {success && <span className="inventory-feedback inventory-feedback-success">{success}</span>}
      {updateError && <span className="inventory-feedback inventory-feedback-error">{updateError}</span>}
      {!selectedShelterId && !loading && shelters.length > 0 && <span className="muted">Select a shelter to update its available capacity.</span>}
    </section>
  )
}

const missionPriorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

function TeamDeploymentPanel({ teams, missions, hospitals, vehicles, selectedTeamId, onTeamChange, form, onFormChange, onDeploy, loading, error, success, result }) {
  const selectedTeam = teams.find((team) => team.team_id === selectedTeamId)

  return (
    <section className="panel team-deployment-panel" aria-labelledby="team-deployment-title">
      <div className="panel-header"><div><span className="eyebrow">MISSION ASSIGNMENT</span><h2 id="team-deployment-title">Team Deployment</h2></div><span className="recommendation-status">{selectedTeam ? `${selectedTeam.team_id} selected` : 'Select a team'}</span></div>
      <form className="team-deployment-form" onSubmit={(event) => { event.preventDefault(); onDeploy() }}>
        <label htmlFor="deployment-team">Rescue team<select id="deployment-team" value={selectedTeamId} onChange={(event) => onTeamChange(event.target.value)}><option value="">Select an available team</option>{teams.map((team) => <option value={team.team_id} key={team.team_id}>{team.team_id} · {team.name} · {team.team_type} · {team.availability}{team.current_mission_id ? ` · ${team.current_mission_id}` : ''}</option>)}</select></label>
        <label htmlFor="deployment-disaster-id">Disaster ID<input id="deployment-disaster-id" value={form.disasterId} onChange={(event) => onFormChange('disasterId', event.target.value)} placeholder="disaster-001" /></label>
        <label htmlFor="deployment-latitude">Destination latitude<input id="deployment-latitude" type="number" step="any" min="-90" max="90" value={form.destinationLatitude} onChange={(event) => onFormChange('destinationLatitude', event.target.value)} /></label>
        <label htmlFor="deployment-longitude">Destination longitude<input id="deployment-longitude" type="number" step="any" min="-180" max="180" value={form.destinationLongitude} onChange={(event) => onFormChange('destinationLongitude', event.target.value)} /></label>
        <label htmlFor="deployment-priority">Priority<select id="deployment-priority" value={form.priority} onChange={(event) => onFormChange('priority', event.target.value)}>{missionPriorities.map((priority) => <option value={priority} key={priority}>{priority}</option>)}</select></label>
        <label htmlFor="deployment-hospital">Hospital (optional)<select id="deployment-hospital" value={form.hospitalId} onChange={(event) => onFormChange('hospitalId', event.target.value)}><option value="">None</option>{hospitals.map((hospital) => <option value={hospital.hospital_id} key={hospital.hospital_id}>{hospital.hospital_id} · {hospital.name}</option>)}</select></label>
        <label htmlFor="deployment-vehicle">Vehicle (optional)<select id="deployment-vehicle" value={form.vehicleId} onChange={(event) => onFormChange('vehicleId', event.target.value)}><option value="">None</option>{vehicles.map((vehicle) => <option value={vehicle.vehicle_id} key={vehicle.vehicle_id}>{vehicle.vehicle_id} · {vehicle.name || vehicle.registration_number || vehicle.vehicle_id}</option>)}</select></label>
        <button className="inventory-allocation-button" type="submit" disabled={loading || !selectedTeamId}>{loading ? 'Deploying...' : 'Deploy team'}</button>
      </form>
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {success && <span className="inventory-feedback inventory-feedback-success">{success}</span>}
      {!selectedTeamId && <span className="muted">Choose an available team before creating a mission.</span>}
      {result && <div className="deployment-result"><div className="route-result-badge">MISSION CREATED</div><div className="deployment-result-grid"><div><small>MISSION ID</small><strong>{result.mission_id}</strong></div><div><small>ASSIGNED TEAM</small><strong>{result.team_id}</strong></div><div><small>DESTINATION</small><strong>{result.destination_latitude}, {result.destination_longitude}</strong></div><div><small>PRIORITY</small><strong>{result.priority}</strong></div><div><small>STATUS</small><strong>{result.status}</strong></div></div></div>}
      {missions.length > 0 && <span className="muted deployment-mission-count">{missions.length} missions currently loaded.</span>}
    </section>
  )
}

function MissionOperationsDetails({ mission, selectedTeam, hospitals, vehicles, routeResult, allocations, missionAllocationsLoading, missionAllocationsError, onStatusChange, missionUpdatingId, onRelease, onCancel, releasingId, cancellingId }) {
  if (!mission) return null
  const actions = missionStatusActions[mission.status] || []
  const hospital = hospitals.find((item) => item.hospital_id === mission.hospital_id)
  const vehicle = vehicles.find((item) => item.vehicle_id === mission.vehicle_id)
  return <section className="mission-operations-details">
    <div className="mission-result-banner"><div><span className="route-result-badge">MISSION DEPLOYED</span><h3>Mission {mission.mission_id} is active in the operations workspace.</h3></div><span className={`badge ${(mission.priority || 'MEDIUM').toLowerCase()}`}>{mission.priority}</span></div>
    <div className="mission-summary-grid">
      <div><small>MISSION ID</small><strong>{mission.mission_id}</strong></div><div><small>DISASTER ID</small><strong>{mission.disaster_id}</strong></div><div><small>ASSIGNED TEAM</small><strong>{selectedTeam?.name || mission.team_id}</strong><span>{selectedTeam?.team_type || mission.team_id}</span></div><div><small>DESTINATION</small><strong>{mission.destination_latitude}, {mission.destination_longitude}</strong></div><div><small>PRIORITY</small><strong>{mission.priority}</strong></div><div><small>STATUS</small><strong className="status-live">{mission.status}</strong></div><div><small>HOSPITAL</small><strong>{hospital?.name || mission.hospital_id || 'Not linked'}</strong></div><div><small>VEHICLE</small><strong>{vehicle?.name || vehicle?.registration_number || mission.vehicle_id || 'Not linked'}</strong></div><div><small>CREATED</small><strong>{mission.created_at || 'Just now'}</strong></div>
    </div>
    <div className="mission-related-grid">
      <section className="related-section"><PanelHeader eyebrow="MISSION STATUS" title="Status actions" />{missionUpdatingId === mission.mission_id ? <span className="muted">Updating mission status...</span> : <div className="status-actions">{actions.map((action) => <button className="text-button" type="button" key={action.status} onClick={() => onStatusChange(mission.mission_id, action.status)}>{action.label} <span aria-hidden="true">↗</span></button>)}{actions.length === 0 && <span className="muted">No further status actions available.</span>}</div>}</section>
      <section className="related-section"><PanelHeader eyebrow="ROUTE LINK" title="Route information" />{routeResult ? <div className="related-metrics"><span><small>DISTANCE</small><b>{routeResult.data?.distance_km || routeResult.distance_km} km</b></span><span><small>DURATION</small><b>{routeResult.data?.estimated_duration_minutes || routeResult.estimated_duration_minutes} min</b></span><span><small>RISK</small><b>{routeResult.data?.route_risk_score || routeResult.route_risk_score}</b></span></div> : <span className="muted">No route result linked to this mission yet.</span>}</section>
      <section className="related-section mission-resource-history"><PanelHeader eyebrow="MISSION RESOURCES" title="Allocated resources" />{missionAllocationsLoading && <span className="muted">Loading mission allocations...</span>}{missionAllocationsError && <span className="inventory-feedback inventory-feedback-error">{missionAllocationsError}</span>}{!missionAllocationsLoading && !missionAllocationsError && allocations.length === 0 && <span className="muted">No resources allocated to this mission.</span>}{!missionAllocationsLoading && !missionAllocationsError && allocations.map((allocation) => <div className="related-allocation-row" key={allocation.allocation_id}><div><strong>{allocation.resource_id}</strong><span>{allocation.quantity} units · {allocation.status}</span></div>{allocation.status === 'ALLOCATED' && <div className="allocation-actions"><button className="allocation-release-button" type="button" onClick={() => onRelease(allocation.allocation_id)} disabled={releasingId === allocation.allocation_id || cancellingId === allocation.allocation_id}>Release</button><button className="allocation-cancel-button" type="button" onClick={() => onCancel(allocation.allocation_id)} disabled={releasingId === allocation.allocation_id || cancellingId === allocation.allocation_id}>Cancel</button></div>}</div>)}</section>
    </div>
  </section>
}

function RescueRoutePlanning({ originLatitude, originLongitude, destinationLatitude, destinationLongitude, riskTolerance, candidateCount, onChange, onPlan, loading, error, result }) {
  return (
    <section className="panel route-planning-panel" aria-labelledby="route-planning-title">
      <div className="panel-header"><div><span className="eyebrow">RISK-AWARE DISPATCH</span><h2 id="route-planning-title">Rescue Route Planning</h2></div><span className="recommendation-status">{result?.riskAware ? 'Candidate evaluated' : 'Ready to plan'}</span></div>
      <p className="recommendation-copy">Compare travel cost and route risk before dispatching a rescue team.</p>
      <form className="route-planning-controls" onSubmit={(event) => { event.preventDefault(); onPlan() }}>
        <label htmlFor="route-origin-latitude">Origin latitude<input id="route-origin-latitude" type="number" step="any" min="-90" max="90" value={originLatitude} onChange={(event) => onChange('originLatitude', event.target.value)} /></label>
        <label htmlFor="route-origin-longitude">Origin longitude<input id="route-origin-longitude" type="number" step="any" min="-180" max="180" value={originLongitude} onChange={(event) => onChange('originLongitude', event.target.value)} /></label>
        <label htmlFor="route-destination-latitude">Destination latitude<input id="route-destination-latitude" type="number" step="any" min="-90" max="90" value={destinationLatitude} onChange={(event) => onChange('destinationLatitude', event.target.value)} /></label>
        <label htmlFor="route-destination-longitude">Destination longitude<input id="route-destination-longitude" type="number" step="any" min="-180" max="180" value={destinationLongitude} onChange={(event) => onChange('destinationLongitude', event.target.value)} /></label>
        <label htmlFor="route-risk-tolerance">Risk tolerance<input id="route-risk-tolerance" type="number" step="0.01" min="0" max="1" placeholder="0.50" value={riskTolerance} onChange={(event) => onChange('riskTolerance', event.target.value)} /></label>
        <label htmlFor="route-candidate-count">Candidates<input id="route-candidate-count" type="number" min="1" max="6" placeholder="Optional" value={candidateCount} onChange={(event) => onChange('candidateCount', event.target.value)} /></label>
        <button className="inventory-allocation-button" type="submit" disabled={loading}>{loading ? 'Planning...' : 'Plan route'}</button>
      </form>
      {error && <span className="inventory-feedback inventory-feedback-error">{error}</span>}
      {loading && <span className="muted">Evaluating route distance and disaster risk...</span>}
      {result && !loading && !error && <div className="route-planning-result"><div className="route-result-badge">{result.riskAware ? 'RISK-AWARE SELECTION' : 'STANDARD ROUTE'}</div><div className="route-result-metrics"><div><small>DISTANCE</small><strong>{result.data.distance_km} km</strong></div><div><small>DURATION</small><strong>{result.data.estimated_duration_minutes} min</strong></div><div><small>RISK SCORE</small><strong>{result.data.route_risk_score}</strong></div><div><small>STATUS</small><strong>{result.data.route_status}</strong></div></div><p>{result.data.explanation}</p></div>}
    </section>
  )
}

function EmergencyMap({ hospitals, vehicles }) {
  return (
    <MapContainer
      center={[12.9716, 77.5946]}
      zoom={12}
      style={{ height: '400px', width: '100%' }}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={[12.9716, 77.5946]}>
        <Popup>Emergency Response Center</Popup>
      </Marker>
      {(hospitals || []).map((hospital) => (
        <Marker key={hospital.hospital_id} position={[hospital.latitude, hospital.longitude]}>
          <Popup>
            <strong>{hospital.name}</strong>
            <div>{hospital.emergency_available ? 'Emergency Available' : 'Emergency Unavailable'}</div>
            <div>Available beds: {hospital.available_beds}</div>
            <div>Available ICU: {hospital.available_icu}</div>
          </Popup>
        </Marker>
      ))}
      {(vehicles || []).filter((vehicle) => (
        Number.isFinite(vehicle.latitude)
        && Number.isFinite(vehicle.longitude)
        && vehicle.latitude >= -90
        && vehicle.latitude <= 90
        && vehicle.longitude >= -180
        && vehicle.longitude <= 180
      )).map((vehicle) => (
        <Marker key={vehicle.vehicle_id} position={[vehicle.latitude, vehicle.longitude]}>
          <Popup>
            <strong>{vehicle.name || vehicle.registration_number || vehicle.vehicle_id}</strong>
            <div>Vehicle type: {vehicle.vehicle_type}</div>
            <div>Status: {vehicle.status}</div>
            <div>Capacity: {vehicle.capacity}</div>
            <div>Current mission: {vehicle.current_mission_id || vehicle.assigned_mission_id || 'Unassigned'}</div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}

function App() {
  const [currentTime, setCurrentTime] = useState(() => new Date())
  const [activeModule, setActiveModule] = useState('dashboard')
  const [notice, setNotice] = useState('All systems are connected and ready for dispatch.')
  const [hospitals, setHospitals] = useState([])
  const [hospitalsLoading, setHospitalsLoading] = useState(true)
  const [hospitalsError, setHospitalsError] = useState('')
  const [nearestHospitalResult, setNearestHospitalResult] = useState(null)
  const [nearestHospitalLoading, setNearestHospitalLoading] = useState(false)
  const [nearestHospitalError, setNearestHospitalError] = useState('')
  const [nearestHospitalLatitude, setNearestHospitalLatitude] = useState('12.9716')
  const [nearestHospitalLongitude, setNearestHospitalLongitude] = useState('77.5946')
  const [teams, setTeams] = useState([])
  const [teamsLoading, setTeamsLoading] = useState(true)
  const [teamsError, setTeamsError] = useState('')
  const [resources, setResources] = useState([])
  const [resourcesLoading, setResourcesLoading] = useState(true)
  const [resourcesError, setResourcesError] = useState('')
  const [vehicles, setVehicles] = useState([])
  const [vehiclesLoading, setVehiclesLoading] = useState(true)
  const [vehiclesError, setVehiclesError] = useState('')
  const [selectedVehicleId, setSelectedVehicleId] = useState('')
  const [vehicleLatitude, setVehicleLatitude] = useState('')
  const [vehicleLongitude, setVehicleLongitude] = useState('')
  const [vehicleStatus, setVehicleStatus] = useState('AVAILABLE')
  const [vehicleUpdateLoading, setVehicleUpdateLoading] = useState(false)
  const [vehicleUpdateSuccess, setVehicleUpdateSuccess] = useState('')
  const [vehicleUpdateError, setVehicleUpdateError] = useState('')
  const [shelters, setShelters] = useState([])
  const [sheltersLoading, setSheltersLoading] = useState(true)
  const [sheltersError, setSheltersError] = useState('')
  const [selectedShelterId, setSelectedShelterId] = useState('')
  const [shelterCapacity, setShelterCapacity] = useState('')
  const [shelterNearestLatitude, setShelterNearestLatitude] = useState('12.9716')
  const [shelterNearestLongitude, setShelterNearestLongitude] = useState('77.5946')
  const [nearestShelter, setNearestShelter] = useState(null)
  const [nearestShelterLoading, setNearestShelterLoading] = useState(false)
  const [nearestShelterError, setNearestShelterError] = useState('')
  const [shelterUpdateLoading, setShelterUpdateLoading] = useState(false)
  const [shelterUpdateSuccess, setShelterUpdateSuccess] = useState('')
  const [shelterUpdateError, setShelterUpdateError] = useState('')
  const [nearestVehicleResult, setNearestVehicleResult] = useState(null)
  const [nearestVehicleLoading, setNearestVehicleLoading] = useState(false)
  const [nearestVehicleError, setNearestVehicleError] = useState('')
  const [missions, setMissions] = useState([])
  const [missionsLoading, setMissionsLoading] = useState(true)
  const [missionsError, setMissionsError] = useState('')
  const [missionUpdatingId, setMissionUpdatingId] = useState('')
  const [deployLoading, setDeployLoading] = useState(false)
  const [deploymentError, setDeploymentError] = useState('')
  const [deploymentSuccess, setDeploymentSuccess] = useState('')
  const [deploymentResult, setDeploymentResult] = useState(null)
  const [deploymentTeamId, setDeploymentTeamId] = useState('')
  const [deploymentForm, setDeploymentForm] = useState({
    disasterId: 'dashboard-deployment-demo',
    destinationLatitude: '12.9716',
    destinationLongitude: '77.5946',
    priority: 'MEDIUM',
    hospitalId: '',
    vehicleId: '',
  })
  const [routeResult, setRouteResult] = useState(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeError, setRouteError] = useState('')
  const [riskResult, setRiskResult] = useState(null)
  const [riskLoading, setRiskLoading] = useState(false)
  const [riskError, setRiskError] = useState('')
  const [allocationResult, setAllocationResult] = useState(null)
  const [allocationLoading, setAllocationLoading] = useState(false)
  const [allocationError, setAllocationError] = useState('')
  const [recommendationLatitude, setRecommendationLatitude] = useState('12.9716')
  const [recommendationLongitude, setRecommendationLongitude] = useState('77.5946')
  const [recommendationType, setRecommendationType] = useState('')
  const [recommendedResources, setRecommendedResources] = useState([])
  const [recommendationLoading, setRecommendationLoading] = useState(false)
  const [recommendationError, setRecommendationError] = useState('')
  const [routePlanningForm, setRoutePlanningForm] = useState({
    originLatitude: '12.9716',
    originLongitude: '77.5946',
    destinationLatitude: '12.9352',
    destinationLongitude: '77.6245',
    riskTolerance: '',
    candidateCount: '',
  })
  const [routePlanningResult, setRoutePlanningResult] = useState(null)
  const [routePlanningLoading, setRoutePlanningLoading] = useState(false)
  const [routePlanningError, setRoutePlanningError] = useState('')
  const [selectedResourceId, setSelectedResourceId] = useState('')
  const [allocationQuantity, setAllocationQuantity] = useState('')
  const [inventoryAllocationLoading, setInventoryAllocationLoading] = useState(false)
  const [inventoryAllocationError, setInventoryAllocationError] = useState('')
  const [inventoryAllocationResult, setInventoryAllocationResult] = useState(null)
  const [selectedAllocationMissionId, setSelectedAllocationMissionId] = useState('')
  const [missionAllocationLoading, setMissionAllocationLoading] = useState(false)
  const [missionAllocationError, setMissionAllocationError] = useState('')
  const [missionAllocationResult, setMissionAllocationResult] = useState(null)
  const [missionAllocations, setMissionAllocations] = useState([])
  const [missionAllocationsLoading, setMissionAllocationsLoading] = useState(false)
  const [missionAllocationsError, setMissionAllocationsError] = useState('')
  const [releasingAllocationId, setReleasingAllocationId] = useState('')
  const [allocationReleaseError, setAllocationReleaseError] = useState('')
  const [cancellingAllocationId, setCancellingAllocationId] = useState('')
  const [allocationCancellationError, setAllocationCancellationError] = useState('')

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const currentDate = new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(currentTime)
  const currentClock = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(currentTime)
  const currentHour = currentTime.getHours()
  const greeting = currentHour < 12 ? 'Good morning' : currentHour < 18 ? 'Good afternoon' : 'Good evening'

  const fetchVehicles = async () => {
    setVehiclesLoading(true)
    setVehiclesError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/vehicles')

      if (!response.ok) {
        throw new Error(`Emergency vehicle request failed with status ${response.status}`)
      }

      const data = await response.json()
      const nextVehicles = Array.isArray(data) ? data : Array.isArray(data.value) ? data.value : []
      setVehicles(nextVehicles)
      setSelectedVehicleId((currentId) => currentId && nextVehicles.some((vehicle) => vehicle.vehicle_id === currentId) ? currentId : nextVehicles[0]?.vehicle_id || '')
    } catch (error) {
      setVehicles([])
      setVehiclesError(error instanceof Error ? error.message : 'Unable to load emergency vehicles.')
    } finally {
      setVehiclesLoading(false)
    }
  }

  const fetchAvailableTeams = async () => {
    setTeamsLoading(true)
    setTeamsError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/available-team?latitude=12.9716&longitude=77.5946')

      if (!response.ok) {
        throw new Error(`Rescue team request failed with status ${response.status}`)
      }

      const data = await response.json()
      setTeams(Array.isArray(data) ? data : Array.isArray(data.value) ? data.value : [])
    } catch (error) {
      setTeams([])
      setTeamsError(error instanceof Error ? error.message : 'Unable to load rescue teams.')
    } finally {
      setTeamsLoading(false)
    }
  }

  const fetchMissions = async () => {
    setMissionsLoading(true)
    setMissionsError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/missions')
      if (!response.ok) {
        throw new Error(`Mission request failed with status ${response.status}`)
      }

      const data = await response.json()
      setMissions(Array.isArray(data) ? data : Array.isArray(data?.value) ? data.value : [])
    } catch (error) {
      setMissions([])
      setMissionsError(error instanceof Error ? error.message : 'Unable to load active missions.')
    } finally {
      setMissionsLoading(false)
    }
  }

  const fetchShelters = async () => {
    setSheltersLoading(true)
    setSheltersError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/shelters')
      if (!response.ok) {
        throw new Error(`Shelter request failed with status ${response.status}`)
      }

      const data = await response.json()
      const nextShelters = Array.isArray(data) ? data : Array.isArray(data.value) ? data.value : []
      setShelters(nextShelters)
      setSelectedShelterId((currentId) => currentId && nextShelters.some((shelter) => shelter.shelter_id === currentId) ? currentId : nextShelters[0]?.shelter_id || '')
    } catch (error) {
      setShelters([])
      setSheltersError(error instanceof Error ? error.message : 'Unable to load emergency shelters.')
    } finally {
      setSheltersLoading(false)
    }
  }

  useEffect(() => {
    const fetchHospitals = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/hospitals')

        if (!response.ok) {
          throw new Error(`Hospital request failed with status ${response.status}`)
        }

        const data = await response.json()
        setHospitals(data)
      } catch (error) {
        setHospitalsError(error instanceof Error ? error.message : 'Unable to load nearby hospitals.')
      } finally {
        setHospitalsLoading(false)
      }
    }

    const fetchResources = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/available-resources')

        if (!response.ok) {
          throw new Error(`Emergency resource request failed with status ${response.status}`)
        }

        const data = await response.json()
        setResources(Array.isArray(data) ? data : Array.isArray(data.value) ? data.value : [])
      } catch (error) {
        setResources([])
        setResourcesError(error instanceof Error ? error.message : 'Unable to load emergency resources.')
      } finally {
        setResourcesLoading(false)
      }
    }

    fetchHospitals()
    fetchAvailableTeams()
    fetchResources()
    fetchVehicles()
    fetchShelters()
    fetchMissions()
  }, [])

  const fetchMissionAllocations = async (missionId) => {
    if (!missionId) {
      setMissionAllocations([])
      setMissionAllocationsError('')
      setMissionAllocationsLoading(false)
      return
    }

    setMissionAllocationsLoading(true)
    setMissionAllocationsError('')

    try {
      const response = await fetch(`http://127.0.0.1:8000/mission/${missionId}/allocations`)

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || `Mission allocation history request failed with status ${response.status}`)
      }

      const data = await response.json()
      setMissionAllocations(Array.isArray(data) ? data : [])
    } catch (error) {
      setMissionAllocations([])
      setMissionAllocationsError(error instanceof Error ? error.message : 'Unable to load mission allocation history.')
    } finally {
      setMissionAllocationsLoading(false)
    }
  }

  useEffect(() => {
    fetchMissionAllocations(selectedAllocationMissionId)
  }, [selectedAllocationMissionId])

  useEffect(() => {
    const selectedVehicle = vehicles.find((vehicle) => vehicle.vehicle_id === selectedVehicleId)
    if (selectedVehicle) {
      setVehicleLatitude(String(selectedVehicle.latitude))
      setVehicleLongitude(String(selectedVehicle.longitude))
      setVehicleStatus(selectedVehicle.status)
    }
  }, [selectedVehicleId, vehicles])

  useEffect(() => {
    const selectedShelter = shelters.find((shelter) => shelter.shelter_id === selectedShelterId)
    if (selectedShelter) {
      setShelterCapacity(String(selectedShelter.available_capacity))
    }
  }, [selectedShelterId, shelters])

  const handleAction = (action) => setNotice(`${action} queued for command review.`)

  const selectVehicle = (vehicleId) => {
    setSelectedVehicleId(vehicleId)
    setVehicleUpdateSuccess('')
    setVehicleUpdateError('')
  }

  const selectShelter = (shelterId) => {
    setSelectedShelterId(shelterId)
    setShelterUpdateSuccess('')
    setShelterUpdateError('')
  }

  const clearQuickActionResults = () => {
    setNearestHospitalResult(null)
    setNearestHospitalError('')
    setNearestHospitalLoading(false)
    setNearestVehicleResult(null)
    setNearestVehicleError('')
    setNearestVehicleLoading(false)
    setAllocationResult(null)
    setAllocationError('')
    setAllocationLoading(false)
    setDeploymentResult(null)
    setDeploymentError('')
    setDeploymentSuccess('')
    setDeployLoading(false)
    setRouteResult(null)
    setRouteError('')
    setRouteLoading(false)
    setRiskResult(null)
    setRiskError('')
    setRiskLoading(false)
  }

  const findNearestShelter = async () => {
    const latitude = Number(shelterNearestLatitude)
    const longitude = Number(shelterNearestLongitude)
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setNearestShelterError('Enter a valid latitude and longitude.')
      setNearestShelter(null)
      return
    }

    setNearestShelterLoading(true)
    setNearestShelterError('')
    try {
      const response = await fetch(`http://127.0.0.1:8000/nearest-shelter?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}`)
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.detail || `Nearest shelter request failed with status ${response.status}`)
      }
      setNearestShelter(data)
    } catch (error) {
      setNearestShelter(null)
      setNearestShelterError(error instanceof Error ? error.message : 'Unable to find the nearest shelter.')
    } finally {
      setNearestShelterLoading(false)
    }
  }

  const updateShelterCapacity = async () => {
    const capacity = Number(shelterCapacity)
    const selectedShelter = shelters.find((shelter) => shelter.shelter_id === selectedShelterId)
    if (!selectedShelter) {
      setShelterUpdateError('Select a shelter first.')
      return
    }
    if (!Number.isInteger(capacity) || capacity < 0 || capacity > selectedShelter.capacity) {
      setShelterUpdateError(`Enter an available capacity from 0 to ${selectedShelter.capacity}.`)
      return
    }

    setShelterUpdateLoading(true)
    setShelterUpdateSuccess('')
    setShelterUpdateError('')
    try {
      const response = await fetch(`http://127.0.0.1:8000/shelters/${encodeURIComponent(selectedShelterId)}/capacity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ available_capacity: capacity }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.detail || `Shelter capacity update failed with status ${response.status}`)
      }
      setShelterUpdateSuccess(`${data.name || data.shelter_id} capacity updated successfully.`)
      await fetchShelters()
    } catch (error) {
      setShelterUpdateError(error instanceof Error ? error.message : 'Unable to update shelter capacity.')
    } finally {
      setShelterUpdateLoading(false)
    }
  }

  const updateVehicle = async (operation) => {
    const latitude = Number(vehicleLatitude)
    const longitude = Number(vehicleLongitude)

    if (!selectedVehicleId) {
      setVehicleUpdateError('Select a vehicle first.')
      return
    }

    if (operation === 'location' && (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180)) {
      setVehicleUpdateError('Enter a valid latitude and longitude.')
      return
    }

    setVehicleUpdateLoading(true)
    setVehicleUpdateSuccess('')
    setVehicleUpdateError('')

    try {
      const response = await fetch(`http://127.0.0.1:8000/vehicles/${encodeURIComponent(selectedVehicleId)}/${operation}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(operation === 'location' ? { latitude, longitude } : { status: vehicleStatus }),
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.detail || `Vehicle ${operation} update failed with status ${response.status}`)
      }

      setVehicleUpdateSuccess(`${data.name || data.vehicle_id} ${operation} updated successfully.`)
      await fetchVehicles()
    } catch (error) {
      setVehicleUpdateError(error instanceof Error ? error.message : `Unable to update vehicle ${operation}.`)
    } finally {
      setVehicleUpdateLoading(false)
    }
  }
  

  const findNearestHospital = async () => {
    navigateTo('hospital')
    clearQuickActionResults()
    const latitude = Number(nearestHospitalLatitude)
    const longitude = Number(nearestHospitalLongitude)

    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setNearestHospitalError('Enter a valid latitude and longitude.')
      setNearestHospitalResult(null)
      return
    }

    setNearestHospitalLoading(true)
    setNearestHospitalError('')

    try {
      const response = await fetch(`http://127.0.0.1:8000/nearest-hospital?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}`)

      if (!response.ok) {
        throw new Error(`Nearest hospital request failed with status ${response.status}`)
      }

      const data = await response.json()
      setNearestHospitalResult(data)
      setNotice(`Nearest hospital: ${data.name}.`)
    } catch (error) {
      setNearestHospitalError(error instanceof Error ? error.message : 'Unable to find nearest hospital.')
    } finally {
      setNearestHospitalLoading(false)
    }
  }

  const findNearestVehicle = async () => {
    navigateTo('vehicles')
    clearQuickActionResults()
    setNearestVehicleLoading(true)
    setNearestVehicleError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/nearest-vehicle?latitude=12.9716&longitude=77.5946')

      if (!response.ok) {
        throw new Error(`Nearest vehicle request failed with status ${response.status}`)
      }

      const data = await response.json()
      setNearestVehicleResult(data)
      setNotice(`Nearest vehicle: ${data.registration_number}.`)
    } catch (error) {
      setNearestVehicleError(error instanceof Error ? error.message : 'Unable to find nearest vehicle.')
    } finally {
      setNearestVehicleLoading(false)
    }
  }

  const deployTeam = async () => {
    navigateTo('deployment')
    clearQuickActionResults()
    const destinationLatitude = Number(deploymentForm.destinationLatitude)
    const destinationLongitude = Number(deploymentForm.destinationLongitude)

    if (!deploymentTeamId) {
      setDeploymentError('Select a rescue team before deploying.')
      return
    }
    if (!deploymentForm.disasterId.trim()) {
      setDeploymentError('Enter a disaster ID before deploying.')
      return
    }
    if (!Number.isFinite(destinationLatitude) || destinationLatitude < -90 || destinationLatitude > 90 || !Number.isFinite(destinationLongitude) || destinationLongitude < -180 || destinationLongitude > 180) {
      setDeploymentError('Enter a valid destination latitude and longitude.')
      return
    }

    setDeployLoading(true)
    setDeploymentError('')
    setDeploymentSuccess('')
    setDeploymentResult(null)

    try {
      const response = await fetch('http://127.0.0.1:8000/deploy-team', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: deploymentTeamId,
          disaster_id: deploymentForm.disasterId.trim(),
          destination_latitude: destinationLatitude,
          destination_longitude: destinationLongitude,
          priority: deploymentForm.priority,
          hospital_id: deploymentForm.hospitalId || null,
          vehicle_id: deploymentForm.vehicleId || null,
        }),
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.detail || `Team deployment failed with status ${response.status}`)
      }

      setDeploymentResult(data)
      setSelectedAllocationMissionId(data.mission_id)
      setDeploymentSuccess(`Mission ${data.mission_id} created successfully.`)
      setNotice(`Mission ${data.mission_id} assigned to ${data.team_id}.`)
      await Promise.all([fetchAvailableTeams(), fetchMissions()])
    } catch (error) {
      setDeploymentError(error instanceof Error ? error.message : 'Unable to deploy rescue team.')
    } finally {
      setDeployLoading(false)
    }
  }

  const allocateResource = async () => {
    navigateTo('allocation')
    clearQuickActionResults()
    setAllocationLoading(true)
    setAllocationError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/allocate-resource', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          disaster_id: 'dashboard-allocation-demo',
          disaster_type: 'FLOOD',
          latitude: 12.9716,
          longitude: 77.5946,
          severity: 4,
          required_specialization: null,
        }),
      })

      if (!response.ok) {
        throw new Error(`Resource allocation request failed with status ${response.status}`)
      }

      const data = await response.json()
      setAllocationResult(data)
      setNotice(`Resources allocated: ${data.recommended_hospital.name} and ${data.recommended_rescue_team.name}.`)
    } catch (error) {
      setAllocationError(error instanceof Error ? error.message : 'Unable to allocate resources.')
    } finally {
      setAllocationLoading(false)
    }
  }

  const recommendResources = async () => {
    const latitude = Number(recommendationLatitude)
    const longitude = Number(recommendationLongitude)

    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setRecommendationError('Enter a valid latitude and longitude.')
      setRecommendedResources([])
      return
    }

    setRecommendationLoading(true)
    setRecommendationError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/allocate-resource', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          disaster_id: 'dashboard-resource-search',
          disaster_type: 'RESOURCE_SEARCH',
          latitude,
          longitude,
          severity: 3,
          required_specialization: null,
          ...(recommendationType ? { resource_type: recommendationType } : {}),
        }),
      })

      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.detail?.message || data?.detail || `Resource recommendation failed with status ${response.status}`)
      }

      setRecommendedResources(Array.isArray(data?.recommended_resources) ? data.recommended_resources : [])
    } catch (error) {
      setRecommendedResources([])
      setRecommendationError(error instanceof Error ? error.message : 'Unable to recommend emergency resources.')
    } finally {
      setRecommendationLoading(false)
    }
  }

  const allocateResourceInventory = async () => {
    const selectedResource = resources.find((resource) => String(resource.resource_id) === selectedResourceId)
    const quantity = Number(allocationQuantity)

    if (!selectedResource) {
      setInventoryAllocationError('Select a resource before allocating.')
      return
    }

    if (!Number.isInteger(quantity) || quantity < 1 || quantity > selectedResource.available_quantity) {
      setInventoryAllocationError(`Enter a quantity from 1 to ${selectedResource.available_quantity}.`)
      return
    }

    setInventoryAllocationLoading(true)
    setInventoryAllocationError('')
    setInventoryAllocationResult(null)

    try {
      const response = await fetch('http://127.0.0.1:8000/allocate-resource-inventory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_id: selectedResourceId,
          quantity,
        }),
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.detail || `Inventory allocation request failed with status ${response.status}`)
      }

      setResources((currentResources) => currentResources.map((resource) => (
        resource.resource_id === data.resource_id ? data : resource
      )))
      setAllocationQuantity('')
      setInventoryAllocationResult({ resourceName: data.name || selectedResource.name, quantity })
    } catch (error) {
      setInventoryAllocationError(error instanceof Error ? error.message : 'Unable to allocate resource inventory.')
    } finally {
      setInventoryAllocationLoading(false)
    }
  }

  const allocateResourceToMission = async () => {
    const selectedResource = resources.find((resource) => String(resource.resource_id) === selectedResourceId)
    const quantity = Number(allocationQuantity)

    if (!selectedAllocationMissionId) {
      setMissionAllocationError('Select a mission before allocating.')
      return
    }

    if (!selectedResource) {
      setMissionAllocationError('Select a resource before allocating.')
      return
    }

    if (!Number.isInteger(quantity) || quantity < 1 || quantity > selectedResource.available_quantity) {
      setMissionAllocationError(`Enter a quantity from 1 to ${selectedResource.available_quantity}.`)
      return
    }

    setMissionAllocationLoading(true)
    setMissionAllocationError('')
    setMissionAllocationResult(null)

    try {
      const response = await fetch('http://127.0.0.1:8000/allocate-resource-to-mission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mission_id: selectedAllocationMissionId,
          resource_id: selectedResourceId,
          quantity,
        }),
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.detail || `Mission resource allocation request failed with status ${response.status}`)
      }

      setResources((currentResources) => currentResources.map((resource) => (
        String(resource.resource_id) === String(data.resource_id)
          ? { ...resource, available_quantity: resource.available_quantity - data.quantity }
          : resource
      )))
      setAllocationQuantity('')
      setMissionAllocationResult(data)
      await fetchMissionAllocations(selectedAllocationMissionId)
    } catch (error) {
      setMissionAllocationError(error instanceof Error ? error.message : 'Unable to allocate resource to mission.')
    } finally {
      setMissionAllocationLoading(false)
    }
  }

  const releaseResourceAllocation = async (allocationId) => {
    setReleasingAllocationId(allocationId)
    setAllocationReleaseError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/release-resource-allocation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allocation_id: allocationId }),
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.detail || `Resource release request failed with status ${response.status}`)
      }

      setResources((currentResources) => currentResources.map((resource) => (
        String(resource.resource_id) === String(data.resource_id)
          ? { ...resource, available_quantity: resource.available_quantity + data.quantity }
          : resource
      )))
      await fetchMissionAllocations(selectedAllocationMissionId)
    } catch (error) {
      setAllocationReleaseError(error instanceof Error ? error.message : 'Unable to release resource allocation.')
    } finally {
      setReleasingAllocationId('')
    }
  }

  const cancelResourceAllocation = async (allocationId) => {
    setCancellingAllocationId(allocationId)
    setAllocationCancellationError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/cancel-resource-allocation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allocation_id: allocationId }),
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.detail || `Resource cancellation request failed with status ${response.status}`)
      }

      setMissionAllocations((currentAllocations) => currentAllocations.map((allocation) => (
        allocation.allocation_id === data.allocation_id
          ? { ...allocation, status: data.status }
          : allocation
      )))
      await fetchMissionAllocations(selectedAllocationMissionId)
    } catch (error) {
      setAllocationCancellationError(error instanceof Error ? error.message : 'Unable to cancel resource allocation.')
    } finally {
      setCancellingAllocationId('')
    }
  }

  const optimizeRoute = async () => {
    navigateTo('route')
    clearQuickActionResults()
    setRouteLoading(true)
    setRouteError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/calculate-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin_latitude: 12.9716,
          origin_longitude: 77.5946,
          destination_latitude: 12.9352,
          destination_longitude: 77.6245,
          disaster_id: 'dashboard-route-demo',
        }),
      })

      if (!response.ok) {
        throw new Error(`Route request failed with status ${response.status}`)
      }

      const data = await response.json()
      setRouteResult(data)
      setNotice(`Route optimized: ${data.distance_km} km, ${data.estimated_duration_minutes} min.`)
    } catch (error) {
      setRouteError(error instanceof Error ? error.message : 'Unable to optimize route.')
    } finally {
      setRouteLoading(false)
    }
  }

  const calculateRiskPriority = async () => {
    navigateTo('dashboard')
    clearQuickActionResults()
    setRiskLoading(true)
    setRiskError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/risk-priority', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          disaster_id: 'dashboard-risk-demo',
          disaster_type: 'FLOOD',
          latitude: 12.9716,
          longitude: 77.5946,
          severity: 4,
          affected_population: 5000,
          critical_infrastructure: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`Risk priority request failed with status ${response.status}`)
      }

      const data = await response.json()
      setRiskResult(data)
      setNotice(`Risk priority calculated: ${data.priority_level}, risk score ${data.risk_score}.`)
    } catch (error) {
      setRiskError(error instanceof Error ? error.message : 'Unable to calculate risk priority.')
    } finally {
      setRiskLoading(false)
    }
  }

  const planRescueRoute = async () => {
    const originLatitude = Number(routePlanningForm.originLatitude)
    const originLongitude = Number(routePlanningForm.originLongitude)
    const destinationLatitude = Number(routePlanningForm.destinationLatitude)
    const destinationLongitude = Number(routePlanningForm.destinationLongitude)
    const riskTolerance = routePlanningForm.riskTolerance === '' ? undefined : Number(routePlanningForm.riskTolerance)
    const candidateCount = routePlanningForm.candidateCount === '' ? 0 : Number(routePlanningForm.candidateCount)

    const validLatitude = (value) => Number.isFinite(value) && value >= -90 && value <= 90
    const validLongitude = (value) => Number.isFinite(value) && value >= -180 && value <= 180
    if (!validLatitude(originLatitude) || !validLongitude(originLongitude) || !validLatitude(destinationLatitude) || !validLongitude(destinationLongitude)) {
      setRoutePlanningError('Enter valid origin and destination coordinates.')
      setRoutePlanningResult(null)
      return
    }
    if (riskTolerance !== undefined && (!Number.isFinite(riskTolerance) || riskTolerance < 0 || riskTolerance > 1)) {
      setRoutePlanningError('Risk tolerance must be between 0 and 1.')
      setRoutePlanningResult(null)
      return
    }
    if (!Number.isInteger(candidateCount) || candidateCount < 0 || candidateCount > 6) {
      setRoutePlanningError('Candidate count must be between 1 and 6, or left blank.')
      setRoutePlanningResult(null)
      return
    }

    const radians = (value) => value * Math.PI / 180
    const latitudeDelta = radians(destinationLatitude - originLatitude)
    const longitudeDelta = radians(destinationLongitude - originLongitude)
    const originLatitudeRadians = radians(originLatitude)
    const destinationLatitudeRadians = radians(destinationLatitude)
    const haversine = 2 * 6371 * Math.asin(Math.sqrt(
      Math.sin(latitudeDelta / 2) ** 2
      + Math.cos(originLatitudeRadians) * Math.cos(destinationLatitudeRadians) * Math.sin(longitudeDelta / 2) ** 2,
    ))
    const candidates = candidateCount > 0
      ? Array.from({ length: candidateCount }, (_, index) => ({
        route_id: `dashboard-route-${index + 1}`,
        distance_km: Number((haversine * (1 + index * 0.06)).toFixed(2)),
        estimated_duration_minutes: Number(((haversine * (1 + index * 0.06) / 35) * 60).toFixed(2)),
        route_risk_score: Number(Math.max(0.08, 0.42 - index * 0.07).toFixed(4)),
      }))
      : undefined

    setRoutePlanningLoading(true)
    setRoutePlanningError('')
    try {
      const response = await fetch('http://127.0.0.1:8000/calculate-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin_latitude: originLatitude,
          origin_longitude: originLongitude,
          destination_latitude: destinationLatitude,
          destination_longitude: destinationLongitude,
          ...(riskTolerance !== undefined ? { risk_tolerance: riskTolerance } : {}),
          ...(candidates ? { route_candidates: candidates } : {}),
        }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.detail || `Route planning request failed with status ${response.status}`)
      }
      setRoutePlanningResult({ data, riskAware: Boolean(candidates) })
    } catch (error) {
      setRoutePlanningResult(null)
      setRoutePlanningError(error instanceof Error ? error.message : 'Unable to plan rescue route.')
    } finally {
      setRoutePlanningLoading(false)
    }
  }

  const updateMissionStatus = async (missionId, newStatus) => {
    setMissionUpdatingId(missionId)

    try {
      const response = await fetch(`http://127.0.0.1:8000/mission/${missionId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })

      if (!response.ok) {
        throw new Error(`Mission update failed with status ${response.status}`)
      }

      const updatedMission = await response.json()
      setMissions((currentMissions) => currentMissions.map((mission) => (
        mission.mission_id === missionId ? updatedMission : mission
      )))
      setNotice(`Mission ${missionId} updated to ${newStatus}.`)
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Unable to update mission status.')
    } finally {
      setMissionUpdatingId('')
    }
  }

  const selectedResource = resources.find((resource) => String(resource.resource_id) === selectedResourceId)
  const inventoryQuantity = Number(allocationQuantity)
  const inventoryAllocationDisabled = inventoryAllocationLoading
    || !selectedResource
    || !Number.isInteger(inventoryQuantity)
    || inventoryQuantity < 1
    || inventoryQuantity > selectedResource.available_quantity
  const missionAllocationDisabled = missionAllocationLoading
    || !selectedAllocationMissionId
    || !selectedResource
    || !Number.isInteger(inventoryQuantity)
    || inventoryQuantity < 1
    || inventoryQuantity > selectedResource.available_quantity

  const navigateTo = (moduleId) => {
    setActiveModule(moduleId)
    document.getElementById(moduleId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  useEffect(() => {
    const sections = navigationItems.map((item) => document.getElementById(item.id)).filter(Boolean)
    const updateActiveSection = () => {
      const visibleSections = sections.map((section) => ({ section, rect: section.getBoundingClientRect() })).filter(({ rect }) => rect.bottom > 132 && rect.top < window.innerHeight)
      const currentSection = visibleSections.filter(({ rect }) => rect.top < 132).sort((first, second) => second.rect.top - first.rect.top)[0]
      const selectedSection = currentSection || visibleSections.sort((first, second) => first.rect.top - second.rect.top)[0]
      if (selectedSection) setActiveModule(selectedSection.section.id)
    }
    const observer = new IntersectionObserver(updateActiveSection, { rootMargin: '-132px 0px -20% 0px', threshold: [0.05, 0.35, 0.7] })
    const handleScroll = () => updateActiveSection()
    window.addEventListener('scroll', handleScroll, { passive: true })
    sections.forEach((section) => observer.observe(section))
    updateActiveSection()
    return () => {
      window.removeEventListener('scroll', handleScroll)
      observer.disconnect()
    }
  }, [])

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand-lockup"><div className="brand-mark"><Icon>✦</Icon></div><div><strong>GeoGuardian <em>AI</em></strong><span>Emergency Rescue Command Center</span></div></div><div className="topbar-meta"><div className="command-time"><span className="live-clock"><i className="pulse-dot" /> LIVE</span><strong>{currentClock}</strong><small>{currentDate}</small></div><div className="system-status"><span className="pulse-dot" /><span><small>SYSTEM STATUS</small>Operational</span></div><button className="profile-button" type="button" aria-label="Open user profile">AC<span>▾</span></button></div></header>
      <div className="workspace-shell">
        <div className="dashboard-content">
        <section className="welcome-row"><div><span className="eyebrow">COMMAND CENTER / OVERVIEW</span><h1>{greeting}, Commander.</h1><p>Real-time operational overview for the metropolitan response network.</p></div><div className="weather"><span className="weather-icon">☼</span><div><strong>28°C</strong><span>Clear skies · Visibility 12 km</span></div></div></section>
        <nav className="module-nav" aria-label="Command center sections">{navigationItems.map((item) => <button key={item.id} type="button" className={activeModule === item.id ? 'active' : ''} aria-current={activeModule === item.id ? 'location' : undefined} onClick={() => navigateTo(item.id)}><Icon>{item.icon}</Icon><span>{item.label}</span></button>)}</nav>
        <section id="dashboard" className="page-section dashboard-section"><section className="metrics-grid" aria-label="Operational summary"><MetricCard label="Active Missions" value="12" detail="3 critical priority" icon="⌁" tone="red" /><MetricCard label="Rescue Teams" value="08" detail="of 14 total teams" icon="♙" tone="teal" /><MetricCard label="Available Vehicles" value="23" detail="4 currently deployed" icon="▣" tone="blue" /><MetricCard label="Emergency Resources" value="94%" detail="Readiness level" icon="◈" tone="amber" /></section>
        <div className="command-grid"><section className="panel missions-panel"><PanelHeader eyebrow="LIVE OPERATIONS" title="Active Missions" action="View all missions" /><div className="mission-list">{missionsLoading && <span className="muted">Loading active missions...</span>}{missionsError && <span className="muted">{missionsError}</span>}{!missionsLoading && !missionsError && missions.length === 0 && <span className="muted">No active missions.</span>}{!missionsLoading && !missionsError && missions.map((mission) => { const priority = mission.priority || 'MEDIUM'; const tone = priority.toLowerCase(); const actions = missionStatusActions[mission.status] || []; const isUpdating = missionUpdatingId === mission.mission_id; return <article className="mission-row" key={mission.mission_id}><div className={`priority-line ${tone}`} /><div className="mission-main"><div className="row-heading"><strong>{mission.disaster_id}</strong><span className={`badge ${tone}`}>{priority}</span></div><span className="muted">{mission.mission_id} · {mission.status}</span></div><div className="mission-eta"><small>STATUS</small><strong>{mission.status}</strong></div>{isUpdating ? <span className="muted">Updating...</span> : actions.map((action) => <button className="text-button" type="button" onClick={() => updateMissionStatus(mission.mission_id, action.status)} disabled={missionUpdatingId !== ''} key={action.status}>{action.label}</button>)}<button className="row-arrow" type="button" aria-label={`Open ${mission.mission_id}`}>↗</button></article> })}</div></section><section className="panel map-panel"><PanelHeader eyebrow="GEOSPATIAL VIEW" title="Emergency Response Map" /><div className="map-placeholder"><EmergencyMap hospitals={hospitals} vehicles={vehicles} /></div><div className="map-footer"><span><i className="legend-dot critical" /> Active incidents</span><span><i className="legend-dot hospital" /> Hospitals</span><span><i className="legend-dot team" /> Rescue teams</span><span><i className="legend-dot vehicle" /> Emergency vehicles</span></div></section></div>
        <div className="lower-grid"><section className="panel"><PanelHeader eyebrow="MEDICAL NETWORK" title="Nearby Hospitals" action="View network" /><div className="compact-list">{hospitalsLoading && <span className="muted">Loading nearby hospitals...</span>}{hospitalsError && <span className="muted">{hospitalsError}</span>}{!hospitalsLoading && !hospitalsError && hospitals.map((hospital) => <article className="compact-row" key={hospital.hospital_id}><div className={`facility-icon ${hospital.emergency_available ? 'green' : 'amber'}`}><Icon>✚</Icon></div><div className="compact-main"><strong>{hospital.name}</strong><span>{hospital.emergency_available ? 'Emergency Available' : 'Emergency Unavailable'} · {hospital.available_beds} beds available</span></div><span className="distance">Nearest<br /><small>away</small></span></article>)}</div></section><section className="panel"><PanelHeader eyebrow="FIELD PERSONNEL" title="Rescue Teams" action="Manage teams" /><div className="compact-list">{teamsLoading && <span className="muted">Loading rescue teams...</span>}{teamsError && <span className="muted">{teamsError}</span>}{!teamsLoading && !teamsError && teams.map((team) => <article className="compact-row" key={team.team_id}><div className={`avatar ${team.availability === 'AVAILABLE' ? 'teal' : 'orange'}`}>{(team.name || 'Team').split(' ').map((part) => part[0]).join('').slice(0, 2)}</div><div className="compact-main"><strong>{team.name}</strong><span>{(team.specialization || ['General Response']).join(' · ')} · {team.members} members</span></div><span className={`availability ${team.availability === 'AVAILABLE' ? 'available' : 'standby'}`}><i />{team.availability}</span></article>)}</div></section><section className="panel"><PanelHeader eyebrow="SUPPLY INVENTORY" title="Emergency Resources" action="View inventory" /><div className="inventory-allocation-controls"><label htmlFor="inventory-resource">Resource<select id="inventory-resource" value={selectedResourceId} onChange={(event) => { setSelectedResourceId(event.target.value); setInventoryAllocationError(''); setInventoryAllocationResult(null); setMissionAllocationError(''); setMissionAllocationResult(null) }}><option value="">Select a resource</option>{resources.map((resource) => <option value={resource.resource_id} key={resource.resource_id}>{resource.name} ({resource.available_quantity} available)</option>)}</select></label><label htmlFor="allocation-mission">Mission<select id="allocation-mission" value={selectedAllocationMissionId} onChange={(event) => { setSelectedAllocationMissionId(event.target.value); setMissionAllocationError(''); setMissionAllocationResult(null) }}><option value="">Select a mission</option>{missions.map((mission) => <option value={mission.mission_id} key={mission.mission_id}>{mission.mission_id} — {mission.disaster_id} — {mission.status}</option>)}</select></label><label htmlFor="inventory-quantity">Quantity<input id="inventory-quantity" type="number" min="1" max={selectedResource?.available_quantity} value={allocationQuantity} onChange={(event) => { setAllocationQuantity(event.target.value); setInventoryAllocationError(''); setInventoryAllocationResult(null); setMissionAllocationError(''); setMissionAllocationResult(null) }} /></label><button className="inventory-allocation-button" type="button" onClick={allocateResourceInventory} disabled={inventoryAllocationDisabled}>{inventoryAllocationLoading ? 'Allocating...' : 'Allocate inventory'}</button><button className="inventory-allocation-button" type="button" onClick={allocateResourceToMission} disabled={missionAllocationDisabled}>{missionAllocationLoading ? 'Allocating...' : 'Allocate to Mission'}</button></div>{inventoryAllocationError && <span className="inventory-feedback inventory-feedback-error">{inventoryAllocationError}</span>}{inventoryAllocationResult && <span className="inventory-feedback inventory-feedback-success">Allocated {inventoryAllocationResult.quantity} {inventoryAllocationResult.resourceName}.</span>}{missionAllocationError && <span className="inventory-feedback inventory-feedback-error">{missionAllocationError}</span>}{missionAllocationResult && <span className="inventory-feedback inventory-feedback-success">Allocated {missionAllocationResult.quantity} {selectedResource?.name || missionAllocationResult.resource_id} to {missionAllocationResult.mission_id}.</span>}<div className="resource-list">{resourcesLoading && <span className="muted">Loading emergency resources...</span>}{resourcesError && <span className="muted">{resourcesError}</span>}{!resourcesLoading && !resourcesError && resources.map((resource) => { const resourceType = (resource.resource_type || '').toUpperCase(); const tone = resourceType.includes('MEDICAL') ? 'red' : resourceType.includes('BLANKET') ? 'cyan' : 'blue'; const icon = resourceType.includes('MEDICAL') ? '✚' : resourceType.includes('WATER') ? '◒' : '▱'; return <article className="resource-row" key={resource.resource_id}><div className={`resource-icon ${tone}`}><Icon>{icon}</Icon></div><div><strong>{resource.name}</strong><span>{resource.resource_type}</span></div><b>{resource.available_quantity}</b></article>})}</div></section><section className="panel"><PanelHeader eyebrow="VEHICLE TRACKING" title="Emergency Vehicles" action="View fleet" /><div className="compact-list">{vehiclesLoading && <span className="muted">Loading emergency vehicles...</span>}{vehiclesError && <span className="muted">{vehiclesError}</span>}{!vehiclesLoading && !vehiclesError && vehicles.map((vehicle) => <article className="compact-row" key={vehicle.vehicle_id}><div className={`facility-icon ${vehicle.status === 'AVAILABLE' ? 'green' : 'amber'}`}><Icon>▣</Icon></div><div className="compact-main"><strong>{vehicle.registration_number}</strong><span>{vehicle.vehicle_type} · {vehicle.status} · Capacity: {vehicle.capacity} · Mission: {vehicle.assigned_mission_id || 'Unassigned'}</span></div><span className={`availability ${vehicle.status === 'AVAILABLE' ? 'available' : 'standby'}`}><i />{vehicle.status}</span></article>)}</div></section></div>
        <section className="quick-actions"><div><span className="eyebrow">COMMAND CONSOLE</span><h2>Quick Actions</h2><p className="notice"><span className="pulse-dot" />{notice}</p></div><div className="action-buttons">{['Allocate Resource', 'Deploy Team', 'Find Nearest Hospital', 'Find Nearest Vehicle', 'Optimize Route', 'Calculate Risk Priority'].map((action, index) => <button type="button" className={`action-button action-${index}`} onClick={() => action === 'Allocate Resource' ? allocateResource() : action === 'Deploy Team' ? deployTeam() : action === 'Find Nearest Hospital' ? findNearestHospital() : action === 'Find Nearest Vehicle' ? findNearestVehicle() : action === 'Optimize Route' ? optimizeRoute() : action === 'Calculate Risk Priority' ? calculateRiskPriority() : handleAction(action)} disabled={(action === 'Deploy Team' && deployLoading) || (action === 'Find Nearest Hospital' && nearestHospitalLoading) || (action === 'Find Nearest Vehicle' && nearestVehicleLoading) || (action === 'Calculate Risk Priority' && riskLoading)} key={action}><span>{['＋', '↗', '✚', '▣', '⌁', '⚠'][index]}</span>{action}<b>→</b></button>)}</div>{nearestHospitalLoading && <span className="muted">Finding nearest hospital...</span>}{nearestHospitalError && <span className="muted">{nearestHospitalError}</span>}{nearestHospitalResult && !nearestHospitalLoading && !nearestHospitalError && <div><strong>Nearest Hospital Result</strong><div><span>Hospital: {nearestHospitalResult.name}</span><span>Available beds: {nearestHospitalResult.available_beds}</span><span>Available ICU: {nearestHospitalResult.available_icu}</span><span>Emergency availability: {nearestHospitalResult.emergency_available ? 'Available' : 'Unavailable'}</span></div></div>}{nearestVehicleLoading && <span className="muted">Finding nearest vehicle...</span>}{nearestVehicleError && <span className="muted">{nearestVehicleError}</span>}{nearestVehicleResult && !nearestVehicleLoading && !nearestVehicleError && <div><strong>Nearest Vehicle Result</strong><div><span>Registration number: {nearestVehicleResult.registration_number}</span><span>Vehicle type: {nearestVehicleResult.vehicle_type}</span><span>Status: {nearestVehicleResult.status}</span><span>Capacity: {nearestVehicleResult.capacity}</span><span>Assigned mission: {nearestVehicleResult.assigned_mission_id || "Unassigned"}</span></div></div>}{allocationLoading && <span className="muted">Allocating resources...</span>}{allocationError && <span className="muted">{allocationError}</span>}{allocationResult && !allocationLoading && !allocationError && <div><strong>Allocation Result</strong><div><span>Hospital: {allocationResult.recommended_hospital.name}</span><span>Rescue Team: {allocationResult.recommended_rescue_team.name}</span><span>Priority Score: {allocationResult.priority_score}</span><span>Estimated Distance: {allocationResult.estimated_distance_km} km</span></div><p>{allocationResult.reasoning}</p></div>}{routeLoading && <span className="muted">Optimizing route...</span>}{routeError && <span className="muted">{routeError}</span>}{routeResult && !routeLoading && !routeError && <div><strong>Route Result</strong><div><span>{routeResult.distance_km} km</span><span>{routeResult.estimated_duration_minutes} min</span><span>{Number(routeResult.route_risk_score).toFixed(2)}</span><span>{routeResult.route_status}</span></div><p>{routeResult.explanation}</p></div>}{riskLoading && <span className="muted">Calculating risk priority...</span>}{riskError && <span className="muted">{riskError}</span>}{riskResult && !riskLoading && !riskError && <div><strong>Risk Priority Result</strong><div><span>{riskResult.risk_score}</span><span>{riskResult.priority_level}</span></div><p>{riskResult.reasoning}</p></div>}</section>
        </section>
        <section id="hospital" className="page-section"><ModuleHeader moduleId="hospital" /><NearestHospital latitude={nearestHospitalLatitude} longitude={nearestHospitalLongitude} onLatitudeChange={setNearestHospitalLatitude} onLongitudeChange={setNearestHospitalLongitude} onFind={findNearestHospital} loading={nearestHospitalLoading} error={nearestHospitalError} result={nearestHospitalResult} /></section>
        <section id="resources" className="page-section"><ModuleHeader moduleId="resources" /><RecommendedResources latitude={recommendationLatitude} longitude={recommendationLongitude} resourceType={recommendationType} onLatitudeChange={setRecommendationLatitude} onLongitudeChange={setRecommendationLongitude} onResourceTypeChange={setRecommendationType} onRecommend={recommendResources} loading={recommendationLoading} error={recommendationError} resources={recommendedResources} /></section>
        <section id="route" className="page-section"><ModuleHeader moduleId="route" /><RescueRoutePlanning {...routePlanningForm} onChange={(field, value) => setRoutePlanningForm((currentForm) => ({ ...currentForm, [field]: value }))} onPlan={planRescueRoute} loading={routePlanningLoading} error={routePlanningError} result={routePlanningResult} /></section>
        <section id="teams" className="page-section"><ModuleHeader moduleId="teams" /><AvailableRescueTeams teams={teams} loading={teamsLoading} error={teamsError} onRefresh={fetchAvailableTeams} /></section>
        <section id="deployment" className="page-section"><ModuleHeader moduleId="deployment" /><div className="mission-workspace"><TeamDeploymentPanel teams={teams} missions={missions} hospitals={hospitals} vehicles={vehicles} selectedTeamId={deploymentTeamId} onTeamChange={(teamId) => { setDeploymentTeamId(teamId); setDeploymentError(''); setDeploymentSuccess('') }} form={deploymentForm} onFormChange={(field, value) => setDeploymentForm((currentForm) => ({ ...currentForm, [field]: value }))} onDeploy={deployTeam} loading={deployLoading} error={deploymentError} success={deploymentSuccess} result={deploymentResult} /><MissionOperationsDetails mission={deploymentResult || missions.find((mission) => mission.mission_id === selectedAllocationMissionId)} selectedTeam={teams.find((team) => team.team_id === (deploymentResult?.team_id || missions.find((mission) => mission.mission_id === selectedAllocationMissionId)?.team_id))} hospitals={hospitals} vehicles={vehicles} routeResult={routePlanningResult || routeResult} allocations={missionAllocations} missionAllocationsLoading={missionAllocationsLoading} missionAllocationsError={missionAllocationsError} onStatusChange={updateMissionStatus} missionUpdatingId={missionUpdatingId} onRelease={releaseResourceAllocation} onCancel={cancelResourceAllocation} releasingId={releasingAllocationId} cancellingId={cancellingAllocationId} /></div></section>
        <section id="vehicles" className="page-section"><ModuleHeader moduleId="vehicles" /><EmergencyVehicleTracking vehicles={vehicles} loading={vehiclesLoading} error={vehiclesError} selectedVehicleId={selectedVehicleId} onVehicleChange={selectVehicle} latitude={vehicleLatitude} longitude={vehicleLongitude} onLatitudeChange={setVehicleLatitude} onLongitudeChange={setVehicleLongitude} status={vehicleStatus} onStatusChange={setVehicleStatus} onRefresh={fetchVehicles} onUpdateLocation={() => updateVehicle('location')} onUpdateStatus={() => updateVehicle('status')} updateLoading={vehicleUpdateLoading} success={vehicleUpdateSuccess} updateError={vehicleUpdateError} /></section>
        <section id="shelters" className="page-section"><ModuleHeader moduleId="shelters" /><EmergencyShelterManagement shelters={shelters} loading={sheltersLoading} error={sheltersError} selectedShelterId={selectedShelterId} onShelterChange={selectShelter} capacity={shelterCapacity} onCapacityChange={setShelterCapacity} nearestLatitude={shelterNearestLatitude} nearestLongitude={shelterNearestLongitude} onNearestLatitudeChange={setShelterNearestLatitude} onNearestLongitudeChange={setShelterNearestLongitude} nearestShelter={nearestShelter} nearestLoading={nearestShelterLoading} nearestError={nearestShelterError} onFindNearest={findNearestShelter} onRefresh={fetchShelters} onUpdateCapacity={updateShelterCapacity} updateLoading={shelterUpdateLoading} success={shelterUpdateSuccess} updateError={shelterUpdateError} /></section>
        <section id="allocation" className="page-section"><ModuleHeader moduleId="allocation" /><ResourceAllocationWorkspace resources={resources} missions={missions} selectedResourceId={selectedResourceId} allocationQuantity={allocationQuantity} onResourceChange={(resourceId) => { setSelectedResourceId(resourceId); setInventoryAllocationError(''); setMissionAllocationError('') }} onQuantityChange={setAllocationQuantity} onAllocateInventory={allocateResourceInventory} onAllocateMission={allocateResourceToMission} inventoryAllocationDisabled={inventoryAllocationDisabled} missionAllocationDisabled={missionAllocationDisabled} inventoryLoading={inventoryAllocationLoading} missionLoading={missionAllocationLoading} inventoryError={inventoryAllocationError} missionError={missionAllocationError} inventoryResult={inventoryAllocationResult} missionResult={missionAllocationResult} selectedMissionId={selectedAllocationMissionId} onMissionChange={(missionId) => { setSelectedAllocationMissionId(missionId); setMissionAllocationError(''); setMissionAllocationResult(null); setAllocationReleaseError(''); setAllocationCancellationError('') }}><ResourceAllocationDashboard missions={missions} selectedMissionId={selectedAllocationMissionId} onMissionChange={(missionId) => { setSelectedAllocationMissionId(missionId); setMissionAllocationError(''); setMissionAllocationResult(null); setAllocationReleaseError(''); setAllocationCancellationError('') }} allocations={missionAllocations} loading={missionAllocationsLoading} error={missionAllocationsError} onRefresh={() => fetchMissionAllocations(selectedAllocationMissionId)} onRelease={releaseResourceAllocation} onCancel={cancelResourceAllocation} releasingId={releasingAllocationId} cancellingId={cancellingAllocationId} releaseError={allocationReleaseError} cancellationError={allocationCancellationError} /></ResourceAllocationWorkspace></section>
      </div><footer><span>GEOGUARDIAN AI <b>•</b> RESCUE MANAGEMENT MODULE</span><span>Local time: {currentClock} <i className="pulse-dot" /></span></footer>
      <section className="panel mission-allocation-history"><PanelHeader eyebrow="RESOURCE AUDIT" title="Mission Allocation History" />{allocationReleaseError && <span className="inventory-feedback inventory-feedback-error">{allocationReleaseError}</span>}{allocationCancellationError && <span className="inventory-feedback inventory-feedback-error">{allocationCancellationError}</span>}{!selectedAllocationMissionId && <span className="muted">Select a mission to view allocation history.</span>}{selectedAllocationMissionId && missionAllocationsLoading && <span className="muted">Loading mission allocations...</span>}{selectedAllocationMissionId && missionAllocationsError && <span className="muted">{missionAllocationsError}</span>}{selectedAllocationMissionId && !missionAllocationsLoading && !missionAllocationsError && missionAllocations.length === 0 && <span className="muted">No resource allocations for this mission.</span>}{selectedAllocationMissionId && !missionAllocationsLoading && !missionAllocationsError && missionAllocations.length > 0 && <div className="compact-list">{missionAllocations.map((allocation) => <article className="compact-row" key={allocation.allocation_id}><div className="compact-main"><strong>{allocation.allocation_id}</strong><span>{allocation.resource_id} · {allocation.quantity} units · {allocation.disaster_id}</span><span>{allocation.status} · {allocation.allocated_at}</span></div>{allocation.status === 'ALLOCATED' && <div className="allocation-actions"><button className="allocation-release-button" type="button" onClick={() => releaseResourceAllocation(allocation.allocation_id)} disabled={releasingAllocationId === allocation.allocation_id || cancellingAllocationId === allocation.allocation_id}>{releasingAllocationId === allocation.allocation_id ? 'Releasing...' : 'Release'}</button><button className="allocation-cancel-button" type="button" onClick={() => cancelResourceAllocation(allocation.allocation_id)} disabled={cancellingAllocationId === allocation.allocation_id || releasingAllocationId === allocation.allocation_id}>{cancellingAllocationId === allocation.allocation_id ? 'Cancelling...' : 'Cancel'}</button></div>}</article>)}</div>}</section>
      </div>
    </main>
  )
}

export default App
