# Rescue module storage

The rescue module stores missions, resource inventory and allocation history,
rescue teams, emergency vehicles, and both shelter registries in SQLite using
Python's standard-library `sqlite3` module. Hospital data remains managed by
the existing hospital service and is not stored in this database.

Set `GEOGUARDIAN_DATABASE_PATH` before starting the FastAPI application to
select a database file. If it is unset, the module uses
`backend/rescue/data/rescue.sqlite3`, created on first startup. Set it to
`:memory:` for a process-local database (as the test suite does).

The service initializes the schema when imported. Seed records are inserted
only when their corresponding entity collection is empty; existing operational
records are loaded as-is and are not replaced by startup seed data. Mission and
allocation IDs are chosen from persisted records while holding a SQLite write
transaction, so concurrent writers and restarts do not reuse a numeric ID.

## Detection-to-mission adapter

The repository currently contains no Member 1 detection package, detection
model, or detection API. The rescue integration therefore exposes a documented
adapter rather than claiming to consume an upstream contract. `POST
/mission/from-detection` accepts a `detection` object with `detection_id`,
`disaster_id`, `disaster_type`, `latitude`, and `longitude`. Optional
`severity` (1-5), `affected_population` (non-negative whole number), and
`critical_infrastructure` reuse fields from the existing risk-priority request.
An optional `confidence` is defined by this adapter on the normalized 0-1
scale; Member 1 must confirm that convention before sending it.

The operator supplies an available team and mission priority and must send
`confirmed: true`. No mission is created during detection validation/prefill.
The endpoint creates an `ASSIGNED` mission with the detector's disaster ID and
coordinates; it neither advances mission status nor allocates resources.
Detection IDs are stored as unique mission links in SQLite, so a repeated
submission returns HTTP 409 rather than creating another mission. The adapter
uses `extra="forbid"` so producer fields need explicit contract review before
they are accepted.

The existing risk-priority request provides affected-population counts, but no
affected-area geometry, detection confidence field, or stable detection ID.
The adapter does not fabricate area geometry or calculate/store a risk score.
Scores continue to enter mission ranking only through the existing risk
priority flow.

To reset local development state, stop the application and remove the configured
SQLite database file (and its `-wal`/`-shm` sidecar files if present). The next
startup creates a fresh database and loads the original seed records. Do not
remove a database file while the application is running.

Critical mission creation/status transitions, mission-linked allocation,
release/cancellation, settlement, and direct inventory decrement read the
current persisted rows under `BEGIN IMMEDIATE`, then store the coupled state
and its audit events in one transaction. SQLite serializes these database
writers, and the process-local reentrant lock also serializes threads sharing
an application process. These guarantees prevent overspending, duplicate
release/settlement, transition based on an old persisted status, and ID reuse
for those mutation paths, even when multiple processes point at the same
database file.

The module still retains operational snapshots in process memory. General list
and lookup endpoints, recommendation/readiness reads, and some non-critical
state updates are not synchronized from SQLite on every request. Therefore,
the application as a whole is **not multi-worker safe**: responses can be stale,
and a mutation path that persists a process-local snapshot rather than loading
its current rows can overwrite another worker's update. Run one application
worker. `:memory:` databases are process-local and cannot coordinate multiple
workers at all. SQLite transaction guarantees for the critical paths do not
remove this broader single-worker restriction.

## Operational audit history

Successful mission creation and status changes, detection-to-mission
confirmation, resource allocation/release/cancellation and automatic
settlement, and supported emergency-vehicle status/location changes are stored
in `operational_audit_events`. Events are appended in the same SQLite
transaction as their operational changes wherever the service performs a
transactional write. Failed operations do not create success events. The
read-only `GET /audit-events` endpoint supports `mission_id`, `disaster_id`,
`event_type`, timezone-qualified `start_time`/`end_time`, `limit` (1-100,
default 25), and `offset` (default 0). Results are newest first, with event ID
as the deterministic tie-breaker.

There is no authenticated operator identity in the current application, so
events use `system/unspecified` as the actor. Event summaries contain operational
change details and related identifiers, not credentials or user-supplied
payloads. This audit trail covers the successful operations listed above; it
does not claim a human actor identity or capture reads and failed attempts.
As with the rest of the current SQLite-backed in-memory service architecture,
multi-worker coordination is not guaranteed.

## Member 2 integration contract

The APIs below are the implemented rescue-module boundary. They do not imply
that the module consumes an external live detection or prediction feed.

| Endpoint | Purpose and required inputs | Response identifiers / behavior |
| --- | --- | --- |
| `POST /mission/from-detection` | Validated detection adapter, `team_id`, optional `priority`, and mandatory `confirmed: true`. | `201` Mission with `mission_id`, `disaster_id`, `team_id`, destination coordinates, and initial `ASSIGNED` status. Duplicate `detection_id` returns `409`; invalid or unconfirmed requests do not create a mission. |
| `POST /mission`, `POST /deploy-team` | Manual mission creation with `team_id`, `disaster_id`, destination latitude/longitude, and optional priority/hospital/vehicle IDs. | `201` Mission; both use the existing assignment and lifecycle rules. |
| `GET /missions`, `GET /mission/{mission_id}` | List missions or retrieve one mission. | Mission records keyed by `mission_id`, associated with `disaster_id`. |
| `GET /missions/ranked` | Read deterministic operational ranking. | Ranked entries include rank, mission, and optional `disaster_risk_score`; response reports unassessed disaster IDs. |
| `PATCH /mission/{mission_id}/status` | JSON body such as `{ "status": "DEPLOYED" }`. | Updated Mission. Transitions: `ASSIGNED → DEPLOYED/CANCELLED`, `DEPLOYED → EN_ROUTE/CANCELLED`, `EN_ROUTE → ARRIVED/CANCELLED`, `ARRIVED → COMPLETED/CANCELLED`. Completion releases active allocations and restores inventory; cancellation marks them cancelled without restoring inventory. |
| `POST /assess-resource-readiness-for-mission` | `mission_id` and a non-empty list of explicit `{resource_type, quantity}` requirements; quantities are positive whole numbers. | Mission/disaster IDs, requested, available, and already-allocated quantities, overall readiness and shortages. Read-only; terminal missions are rejected. |
| `POST /recommend-resources-for-mission` | Existing non-terminal `mission_id`, optional resource type and positive minimum `quantity`. | Mission/disaster IDs, destination, eligible recommended resources, and `recommendation_only: true`. Does not reserve inventory. |
| `POST /allocate-resource-to-mission` | `mission_id`, `resource_id`, and positive `quantity`. | Allocation record with `allocation_id`, mission/disaster/resource IDs, quantity, timestamp, and status. Decrements inventory. |
| `POST /release-resource-allocation`, `POST /cancel-resource-allocation` | `allocation_id`. | Updated allocation; release restores inventory, manual cancellation does not. |
| `GET /mission/{mission_id}/allocations` | Mission ID in path. | Allocation history, including `allocation_id` and status. |
| `GET /available-resources`, `GET /nearby-resources` | Optional resource type; nearby lookup also requires latitude/longitude. | Inventory records identified by `resource_id`, including `available_quantity`. |
| `POST /allocate-resource-inventory` | `resource_id` and positive `quantity`. | Updated inventory record; direct inventory decrement, not mission-linked. |
| `POST /allocate-resource` | Disaster ID/type, location, severity, and optional team/resource filters. | Read-only recommendation for hospital, rescue team, and resources; does not allocate inventory or create a mission. |
| `POST /risk-priority` | `disaster_id`, `disaster_type`, coordinates, severity (1-5), affected population (non-negative integer), and optional `critical_infrastructure`. | `disaster_id`, `risk_score` (0-100), `priority_level`, and reasoning. Successful results are cached by disaster ID in process memory for ranking. |
| `GET /audit-events` | Optional mission/disaster/event/time filters and pagination (`limit`, `offset`). | Newest-first audit page with `event_id`, event type, timestamp, actor, related IDs, and structured summary. |
| `GET /available-team`, `GET /hospitals`, `GET /nearest-hospital` | Available-team and nearest-hospital lookups require coordinates. | Available team or hospital records, including their IDs. |
| `GET /vehicles`, `GET /available-vehicles`, `GET /available-vehicle`, `GET /nearest-vehicle`, `POST /vehicles/{vehicle_id}/status`, `POST /vehicles/{vehicle_id}/location` | Vehicle lookup may filter by type or coordinates; updates require status or coordinates. | Vehicle records identified by `vehicle_id`; successful status/location updates are audited. |
| `GET /shelters`, `GET /available-shelters`, `GET /nearest-shelter`, `POST /shelters/{shelter_id}/capacity` | Nearest lookup requires coordinates; capacity update requires `available_capacity`. | Shelter record identified by `shelter_id`, optionally with distance for nearest lookup. |
| `POST /calculate-route` | Route request with origin and destination coordinates. | Deterministic route estimate including distance, duration, route-risk score, status, and explanation. |

### Detection producer contract

No Member 1 detection schema, package, or API is present in this repository.
`POST /mission/from-detection` is an explicit adapter, not a live Member 1
integration. Required `detection` fields are `detection_id`, `disaster_id`,
`disaster_type`, `latitude`, and `longitude`. Optional fields are `severity`
(integer 1-5), `confidence` (currently interpreted as 0-1),
`affected_population` (non-negative integer), and
`critical_infrastructure` (boolean). Unknown fields are rejected. Member 1
must confirm the stable ID and disaster-ID semantics, coordinate reference
system/meaning, confidence scale, and optional-field definitions before a
producer is connected. Affected-area geometry is not accepted or inferred.
Mission creation requires an available team and explicit operator confirmation;
the adapter does not deploy a team or allocate resources automatically.

### Risk and Member 4 prediction handoff

Ranking risk scores come only from a successful `POST /risk-priority` request
using caller-supplied severity, population, and critical-infrastructure
inputs. That endpoint returns a 0-100 `risk_score` associated with the supplied
`disaster_id`; ranking looks up that same ID, puts assessed disasters before
unassessed ones, then breaks ties by assigned mission priority, lifecycle
status, oldest creation time, and mission ID. Ranking does not calculate
scores. The score cache is process-local and is lost at restart.

The project identifies Member 4 as Prediction & Analytics, but no Member 4
prediction model/API or persisted prediction output is implemented here.
There is no automated path from prediction results to `/risk-priority`; the
producer contract and mapping of prediction risk fields remain integration
inputs. Adapter severity or confidence is not itself a calculated risk score,
and current ranking is not live prediction integration.
