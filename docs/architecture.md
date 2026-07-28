# Architecture — EcoTrace AI (v0.3.0)

## System context

EcoTrace AI provides authenticated users with organization-scoped operational sustainability data and deterministic carbon accounting through a browser SPA and a versioned HTTP API backed by PostgreSQL. Carbon accounting adds emission factors, matching, inventories, and Decimal calculation snapshots — without AI/LCA/IoT.

```mermaid
flowchart LR
  User[Sustainability User] --> Web[Angular SPA]
  Web --> API[FastAPI Modular Monolith]
  API --> DB[(PostgreSQL)]
  API --> Files[(Attachment volume)]
```

## Container architecture

```mermaid
flowchart TB
  subgraph compose [docker compose]
    Web[web / Nginx + Angular]
    API[api / Uvicorn + FastAPI]
    PG[(postgres)]
    ATT[(ecotrace_attachments)]
  end
  Browser --> Web
  Browser -->|optional direct| API
  Web -->|/api proxy| API
  API --> PG
  API --> ATT
```

## Backend module boundaries

```text
ecotrace/
  api/                 # presentation adapters (routers, middleware, dependencies)
  core/                # config, security, logging, database, exceptions
  shared/              # cross-cutting schemas, audit, org access helpers
  modules/
    identity/          # users, roles, tokens, auth use cases
    organizations/     # organizations + memberships
    facilities/        # facility master data
    operational_assets/# production lines, equipment, data sources
    reference_data/    # units + activity types
    reporting_periods/ # period lifecycle + lock rules
    activity_data/     # activity records, revisions, attachments
    data_imports/      # CSV import jobs
  db/                  # Alembic + seed
```

Carbon accounting carbon modules plug in beside these without redesigning activity records.

## Facility hierarchy

```mermaid
flowchart TD
  Org[Organization] --> Facility
  Facility --> ProductionLine
  Facility --> Equipment
  ProductionLine -.optional.-> Equipment
  Facility --> DataSource
  Equipment -.optional.-> DataSource
  Org --> ReportingPeriod
  Org --> ActivityRecord
  ActivityRecord --> Facility
  ActivityRecord --> ReportingPeriod
  ActivityRecord --> ActivityType
  ActivityRecord --> Unit
```

## Activity data model

```mermaid
erDiagram
  ORGANIZATIONS ||--o{ FACILITIES : owns
  FACILITIES ||--o{ PRODUCTION_LINES : has
  FACILITIES ||--o{ EQUIPMENT : has
  ORGANIZATIONS ||--o{ REPORTING_PERIODS : has
  ORGANIZATIONS ||--o{ ACTIVITY_RECORDS : has
  ACTIVITY_TYPES ||--o{ ACTIVITY_RECORDS : classifies
  ACTIVITY_RECORDS ||--o{ ACTIVITY_RECORD_REVISIONS : history
  ACTIVITY_RECORDS ||--o{ ACTIVITY_ATTACHMENTS : evidence
  ORGANIZATIONS ||--o{ IMPORT_JOBS : imports
  IMPORT_JOBS ||--o{ IMPORT_JOB_ROWS : rows
```

## Frontend module boundaries

- `core/` — auth, guards, interceptors, typed API services, models
- `features/` — auth, dashboard, organizations, facilities, production-lines, equipment, data-sources, reporting-periods, activity-data, data-imports, reference-data, profile
- `layout/` — authenticated shell with role-aware navigation
- lazy-loaded routes for feature isolation

## Authentication flow

```mermaid
sequenceDiagram
  participant U as User
  participant W as Angular
  participant A as API
  participant D as PostgreSQL
  U->>W: Submit credentials
  W->>A: POST /api/v1/auth/login
  A->>D: Verify user + Argon2 hash
  A->>D: Store refresh token hash
  A->>D: Write audit login_success
  A-->>W: accessToken + refreshToken + user
  W->>W: Persist tokens (localStorage MVP)
  W->>A: Authorization Bearer accessToken
```

## Multi-organization isolation

- Every Operations business record belongs to an organization directly or via hierarchy.
- Repository queries include organization scope.
- Unauthorized cross-organization access returns **404** (existence hidden), matching Foundation.

## Activity record state transitions

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> submitted: submit
  submitted --> approved: approve
  submitted --> rejected: reject
  rejected --> draft: edit
  approved --> submitted: correct
  draft --> archived: archive
  approved --> archived: archive
```

## CSV import flow

```mermaid
flowchart LR
  Template --> Upload
  Upload --> Validate
  Validate -->|ready| Execute
  Validate -->|validation_failed| ReviewErrors
  Execute --> Completed
  Execute -->|already executed| Conflict409
```

## Non-goals

AI copilots, RAG, full LCA/PCF, Digital Product Passport, IoT/MQTT/Kafka ingestion, market-based Scope 2 evidence models, spend-based Scope 3, Redis/Celery workers, and executive dashboards.

See [carbon-accounting.md](carbon-accounting.md) for calculation methodology, matching precedence, and snapshot design.

## Phase 7 extensions

Additional modules: agents, automation, job_execution, anomaly_detection, forecasting, data_quality, alerts, notifications, scheduled_reports, supplier_monitoring, regulatory_intelligence, production_operations.

```mermaid
flowchart TB
  UI[Angular Web] --> API[FastAPI Modular Monolith]
  API --> PG[(PostgreSQL)]
  SCH[Scheduler Worker] --> PG
  SCH --> API
  API --> STOR[/Attachments Knowledge Reports/]
  Agents[Agents] --> Services[Application Services]
  Tools[Allowlisted Tools] --> Services
  Agents --> Approvals[Human Approvals]
```

Agent execution: prompt → injection check → allowlisted tools → read results or pending approvals → audited rationale (no hidden CoT).
