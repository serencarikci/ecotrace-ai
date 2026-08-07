# CBAM Calculation Architecture (Boundaries Only)

Architecture and contracts only. Formula and regulatory content are **BLOCKED_DOMAIN** until a CBAM domain expert provides them.

## Separation mandate

```mermaid
flowchart LR
  subgraph forbidden [Must not produce CBAM SEE]
    CA[carbon_accounting]
    CI[carbon_inventory]
    LCA[lifecycle_assessment]
    PCF[product_carbon_footprint]
  end
  subgraph cbam [CBAM engine]
    VAL[validator]
    ENG[cbam calculation engine]
    TRACE[step traces]
    OUT[immutable run results]
  end
  VAL --> ENG --> TRACE --> OUT
  CA -.->x ENG
  CI -.->x ENG
  LCA -.->x ENG
  PCF -.->x ENG
```

Shared utilities allowed: Decimal helpers, unit dimension conversion (with snapshot of conversion factors), clock/UUID, audit writer, CamelModel/Page, org_access.

**Forbidden inside `modules/cbam`:** importing ORM models or calculation engines from `carbon_accounting`, `carbon_inventory`, `lifecycle_assessment`, `product_carbon_footprint`; writing to those modules’ tables; using their results as SEE. Future architecture test must detect forbidden imports (not implemented in this documentation-only phase).

## Engine package (proposed)

`modules/cbam/application/calculation/`: validate_inputs, snapshot_builder, engine, boundaries/*, types.

No router or Angular component may compute SEE.

## Numeric and unit rules (D-036 / D-037)

| Rule | Requirement |
|------|-------------|
| Numeric type | `Decimal` only |
| Decimal context | Engine version defines a **deterministic** Decimal context; no uncontrolled runtime float defaults |
| Intermediate quantization | Only if defined by an approved calculation-rule pack; otherwise none |
| Final reporting rounding | **BLOCKED_DOMAIN** (D-014 / D-036) until expert approval |
| Snapshot numerics | Preserve **raw normalized Decimal strings** before presentation rounding |
| Units | Every quantity has `unit_code` |
| Unit snapshot | source unit, normalized unit, conversion-factor value, conversion-factor version/stable definition, conversion direction, precision policy |
| Provenance | `actual` \| `default` \| `alternative_default` \| `unknown` on emission-related values |
| Silent fallback | **Forbidden** |
| Unknown rules / missing expert content | Run status `blocked`, detail code `BLOCKED_DOMAIN` |

## Snapshot layers

### 1. Calculation input snapshot

Frozen copies of: period binding identity/dates; installation profile fields; **product-profile version** + CN/AGC codes + catalog version; route/process/boundary versions; **`CbamActivityRecord`** values; inventory receipts/lots/**process consumptions** used; precursor lots/declarations; allocation applications; shipments (when shipment scope requested).

### 2. Reference-data snapshot

Pinned CN/AGC catalog version + codes used; functional unit definitions used.

### 3. Factor snapshot

Factor set version; each factor value/unit/provenance/citation copied (no live EF FK as source of truth for approved results).

### 4. Rule-version snapshot

Rule pack id/code, methodology_version, engine_version, precision context, handler capability matrix.

## Boundary definitions

### Unit-normalization boundary

Input → normalized Decimal + unit; incompatible dimensions → blocking.

### Allocation boundary

Uses allocation application snapshot; missing/invalid → `blocked` / `BLOCKED_DOMAIN`. Conservation per D-032 (tolerance not invented).

### Precursor-calculation boundary

Graph + declarations; cycles → blocking.

### Direct-emission / indirect-emission boundaries

Formula content TBD_EXPERT (D-007 / D-008).

### Inventory-consumption gate

If the requested calculation scope **requires** process consumption and required consumption is missing → status `blocked`. **No fake, empty, or provisional consumption** is allowed to appear complete.

### Product SEE vs shipment SEE

- Core **product-specific embedded-emission** calculation may run **without** a shipment.
- **Shipment-level** embedded emissions require the shipment phase and shipment records.
- Shipment boundary must not invent shipment quantities.

## Calculation-step trace and evidence (F-19)

Each `CbamCalculationStep`: step_key, sequence, boundary_name, inputs (refs + snapshotted values), outputs (Decimal, unit, provenance), rule_ref/factor_refs, status (`ok`\|`warning`\|`blocked`\|`failed`), messages, optional formula_ref.

**Traceability guarantee:**

calculation run → calculation step → input snapshot entry → source `CbamActivityRecord` / precursor / consumption → `CbamEvidenceLink` → evidence checksum/version.

Steps need not duplicate all evidence IDs when the input snapshot already provides an immutable direct path.

Traces immutable once the run leaves `validating`.

## Warnings vs blocking

| Class | Effect |
|-------|--------|
| Warning | May complete as `calculated` with warnings; approval policy TBD_EXPERT / D-030 |
| Blocking validation | Status `blocked` or `failed`; no SEE totals published as approved |
| Detail `BLOCKED_DOMAIN` | Unresolved expert/rule content; status remains `blocked` |

## Final result structure (schema only)

`totals[]` with metricKey/value/unit/provenance; optional breakdowns; disclaimer; warnings; blockingErrors; pinned version ids. No Scope 1/2/3 labels.

## Recalculation, superseding, cancellation

- New run increments `run_number`; history preserved.
- Superseding timing: **D-039**.
- Cancellation: structural status `cancelled` may exist; **transitions not activated** until D-039; do not misuse `failed` as cancelled.
- Comparison API: read-only diff of two runs.

## Period approval linkage (D-030)

Technical model supports linking a period approval to **one exact calculation-run ID**. A locked period must reference one approved calculation snapshot. Changing the selected run requires new approval or revision. **Final production order remains BLOCKED_DOMAIN** — do not claim a final order in docs or activate production lock/approve transitions until D-030 is resolved.

## Test posture (future)

- Golden tests only after expert-approved vectors.
- Structural tests: units, provenance, no silent fallback, immutability, forbidden imports, missing consumption → blocked.
- Never assert invented regulatory numbers.
