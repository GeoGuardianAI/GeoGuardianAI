import React, { useMemo, useState } from "react";

type Resource = {
  id: string;
  name: string;
  icon: string;
  total: number;
  available: number;
  active: number;
  status: "READY" | "LIMITED";
};

const initialResources: Resource[] = [
  {
    id: "boats",
    name: "Rescue Boats",
    icon: "🚤",
    total: 12,
    available: 8,
    active: 4,
    status: "READY",
  },
  {
    id: "ambulances",
    name: "Ambulances",
    icon: "🚑",
    total: 16,
    available: 10,
    active: 6,
    status: "READY",
  },
  {
    id: "medical",
    name: "Medical Teams",
    icon: "🧑‍⚕️",
    total: 8,
    available: 5,
    active: 3,
    status: "LIMITED",
  },
  {
    id: "helicopters",
    name: "Helicopters",
    icon: "🚁",
    total: 3,
    available: 2,
    active: 1,
    status: "READY",
  },
];

export const ResourceManagement: React.FC = () => {
  const [resources, setResources] = useState<Resource[]>(initialResources);
  const [deploymentApplied, setDeploymentApplied] = useState(false);

  const totalAvailable = useMemo(
    () => resources.reduce((sum, resource) => sum + resource.available, 0),
    [resources]
  );

  const handleDeployment = () => {
    setResources((current) =>
      current.map((resource) => {
        if (resource.id === "boats" && resource.available >= 5) {
          return {
            ...resource,
            available: resource.available - 5,
            active: resource.active + 5,
          };
        }

        return resource;
      })
    );

    setDeploymentApplied(true);
  };

  return (
    <main className="resources-page">
      {/* PAGE HEADER */}
      <section className="resources-header">
        <div>
          <p className="section-eyebrow">RESOURCE OPERATIONS</p>

          <h1>Emergency Resources</h1>

          <p className="resources-subtitle">
            Monitor availability and coordinate response resources for the
            active Pune flood incident.
          </p>
        </div>

        <div className="resource-update">
          <span className="status-dot" />
          <div>
            <strong>Operational</strong>
            <small>Updated 17:30:42 IST</small>
          </div>
        </div>
      </section>

      {/* SUMMARY */}
      <section className="resource-summary">
        <div>
          <span>Total available</span>
          <strong>{totalAvailable}</strong>
          <small>response units</small>
        </div>

        <div>
          <span>Currently deployed</span>
          <strong>
            {resources.reduce((sum, resource) => sum + resource.active, 0)}
          </strong>
          <small>active units</small>
        </div>

        <div>
          <span>Incident</span>
          <strong>LEVEL 4</strong>
          <small>Pune flood emergency</small>
        </div>

        <div>
          <span>Priority</span>
          <strong className="priority-critical">CRITICAL</strong>
          <small>immediate response</small>
        </div>
      </section>

      {/* RESOURCE CARDS */}
      <section className="resource-section">
        <div className="section-heading">
          <div>
            <h2>Resource Availability</h2>
            <p>Current operational capacity across response units.</p>
          </div>
        </div>

        <div className="resource-grid">
          {resources.map((resource) => {
            const percentage =
              (resource.available / resource.total) * 100;

            return (
              <article className="resource-card" key={resource.id}>
                <div className="resource-card-top">
                  <div className="resource-icon">{resource.icon}</div>

                  <span
                    className={`resource-status ${
                      resource.status === "READY"
                        ? "status-ready"
                        : "status-limited"
                    }`}
                  >
                    {resource.status}
                  </span>
                </div>

                <h3>{resource.name}</h3>

                <div className="resource-count">
                  <strong>{resource.available}</strong>
                  <span>/ {resource.total} available</span>
                </div>

                <div className="resource-bar">
                  <div
                    className="resource-bar-fill"
                    style={{ width: `${percentage}%` }}
                  />
                </div>

                <div className="resource-meta">
                  <span>{resource.active} deployed</span>
                  <span>{resource.available} ready</span>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* AI RECOMMENDATION */}
      <section className="deployment-section">
        <div className="deployment-header">
          <div>
            <p className="section-eyebrow">AI DECISION SUPPORT</p>
            <h2>Recommended Deployment</h2>
          </div>

          <span className="recommendation-badge">HIGH PRIORITY</span>
        </div>

        <div className="recommendation-card">
          <div className="recommendation-main">
            <div className="recommendation-icon">🚤</div>

            <div>
              <h3>Deploy 5 rescue boats</h3>

              <p>
                Position five available rescue boats near the flooded NH-48
                corridor to support evacuation and stranded-person rescue.
              </p>
            </div>
          </div>

          <div className="recommendation-reason">
            <h4>Why this recommendation?</h4>

            <div className="reason-grid">
              <div>
                <span>River level</span>
                <strong>1.9 m</strong>
                <small>Warning: 1.8 m</small>
              </div>

              <div>
                <span>Population exposure</span>
                <strong>22,400</strong>
                <small>Affected population</small>
              </div>

              <div>
                <span>Evacuation</span>
                <strong>ACTIVE</strong>
                <small>Level 4 flood</small>
              </div>

              <div>
                <span>Available boats</span>
                <strong>{resources[0].available}</strong>
                <small>Ready for dispatch</small>
              </div>
            </div>
          </div>

          <div className="recommendation-footer">
            <span>
              Evidence: Flood response SOP + current incident data
            </span>

            <div className="recommendation-actions">
              <button className="secondary-action">
                View evidence
              </button>

              <button
                className="primary-action"
                onClick={handleDeployment}
                disabled={deploymentApplied}
              >
                {deploymentApplied
                  ? "Deployment applied"
                  : "Apply deployment"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* DEPLOYMENT TABLE */}
      <section className="deployment-table-section">
        <div className="section-heading">
          <div>
            <h2>Current Deployment</h2>
            <p>Operational status of response resources.</p>
          </div>
        </div>

        <div className="deployment-table-wrapper">
          <table className="deployment-table">
            <thead>
              <tr>
                <th>Resource</th>
                <th>Active</th>
                <th>Available</th>
                <th>Total</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {resources.map((resource) => (
                <tr key={resource.id}>
                  <td>
                    <span className="table-resource">
                      <span>{resource.icon}</span>
                      {resource.name}
                    </span>
                  </td>

                  <td>{resource.active}</td>
                  <td>{resource.available}</td>
                  <td>{resource.total}</td>

                  <td>
                    <span
                      className={`table-status ${
                        resource.status === "READY"
                          ? "table-ready"
                          : "table-limited"
                      }`}
                    >
                      {resource.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
};

export default ResourceManagement;
