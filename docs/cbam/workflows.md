# CBAM Workflow Specification

Permissions map to existing EcoTrace roles unless CBAM-specific roles are later added (D-019). Baseline mapping:

| Capability | Roles (baseline) |
|------------|------------------|
| Read | organization_admin, sustainability_manager, analyst, viewer, system_admin |
| Write data | organization_admin, sustainability_manager, analyst, system_admin |
| Expert review | sustainability_manager, organization_admin, system_admin |
| Approve / lock (when activated) | organization_admin, sustainability_manager (lock), system_admin — subject to D-019/D-030 |
| Unlock / revise | organization_admin, system_admin |
| Manage reference catalogs | system_admin |

Exact CBAM declarant/verifier roles: **D-019** / **D-038**.

**Any transition not explicitly listed is forbidden.**

---

## CBAM lock vs generic ReportingPeriod (F-01)

- CBAM workflow and lock state live only on `CbamReportingPeriodBinding`.
- Generic `ReportingPeriod` lock is **not** source of truth.
- Generic lock may be an **optional guard** (column “Allowed while generic ReportingPeriod is locked” below).
- Generic lock/unlock **never** auto-changes CBAM binding lock.
- Locked CBAM data is corrected only via **CBAM revision** workflow.
- Operational interaction preference: **D-031**.

---

## 1. CBAM reporting period binding — states

`draft` · `data_collection` · `data_ready` · `expert_review` · `rework` · `approval_pending` · `approved` · `locked` · `revised`

### Explicit transitions

| Current | Target | Permission | Validation | Required reason | Audit event | Reversible? | Allowed while generic RP locked? | Blocking decisions |
|---------|--------|------------|------------|-----------------|-------------|-------------|----------------------------------|--------------------|
| draft | data_collection | write/manage | binding exists; at least one installation profile usable for org | no | `cbam.period.opened` | yes via admin reverse below | yes | D-012, D-035 |
| data_collection | data_ready | write | completeness validation green per rules; no blocking findings | no | `cbam.period.data_ready` | yes → data_collection | yes | D-013, D-033, D-035 |
| data_ready | data_collection | write | none (reopen collection) | yes | `cbam.period.back_to_collection` | — | yes | — |
| data_ready | expert_review | write/manage | no blocking validation findings | no | `cbam.period.expert_review` | yes → rework or data_collection | yes | — |
| expert_review | rework | expert | ≥1 finding or comment | yes | `cbam.period.rework` | yes | yes | — |
| expert_review | data_collection | expert/manage | reopen for major data gaps | yes | `cbam.period.expert_to_collection` | — | yes | — |
| rework | data_collection | write | none | no | `cbam.period.rework_started` | — | yes | — |
| expert_review | approval_pending | expert | review complete; no blocking findings; validation green | no | `cbam.period.approval_pending` | yes → expert_review/rework | yes | **D-030** (final meaning of this state) |
| approval_pending | expert_review | manage | return for review | yes | `cbam.period.back_to_expert` | — | yes | D-030 |
| approval_pending | approved | approve | **Activation blocked until D-030 resolved.** Technical prerequisite when activated: linked `approved_calculation_run_id` set to one exact run; that run must be in an approvable state per D-030 | yes (approval record) | `cbam.period.approved` | no (use revise) | yes (generic lock irrelevant) | **D-030** `BLOCKED_DOMAIN` |
| approved | locked | lock | **Activation blocked until D-030 resolved.** When activated: approved; binding references one approved calculation snapshot | no | `cbam.period.locked` | only via revise | yes | **D-030** |
| locked | revised | unlock+revise | revision reason required; creates `CbamRevision`; does not auto-change generic RP | yes | `cbam.period.revised` | — | yes | D-031 |
| revised | data_collection | write | none | no | `cbam.period.reopened` | — | yes | — |

**Forbidden examples (non-exhaustive):** `locked` → `approved`; `approved` → `data_collection` without `revised`; any auto transition driven by generic RP lock/unlock.

Until **D-030** is resolved: skeleton may persist states `approval_pending` / `approved` / `locked`, but production activation of `approval_pending→approved` and `approved→locked` must remain disabled (fail closed / not exposed as complete).

---

## 2. Activity and precursor data — states

`draft` · `submitted` · `accepted` · `rejected` · `superseded`

Applies to **`CbamActivityRecord`**, precursor lots, and declarations (entity-specific audit action prefixes).

| Current | Target | Permission | Validation | Required reason | Audit event | Reversible? | Evidence behavior |
|---------|--------|------------|------------|-----------------|-------------|-------------------|-------------------|
| (new) | draft | write | unit/quantity ≥ 0; provenance set | no | `cbam.activity.created` | yes | optional |
| draft | submitted | write | provenance not `unknown` unless allowed (D-011) | no | `cbam.activity.submitted` | via reject | required if D-013 says so |
| submitted | accepted | approve/expert | period in `data_collection` \| `rework` \| `data_ready` | no | `cbam.activity.accepted` | via supersede only | retain |
| submitted | rejected | approve/expert | — | **yes** | `cbam.activity.rejected` | via `rejected→draft` | retain on rejected record |
| rejected | draft | write | **correction reason required**; creates new revision/version; **original rejected record preserved** (no in-place edit without history); prior evidence retained unless explicitly replaced with new evidence links | **yes** (correction reason) | `cbam.activity.reopened_from_rejected` | — | replacement or retention recorded |
| accepted | superseded | write/system | replacing record created | yes | `cbam.activity.superseded` | no mutate old | old evidence kept |

**Forbidden:** editing a `rejected` or `accepted` record in place without revision/supersede history.

---

## 3. Calculation run — states

Lifecycle statuses only:

`requested` · `validating` · `blocked` · `calculated` · `failed` · `approved` · `superseded` · `cancelled` (structural; **activation D-039**)

### BLOCKED_DOMAIN semantics (F-06)

- **Status:** `blocked`
- **Detail code:** `BLOCKED_DOMAIN` (or other codes)
- `BLOCKED_DOMAIN` is **never** a lifecycle state.
- A `blocked` run must store: blocking code, blocking decision IDs, affected rules/inputs, human-readable explanation, timestamp.

| Current | Target | Permission | Validation | Required reason | Audit event | Notes |
|---------|--------|------------|------------|-----------------|-------------|-------|
| — | requested | calculate (baseline manage/analyst; D-019) | period allows calc; idempotency key REQUIRED (D-040) | no | `cbam.calc.requested` | |
| requested | validating | system | snapshot build started | no | `cbam.calc.validating` | |
| validating | blocked | system | blocking validation or missing rule/consumption | no | `cbam.calc.blocked` | includes `BLOCKED_DOMAIN` detail when applicable |
| validating | calculated | system | required boundaries ok for requested scope | no | `cbam.calc.calculated` | shipment boundary only if shipment scope requested |
| validating | failed | system | engine exception | no | `cbam.calc.failed` | **not** cancellation |
| calculated | approved | approve | per D-030 when activated | yes | `cbam.calc.approved` | activation gated by D-030 |
| calculated \| approved | superseded | system/manage | new run created | yes | `cbam.calc.superseded` | timing details D-039 |
| requested \| validating | cancelled | **not activated** until D-039 | — | yes | `cbam.calc.cancelled` | **BLOCKED_DECISION**; do not use `failed` as cancelled |

Missing required inventory consumption → `blocked` (no provisional consumption).

---

## 4. Report — states

`requested` · `generating` · `generated` · `failed` · `superseded`

| Current | Target | Permission | Validation | Audit |
|---------|--------|------------|------------|-------|
| — | requested | manage/approve | run exists per report type policy; Idempotency-Key REQUIRED (D-040) | `cbam.report.requested` |
| requested | generating | system | template version known | `cbam.report.generating` |
| generating | generated | system | artifact + hash | `cbam.report.generated` |
| generating | failed | system | error | `cbam.report.failed` |
| generated | superseded | manage | reason | `cbam.report.superseded` |

---

## Separation of duty (baseline)

| Rule | Default |
|------|---------|
| Submitter ≠ accepter for activity | Enabled for production; may relax in demo (D-024) |
| Calculation requester ≠ period approver | When SoD flag on (D-024 / D-030) |
| Verifier package publisher ≠ data submitter | D-018 / D-038 |

SoD bypass: `system_admin` + audit `sodBypass=true`.

---

## Audit requirements

Every transition: `write_audit_log` with actor, organization_id, entity_type, entity_id, action, request_id, metadata (from/to, reason, decision IDs when blocked).
