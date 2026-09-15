# CBAM Stationary Combustion Fuel Reference Catalog

**Scope:** Fuel reference catalog + Phase 3 orchestration/result snapshot. No public API, UI, allocation, or Excel.

## Architecture decision

Dedicated tables are used instead of `CbamFactorDefinition` / `CbamFactorValue`.

Reason: a stationary-combustion parameter set must hold **together** fuel identity, input basis, NCV, fossil CO2 factor, oxidation factor, optional reference density, dataset version, dual-source provenance, and effective dates. Forcing NCV, oxidation, or density into a single “emission factor” row would blur domain meaning and mix this catalog with electricity / product factor resolution.

`CbamReferenceSource` is reused for source identity (e.g. platform `IPCC`). Chapter/table locations are stored as explicit typed columns on the parameter set so NCV and CO2 provenance remain independent.

## Tables

- `cbam_stationary_combustion_fuels` — stable fuel definition (`code`, name, `input_basis`, `default_activity_unit`, status)
- `cbam_stationary_combustion_parameter_sets` — immutable versioned parameter rows (`dataset_code` + `dataset_version`, validity, NCV, fossil CO2 EF, oxidation, optional density, provenance)
- `cbam_stationary_combustion_results` — immutable typed execution snapshot (inputs, resolved parameters, provenance, intermediates, final `tCO2`) linked to `cbam_calculation_runs`

## Natural gas seed (`NATURAL_GAS`)

| Field | Value |
|-------|--------|
| Input basis | VOLUME |
| Default activity unit | Sm3 |
| NCV | 48 TJ/Gg — 2006 IPCC V2 Ch.1 Table 1.2 |
| Fossil CO2 EF | 56100 kgCO2/TJ — 2006 IPCC V2 Ch.2 Table 2.3 (Manufacturing Industries and Construction) |
| Oxidation factor | 1 |
| Dataset | `IPCC_2006_STATIONARY_COMBUSTION` / `2006_V1` |
| Reference density | **null** (not authoritative) |

## Density rule (unresolved)

Workbooks disagree (0.67 vs 0.68 kg/Sm3). No active default density is seeded. Schema allows optional density for future decisions. Phase 1 math and Phase 3 orchestration require an **explicit** density for VOLUME input on the execution command. No automatic density fallback. The exact command density is snapshotted on the result.

## Effective-date resolution

`resolve_stationary_combustion_parameters(fuel_code, reference_date, dataset_version?)`:

- ACTIVE fuel + ACTIVE parameter set
- `valid_from <= reference_date` and (`valid_until` null or `reference_date <= valid_until`)
- 0 matches → `UNRESOLVED`
- >1 matches → `AMBIGUOUS` (fail-closed; no silent newest-row pick)
- Optional `dataset_version` narrows candidates
- Historical dates resolve historical versions; future versions do not rewrite past resolutions

Published corrections create a **new** version; in-place mutation of published rows is not part of this catalog’s write path (create-only service; no update/delete/deactivate APIs). Re-running the platform seed against an existing `(dataset_code, dataset_version)` that diverges from expected published values raises `IMMUTABLE_PARAMETER_VERSION_CONFLICT` instead of rewriting. Overlapping ACTIVE validity for the same fuel is rejected at create time in the catalog service (no DB exclusion constraint).

## Phase 3 orchestration

`execute_stationary_combustion_calculation` connects a persisted activity record, catalog resolution, and Phase 1 pure math, then stores an immutable typed result.

- Reuses `CbamCalculationRun` lifecycle (`DRAFT` → `RUNNING` → `COMPLETED` / `FAILED`)
- Does **not** write `CbamCalculationResult` (that row still requires `factor_resolution_id` and models one activity × one factor)
- Does **not** invent fake factor resolutions for NCV or CO2
- Calculation definition `STATIONARY_COMBUSTION_CO2_V1` has `factor_definition_id = null`
- NCV / fossil CO2 come only from the resolved published parameter set
- Activity quantity/unit come only from the persisted activity record
- Recalculation creates a new run + result; historical snapshots stay unchanged

## Phase 4A REST API

Organization-scoped routes under `/api/v1/cbam/organizations/{organizationId}/…`:

| Method | Path | Permission |
|--------|------|------------|
| GET | `stationary-combustion/fuels` | `cbam:view` |
| GET | `stationary-combustion/fuels/{fuelCode}/parameters?referenceDate=&datasetVersion=` | `cbam:view` |
| POST | `reporting-period-bindings/{bindingId}/stationary-combustion/executions` | `cbam:configure` |
| GET | `reporting-period-bindings/{bindingId}/stationary-combustion/results` | `cbam:view` |
| GET | `reporting-period-bindings/{bindingId}/stationary-combustion/results/{resultId}` | `cbam:view` |

Run status for an execution is returned on the execution response (`status`, `runId`) and remains readable via existing `calculation-runs/{runId}` when needed.

**Execution ownership:** request body supplies required `clientRequestId` (UUID), `activityRecordId`, `fuelCode`, optional density, optional `datasetVersion`, and optional `calculationReferenceDate`. Quantity, unit, NCV, CO2 factor, and oxidation never come from the client. Public API does **not** accept `calculationRunId` (internal Phase 3 run-retry remains available only to the application service).

**Reference date:** prefer persisted `activityDate`; otherwise require `calculationReferenceDate` inside the binding’s reporting period (inclusive). Never use “today”. Effective reference date is part of the idempotency material identity.

**Density:** VOLUME fuels require explicit command density; no defaults. MASS fuels reject density.

### Execution idempotency (`clientRequestId`)

Bounded to this endpoint only (not a platform Idempotency-Key store). Scope:

`organization_id` + `reporting_period_binding_id` + stationary-combustion result + `clientRequestId`

Persisted on the successful typed result with a SHA-256 **request fingerprint** of the normalized material identity (org, binding, activity, fuel code, effective reference date, density value/unit, explicit nullable dataset version). Uniqueness is enforced by a partial unique index on `(organization_id, reporting_period_binding_id, client_request_id)`.

| Case | Behavior |
|------|----------|
| First successful execution for the key | Create run + result; **HTTP 201**; `idempotentReplay=false`; echo `clientRequestId` |
| Exact retry (same key + same material identity) | No new run/result; **HTTP 200**; same `runId`/`resultId`; `idempotentReplay=true` |
| Same key, different material input | **HTTP 409** `IDEMPOTENCY_KEY_REUSED` — do not return the prior result as if it matched |
| New `clientRequestId` | Intentional recalculation — new run/result (**201**) |
| Missing / non-UUID `clientRequestId` | Schema **422** (required; no unsafe fallback) |
| Validation / calc failure before a result exists | No successful idempotency row; same `clientRequestId` may be retried after correction. Failed API attempts do not commit a success record; do not treat a failed run as an idempotent success. |

Concurrent identical keys: DB uniqueness ensures one winner; the loser recovers via rollback and returns replay (200) or `IDEMPOTENCY_KEY_REUSED` if material identity differs. Same UUID may be used in another organization or another binding without collision (both are part of the uniqueness scope).

### Direct Emissions UI (Phase 4B + 5B)

Period detail tab **Direct Emissions** (after Activities):

- `cbam:view` can open the tab, see fuels/parameters/results/summary; `cbam:configure` can Calculate / Calculate again / Update calculation
- Uses persisted Activities only (no quantity edit; empty state links back to Activities)
- VOLUME fuels require an empty-by-default density input (no 0.67/0.68 default); MASS fuels omit density
- Client generates `clientRequestId` per intentional attempt; retries keep the same id; material changes or recalculation start a new id
- **Period Summary** loads from the Phase 5A summary API (authoritative aggregate readiness + totals; no client-side total math; no monthly breakdown)
- **Activity coverage** loads from `GET …/stationary-combustion/activity-coverage` (authoritative per-activity `MISSING` / `CURRENT` / `STALE`); CTA labels use coverage only — never infer readiness from a paginated result-history page
- Result list uses API pagination for history display only; badges: Current / History / Out of date from `isCurrent` + `isStale`
- Stale current results remain readable; configure users can submit a new calculation (old snapshot stays history)
- Full A→E Excel wizard redesign and allocation remain out of scope

### Current result and period summary (Phase 5A)

Successful intentional executions set an authoritative **current-result pointer** per activity (`cbam_stationary_combustion_current_results`). Historical results remain immutable and listable.

| Event | Pointer |
|-------|---------|
| First success / intentional recalculation | Insert or replace pointer to the new result |
| Exact idempotent replay of the current result | Unchanged |
| Replay of an older non-current result (same clientRequestId) | Unchanged (does not move backwards) |
| Failed calculation | Unchanged |

**Stale:** a current snapshot no longer matches the live activity quantity, unit, fuel/type, or activity date (when set). Newer catalog versions alone do **not** stale a result. Stale results stay readable as history but are excluded from period totals.

**Period summary** (`GET …/stationary-combustion/summary`, `cbam:view`): aggregates only valid current snapshots for the binding. Readiness priority: `EMPTY` > `INCOMPLETE` > `STALE` > `READY`. Totals sum high-precision snapshot fields (`fuel_mass_*`, `energy_content_tj`, `fossil_co2_*`) and quantize **once** at the period `finalResultValue` boundary. Monthly breakdown and quarterly entry-method rules are **not** decided here; allocation is out of scope.

**Activity coverage** (`GET …/stationary-combustion/activity-coverage?page&pageSize`, `cbam:view`): paginated eligible activities with authoritative `coverageStatus` (`MISSING` / `CURRENT` / `STALE`), current result pointers, and stale reason codes. Ordering: `activity_date` ascending (nulls last), then activity id. Coverage counts across pages reconcile with summary `missingResultCount` / `staleResultCount` / `validCurrentResultCount` / `eligibleActivityCount`; period totals are **not** computed from coverage. History pagination must not be used to infer per-activity readiness.

**Historical results:** rows created before migration may have null `clientRequestId`; they remain readable. List/detail expose `clientRequestId` when present. No update/delete routes.
