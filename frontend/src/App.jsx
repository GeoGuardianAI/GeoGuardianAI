import { useEffect, useState } from 'react'
import './App.css'

function Icon({ children }) {
  return <span className="icon" aria-hidden="true">{children}</span>
}

function PanelHeader({ eyebrow, title, action }) {
  return <div className="panel-header"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{action && <button className="text-button" type="button">{action} <span aria-hidden="true">↗</span></button>}</div>
}

function MetricCard({ label, value, detail, icon, tone }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}><Icon>{icon}</Icon></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div><span className="metric-trend">↗</span></article>
}

function App() {
  const [notice, setNotice] = useState('All systems are connected and ready for dispatch.')
  const [hospitals, setHospitals] = useState([])
  const [hospitalsLoading, setHospitalsLoading] = useState(true)
  const [hospitalsError, setHospitalsError] = useState('')
  const [teams, setTeams] = useState([])
  const [teamsLoading, setTeamsLoading] = useState(true)
  const [teamsError, setTeamsError] = useState('')
  const [resources, setResources] = useState([])
  const [resourcesLoading, setResourcesLoading] = useState(true)
  const [resourcesError, setResourcesError] = useState('')
  const [missions, setMissions] = useState([])
  const [missionsLoading, setMissionsLoading] = useState(true)
  const [missionsError, setMissionsError] = useState('')

  useEffect(() => {
    const fetchHospitals = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/nearest-hospital?latitude=12.9716&longitude=77.5946')

        if (!response.ok) {
          throw new Error(`Hospital request failed with status ${response.status}`)
        }

        const hospital = await response.json()
        setHospitals([hospital])
      } catch (error) {
        setHospitalsError(error instanceof Error ? error.message : 'Unable to load nearby hospitals.')
      } finally {
        setHospitalsLoading(false)
      }
    }

    const fetchTeams = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/available-team?latitude=12.9716&longitude=77.5946')

        if (!response.ok) {
          throw new Error(`Rescue team request failed with status ${response.status}`)
        }

        const data = await response.json()
        setTeams(Array.isArray(data) ? data : Array.isArray(data.value) ? data.value : [])
      } catch (error) {
        setTeamsError(error instanceof Error ? error.message : 'Unable to load rescue teams.')
      } finally {
        setTeamsLoading(false)
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

    const fetchMissions = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/missions')

        if (!response.ok) {
          throw new Error(`Mission request failed with status ${response.status}`)
        }

        const data = await response.json()
        setMissions(
          Array.isArray(data)
            ? data
            : Array.isArray(data?.value)
              ? data.value
              : []
        )
      } catch (error) {
        setMissions([])
        setMissionsError(error instanceof Error ? error.message : 'Unable to load active missions.')
      } finally {
        setMissionsLoading(false)
      }
    }

    fetchHospitals()
    fetchTeams()
    fetchResources()
    fetchMissions()
  }, [])

  const handleAction = (action) => setNotice(`${action} queued for command review.`)

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand-lockup"><div className="brand-mark"><Icon>✦</Icon></div><div><strong>GeoGuardian <em>AI</em></strong><span>Emergency Rescue Command Center</span></div></div><div className="topbar-meta"><span className="live-clock">● LIVE · 14:32:08 UTC</span><div className="system-status"><span className="pulse-dot" /><span><small>SYSTEM STATUS</small>Operational</span></div><button className="profile-button" type="button" aria-label="Open user profile">AC<span>▾</span></button></div></header>
      <div className="dashboard-content">
        <section className="welcome-row"><div><span className="eyebrow">COMMAND OVERVIEW / 06 SEP 2026</span><h1>Good afternoon, Commander.</h1><p>Real-time operational overview for the metropolitan response network.</p></div><div className="weather"><span className="weather-icon">☼</span><div><strong>28°C</strong><span>Clear skies · Visibility 12 km</span></div></div></section>
        <section className="metrics-grid" aria-label="Operational summary"><MetricCard label="Active Missions" value="12" detail="3 critical priority" icon="⌁" tone="red" /><MetricCard label="Rescue Teams" value="08" detail="of 14 total teams" icon="♙" tone="teal" /><MetricCard label="Available Vehicles" value="23" detail="4 currently deployed" icon="▣" tone="blue" /><MetricCard label="Emergency Resources" value="94%" detail="Readiness level" icon="◈" tone="amber" /></section>
        <div className="command-grid"><section className="panel missions-panel"><PanelHeader eyebrow="LIVE OPERATIONS" title="Active Missions" action="View all missions" /><div className="mission-list">{missionsLoading && <span className="muted">Loading active missions...</span>}{missionsError && <span className="muted">{missionsError}</span>}{!missionsLoading && !missionsError && missions.length === 0 && <span className="muted">No active missions.</span>}{!missionsLoading && !missionsError && missions.map((mission) => { const priority = mission.priority || 'MEDIUM'; const tone = priority.toLowerCase(); return <article className="mission-row" key={mission.mission_id}><div className={`priority-line ${tone}`} /><div className="mission-main"><div className="row-heading"><strong>{mission.disaster_id}</strong><span className={`badge ${tone}`}>{priority}</span></div><span className="muted">{mission.mission_id} · {mission.status}</span></div><div className="mission-eta"><small>STATUS</small><strong>{mission.status}</strong></div><button className="row-arrow" type="button" aria-label={`Open ${mission.mission_id}`}>↗</button></article> })}</div></section><section className="panel map-panel"><PanelHeader eyebrow="GEOSPATIAL VIEW" title="Emergency Response Map" /><div className="map-placeholder"><div className="map-grid" /><div className="map-route route-one" /><div className="map-route route-two" /><div className="map-marker marker-one">1</div><div className="map-marker marker-two">2</div><div className="map-marker marker-three">3</div><div className="map-center"><Icon>⌖</Icon><strong>Map integration pending</strong><span>Leaflet map integration will be added next.</span></div><span className="map-scale">2 km</span></div><div className="map-footer"><span><i className="legend-dot critical" /> Active incidents</span><span><i className="legend-dot hospital" /> Hospitals</span><span><i className="legend-dot team" /> Rescue teams</span></div></section></div>
        <div className="lower-grid"><section className="panel"><PanelHeader eyebrow="MEDICAL NETWORK" title="Nearby Hospitals" action="View network" /><div className="compact-list">{hospitalsLoading && <span className="muted">Loading nearby hospitals...</span>}{hospitalsError && <span className="muted">{hospitalsError}</span>}{!hospitalsLoading && !hospitalsError && hospitals.map((hospital) => <article className="compact-row" key={hospital.hospital_id}><div className={`facility-icon ${hospital.emergency_available ? 'green' : 'amber'}`}><Icon>✚</Icon></div><div className="compact-main"><strong>{hospital.name}</strong><span>{hospital.emergency_available ? 'Emergency Available' : 'Emergency Unavailable'} · {hospital.available_beds} beds available</span></div><span className="distance">Nearest<br /><small>away</small></span></article>)}</div></section><section className="panel"><PanelHeader eyebrow="FIELD PERSONNEL" title="Rescue Teams" action="Manage teams" /><div className="compact-list">{teamsLoading && <span className="muted">Loading rescue teams...</span>}{teamsError && <span className="muted">{teamsError}</span>}{!teamsLoading && !teamsError && teams.map((team) => <article className="compact-row" key={team.team_id}><div className={`avatar ${team.availability === 'AVAILABLE' ? 'teal' : 'orange'}`}>{(team.name || 'Team').split(' ').map((part) => part[0]).join('').slice(0, 2)}</div><div className="compact-main"><strong>{team.name}</strong><span>{(team.specialization || ['General Response']).join(' · ')} · {team.members} members</span></div><span className={`availability ${team.availability === 'AVAILABLE' ? 'available' : 'standby'}`}><i />{team.availability}</span></article>)}</div></section><section className="panel"><PanelHeader eyebrow="SUPPLY INVENTORY" title="Emergency Resources" action="View inventory" /><div className="resource-list">{resourcesLoading && <span className="muted">Loading emergency resources...</span>}{resourcesError && <span className="muted">{resourcesError}</span>}{!resourcesLoading && !resourcesError && resources.map((resource) => { const resourceType = (resource.resource_type || '').toUpperCase(); const tone = resourceType.includes('MEDICAL') ? 'red' : resourceType.includes('BLANKET') ? 'cyan' : 'blue'; const icon = resourceType.includes('MEDICAL') ? '✚' : resourceType.includes('WATER') ? '◒' : '▱'; return <article className="resource-row" key={resource.resource_id}><div className={`resource-icon ${tone}`}><Icon>{icon}</Icon></div><div><strong>{resource.name}</strong><span>{resource.resource_type}</span></div><b>{resource.available_quantity}</b></article>})}</div></section></div>
        <section className="quick-actions"><div><span className="eyebrow">COMMAND CONSOLE</span><h2>Quick Actions</h2><p className="notice"><span className="pulse-dot" />{notice}</p></div><div className="action-buttons">{['Allocate Resource', 'Deploy Team', 'Find Nearest Hospital', 'Optimize Route'].map((action, index) => <button type="button" className={`action-button action-${index}`} onClick={() => handleAction(action)} key={action}><span>{['＋', '↗', '✚', '⌁'][index]}</span>{action}<b>→</b></button>)}</div></section>
      </div><footer><span>GEOGUARDIAN AI <b>•</b> RESCUE MANAGEMENT MODULE</span><span>Last data sync: 14:31:54 UTC <i className="pulse-dot" /></span></footer>
    </main>
  )
}

export default App
