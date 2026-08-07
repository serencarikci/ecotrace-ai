# CBAM Domain Decision Register

Items that must be answered by a CBAM domain expert, product owner, or security owner before activating related production behavior.

Status values: `BLOCKED_DOMAIN` | `BLOCKED_DECISION` | `HIGH` | `MEDIUM` | `LOW` | `RESOLVED_ARCH`

Do not invent regulatory answers in code. Closing a decision requires Resolution + Resolution date + authority evidence.

## Schema (every entry)

Each decision record includes: stable ID, title, question, reason, affected modules, affected calculations, affected reports, owner, priority, blocking phase, required evidence or authority, current status, resolution, resolution date.

---

## D-001 — Pilot sector

| Field | Value |
|-------|--------|
| Title | Pilot sector |
| Question | Which first pilot sector/goods group? |
| Reason | Scopes CN/AGC/route/FU content for pilot |
| Affected modules | cbam reference, product profiles, routes |
| Affected calculations | All pilot SEE |
| Affected reports | Operator/customer pilot reports |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 12 (plan by phase 3) |
| Required evidence or authority | Expert sector selection memo |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-002 — CN codes

| Field | Value |
|-------|--------|
| Title | CN codes |
| Question | Which CN codes are in scope for pilot and how is the authoritative list sourced/versioned? |
| Reason | Catalog content must not be invented |
| Affected modules | cbam reference-data |
| Affected calculations | Scope determination |
| Affected reports | Operator report goods tables |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 3 / 12 |
| Required evidence or authority | Official CN source + version |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-003 — Aggregated goods categories

| Field | Value |
|-------|--------|
| Title | Aggregated goods categories |
| Question | Which AGCs apply and how do they map to CN codes? |
| Reason | Product classification and FU defaults |
| Affected modules | cbam reference-data, product profiles |
| Affected calculations | Classification pinning |
| Affected reports | Goods category sections |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 3 |
| Required evidence or authority | Official AGC mapping |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-004 — Production routes

| Field | Value |
|-------|--------|
| Title | Production routes |
| Question | Which production routes are supported for the pilot installation/product? |
| Reason | Route versions drive process boundaries |
| Affected modules | cbam processes/routes |
| Affected calculations | Process/route pinned runs |
| Affected reports | Methodology annex |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 4 / 12 |
| Required evidence or authority | Pilot process documentation |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-005 — Functional units

| Field | Value |
|-------|--------|
| Title | Functional units |
| Question | What functional units apply per AGC/product? |
| Reason | SEE normalization basis |
| Affected modules | product profiles, calculations |
| Affected calculations | SEE per FU |
| Affected reports | Specific embedded emissions |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 3 / 5 |
| Required evidence or authority | Regime-aligned FU definitions |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-006 — System boundaries

| Field | Value |
|-------|--------|
| Title | System boundaries |
| Question | What process/system boundaries are mandatory for pilot routes? |
| Reason | Included/excluded flows |
| Affected modules | boundaries, flows |
| Affected calculations | Direct/indirect scope |
| Affected reports | Boundary disclosures |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 4 |
| Required evidence or authority | Boundary checklist |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-007 — Direct emissions

| Field | Value |
|-------|--------|
| Title | Direct emissions methods |
| Question | Which direct emission methods/formulas are authorized? |
| Reason | Engine boundary content |
| Affected modules | cbam calculation engine |
| Affected calculations | Direct SEE |
| Affected reports | Operator emissions |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 9 |
| Required evidence or authority | Approved rule pack |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-008 — Indirect emissions

| Field | Value |
|-------|--------|
| Title | Indirect emissions applicability |
| Question | Which electricity/heat indirect rules apply (including applicability)? |
| Reason | Applicable indirect boundary |
| Affected modules | activity, calculation |
| Affected calculations | Indirect SEE |
| Affected reports | Indirect sections |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 9 |
| Required evidence or authority | Approved rule pack |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-009 — Precursor rules

| Field | Value |
|-------|--------|
| Title | Precursor SEE requirements |
| Question | When are precursor SEE required? How to treat missing declarations? |
| Reason | Complex goods completeness |
| Affected modules | precursors, calculation |
| Affected calculations | Precursor boundary |
| Affected reports | Precursor annex |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 7 / 9 |
| Required evidence or authority | Precursor policy |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-010 — Allocation methods

| Field | Value |
|-------|--------|
| Title | Allocation methods |
| Question | Which allocation methods are allowed and how are factors derived? |
| Reason | Process allocation applications |
| Affected modules | allocation, calculation |
| Affected calculations | Allocation boundary |
| Affected reports | Allocation disclosures |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 8 / 9 |
| Required evidence or authority | Method list + derivation rules |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-011 — Actual/default/alternative-default

| Field | Value |
|-------|--------|
| Title | Provenance class usage |
| Question | When may each provenance class be used? Any forbidden silent substitutions? |
| Reason | No silent fallback architecture |
| Affected modules | activity, factors, calculation |
| Affected calculations | All SEE with provenance |
| Affected reports | Provenance labels |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 5 / 9 |
| Required evidence or authority | Provenance policy |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-012 — Reporting period calendar

| Field | Value |
|-------|--------|
| Title | Reporting period calendar rules |
| Question | Calendar rules for CBAM reporting period vs EcoTrace generic periods? |
| Reason | Binding creation and completeness |
| Affected modules | period bindings, reporting_periods ref |
| Affected calculations | Period-scoped runs |
| Affected reports | Period headers |
| Owner | Domain + product |
| Priority | HIGH |
| Blocking phase | 2 |
| Required evidence or authority | Product calendar policy |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

## D-013 — Accepted evidence

| Field | Value |
|-------|--------|
| Title | Accepted evidence types |
| Question | Which document types are mandatory for activity/precursor/approval? |
| Reason | Evidence gate for workflows |
| Affected modules | evidence, workflows |
| Affected calculations | Trace to evidence |
| Affected reports | Verification package |
| Owner | Domain expert |
| Priority | HIGH |
| Blocking phase | 5 / 11 |
| Required evidence or authority | Evidence checklist |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

## D-014 — Rounding (final)

| Field | Value |
|-------|--------|
| Title | Final rounding rules |
| Question | Rounding/quantization rules for final SEE presentation? |
| Reason | Report presentation vs raw Decimal |
| Affected modules | calculation, reports |
| Affected calculations | Final presentation only |
| Affected reports | All numeric outputs |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 9 / 11 |
| Required evidence or authority | Rounding policy in rule pack |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-015 — Calculation tolerance

| Field | Value |
|-------|--------|
| Title | Golden-test tolerance |
| Question | Numeric comparison tolerance for golden tests and reruns? |
| Reason | Pilot acceptance |
| Affected modules | tests |
| Affected calculations | Comparison |
| Affected reports | N/A |
| Owner | Domain expert |
| Priority | HIGH |
| Blocking phase | 12 |
| Required evidence or authority | Expert-signed tolerance |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

## D-016 — Excel workbook version

| Field | Value |
|-------|--------|
| Title | Excel workbook version |
| Question | Which official/template workbook version must be supported? |
| Reason | Import/export templates |
| Affected modules | imports/exports |
| Affected calculations | N/A directly |
| Affected reports | Workbook export |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 10 |
| Required evidence or authority | Template file + version ID |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-017 — Report recipient

| Field | Value |
|-------|--------|
| Title | Report recipients and languages |
| Question | Who receives operator vs customer reports? Languages? |
| Reason | Report generation targets |
| Affected modules | reports |
| Affected calculations | N/A |
| Affected reports | All |
| Owner | Product + domain |
| Priority | HIGH |
| Blocking phase | 11 |
| Required evidence or authority | Product brief |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

## D-018 — Verifier requirements

| Field | Value |
|-------|--------|
| Title | Verifier package requirements |
| Question | Is accredited verifier workflow in v1? What package contents? |
| Reason | Verification package scope |
| Affected modules | verification package, authz |
| Affected calculations | Package inclusion of runs |
| Affected reports | Verification package |
| Owner | Domain + compliance |
| Priority | HIGH |
| Blocking phase | 11 |
| Required evidence or authority | Compliance brief; see also D-038 |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

## D-019 — Approval roles

| Field | Value |
|-------|--------|
| Title | Approval role model |
| Question | Declarant vs reviewer vs approver vs verifier role model vs existing EcoTrace roles? |
| Reason | RBAC and SoD |
| Affected modules | identity helpers, workflows |
| Affected calculations | Who may request/approve |
| Affected reports | Who may generate |
| Owner | Product + security |
| Priority | HIGH |
| Blocking phase | 1 / 11 |
| Required evidence or authority | Role matrix sign-off |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

## D-020 — Heat modeling

| Field | Value |
|-------|--------|
| Title | Heat modeling |
| Question | Measurable vs non-measurable heat rules for pilot? |
| Reason | Activity typing and indirect/direct boundaries |
| Affected modules | activity, calculation |
| Affected calculations | Heat-related SEE |
| Affected reports | Energy sections |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 5 / 9 |
| Required evidence or authority | Heat methodology |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-021 — Shipment SEE

| Field | Value |
|-------|--------|
| Title | Shipment-level SEE in pilot |
| Question | Is shipment-level SEE required in pilot? |
| Reason | Whether phase 10 is in pilot critical path |
| Affected modules | shipments, calculation |
| Affected calculations | Shipment boundary |
| Affected reports | Customer/shipment reports |
| Owner | Domain expert |
| Priority | MEDIUM |
| Blocking phase | 10 |
| Required evidence or authority | Pilot scope memo |
| Current status | MEDIUM |
| Resolution | |
| Resolution date | |

## D-022 — Default factor source

| Field | Value |
|-------|--------|
| Title | Default factor source |
| Question | Authoritative source/version for default values if allowed? |
| Reason | Factor set content |
| Affected modules | factor sets |
| Affected calculations | Default provenance paths |
| Affected reports | Factor citations |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 3 / 9 |
| Required evidence or authority | Official default set |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-023 — Complex goods depth

| Field | Value |
|-------|--------|
| Title | Complex goods nesting depth |
| Question | Maximum precursor nesting depth? |
| Reason | Graph validation |
| Affected modules | complex-goods graph |
| Affected calculations | Precursor boundary |
| Affected reports | Precursor tree |
| Owner | Domain expert |
| Priority | MEDIUM |
| Blocking phase | 7 |
| Required evidence or authority | Depth policy |
| Current status | MEDIUM |
| Resolution | |
| Resolution date | |

## D-024 — SoD policy

| Field | Value |
|-------|--------|
| Title | Separation of duty policy |
| Question | Production SoD strictness (submitter≠approver)? |
| Reason | Workflow enforcement |
| Affected modules | workflows, authz |
| Affected calculations | Approval of runs |
| Affected reports | Approval of reports |
| Owner | Security + product |
| Priority | MEDIUM |
| Blocking phase | 1 / 11 |
| Required evidence or authority | SoD policy |
| Current status | MEDIUM |
| Resolution | |
| Resolution date | |

## D-025 — Corporate activity import

| Field | Value |
|-------|--------|
| Title | Corporate activity import |
| Question | Is copying from corporate activity_records allowed in pilot? |
| Reason | Optional import adapter scope |
| Affected modules | import adapter |
| Affected calculations | Only after copy into CbamActivityRecord |
| Affected reports | N/A |
| Owner | Product |
| Priority | LOW |
| Blocking phase | 5 |
| Required evidence or authority | Product decision |
| Current status | LOW |
| Resolution | |
| Resolution date | |

## D-026 — Rule pack versioning

| Field | Value |
|-------|--------|
| Title | Rule pack versioning scheme |
| Question | Naming/version scheme for calculation rule packs? |
| Reason | Pinning and reproducibility |
| Affected modules | rule packs, calculation |
| Affected calculations | All |
| Affected reports | Methodology version fields |
| Owner | Engineering + domain |
| Priority | MEDIUM |
| Blocking phase | 9 |
| Required evidence or authority | Versioning convention |
| Current status | MEDIUM |
| Resolution | |
| Resolution date | |

## D-027 — Disclaimer text

| Field | Value |
|-------|--------|
| Title | Non-certification disclaimer |
| Question | Legal/product disclaimer for non-certification? |
| Reason | Report footers |
| Affected modules | reports, UI |
| Affected calculations | N/A |
| Affected reports | All |
| Owner | Legal/product |
| Priority | MEDIUM |
| Blocking phase | 11 |
| Required evidence or authority | Approved disclaimer text |
| Current status | MEDIUM |
| Resolution | |
| Resolution date | |

## D-028 — Transitional vs definitive

| Field | Value |
|-------|--------|
| Title | CBAM regime phase |
| Question | Which CBAM regime phase does pilot target? |
| Reason | Rule pack selection |
| Affected modules | rule packs |
| Affected calculations | Applicable boundaries |
| Affected reports | Regime labels |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 9 / 12 |
| Required evidence or authority | Regime selection |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-029 — Product CN effective dating

| Field | Value |
|-------|--------|
| Title | Product CN effective dating and CBAM product-profile versioning |
| Question | What are the exact business rules for non-overlapping `valid_from`/`valid_to`, when a new profile version is required, and how CN/AGC/route applicability changes are authorized? |
| Reason | Structural model supports temporal classifications; expert must define cutover and overlap rules |
| Affected modules | cbam product profiles, reference pins, routes |
| Affected calculations | Classification snapshot in every run |
| Affected reports | Goods identity sections |
| Owner | Domain expert + product |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 2 / 9 |
| Required evidence or authority | Classification change SOP |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-030 — Period and calculation approval ordering

| Field | Value |
|-------|--------|
| Title | Period approval and calculation-run approval ordering |
| Question | What is the final production order between calculation-run approval, period approval, and period lock? Who may approve each? |
| Reason | Dual approval surfaces must not invent a final order |
| Affected modules | workflows, approvals, calculation runs |
| Affected calculations | Which run becomes the locked snapshot |
| Affected reports | Reports that require locked period |
| Owner | Domain + product + security |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 11 |
| Required evidence or authority | Approval SOP |
| Current status | BLOCKED_DOMAIN |
| Resolution | Technical constraint only: period approval must link one exact `calculation_run_id`; locked period references one approved calculation snapshot; changing selected run requires new approval or revision. Final order remains unresolved. |
| Resolution date | |

## D-031 — Generic versus CBAM lock interaction

| Field | Value |
|-------|--------|
| Title | Generic versus CBAM lock interaction |
| Question | Beyond the architectural rule that CBAM lock is independent, what operational policy should operators follow regarding generic ReportingPeriod lock (recommended, ignored, or process-gated)? |
| Reason | Architecture already forbids auto sync; ops policy may still need confirmation |
| Affected modules | reporting_periods (read), cbam period bindings |
| Affected calculations | None directly if CBAM lock independent |
| Affected reports | None directly |
| Owner | Product + domain |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 2 / 11 |
| Required evidence or authority | Ops policy note |
| Current status | BLOCKED_DOMAIN |
| Resolution | Architectural rule (RESOLVED_ARCH separately): CBAM binding owns CBAM lock; generic lock is not source of truth; no automatic lock/unlock coupling. Operational preference TBD. |
| Resolution date | |

## D-032 — Allocation conservation

| Field | Value |
|-------|--------|
| Title | Allocation conservation and factor-sum rules |
| Question | What conservation rules and numeric tolerance apply when reconciling source quantities/emissions to allocated outputs? |
| Reason | Structural invariant exists; tolerance value must not be invented |
| Affected modules | allocation, calculation |
| Affected calculations | Allocation boundary |
| Affected reports | Allocation disclosures |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 8 / 9 |
| Required evidence or authority | Conservation + tolerance policy |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-033 — Inventory receipt and process consumption

| Field | Value |
|-------|--------|
| Title | Inventory receipt and process-consumption policy |
| Question | Which receipt/lot/consumption statuses are mandatory before calculation, and how are corrections/reversals authorized? |
| Reason | Engine must block on missing consumption; business gates TBD |
| Affected modules | inventory receipt/lot/consumption |
| Affected calculations | Runs that require consumption |
| Affected reports | Material balance annex |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 6 / 9 |
| Required evidence or authority | Inventory SOP |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-034 — Shared processes across products

| Field | Value |
|-------|--------|
| Title | Shared processes across products and routes |
| Question | May one installation process serve multiple products/routes, and how must shared quantities be allocated? |
| Reason | Process ownership is installation-scoped; sharing rules TBD |
| Affected modules | processes, routes, allocation |
| Affected calculations | Shared-process allocation |
| Affected reports | Process disclosures |
| Owner | Domain expert |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 4 / 8 |
| Required evidence or authority | Sharing policy |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-035 — Multi-installation period completeness

| Field | Value |
|-------|--------|
| Title | Multi-installation reporting-period completeness |
| Question | When an organization has multiple CBAM installations, what completeness rules apply before a period binding can leave data_collection? |
| Reason | Period binding is org-scoped; multi-site gates TBD |
| Affected modules | period bindings, validation |
| Affected calculations | Period runs coverage |
| Affected reports | Org-level operator report |
| Owner | Domain + product |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 2 / 11 |
| Required evidence or authority | Completeness checklist |
| Current status | BLOCKED_DOMAIN |
| Resolution | |
| Resolution date | |

## D-036 — Numeric precision and rounding

| Field | Value |
|-------|--------|
| Title | Intermediate numeric precision and final rounding policy |
| Question | What intermediate Decimal context/quantization and final reporting rounding are authorized? |
| Reason | Engine must be deterministic without inventing final rounding |
| Affected modules | calculation engine, reports |
| Affected calculations | All |
| Affected reports | All numeric fields |
| Owner | Domain expert + engineering |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 9 |
| Required evidence or authority | Rule-pack precision section |
| Current status | BLOCKED_DOMAIN |
| Resolution | Architectural constraints (not final values): Decimal only; engine version defines deterministic Decimal context; no uncontrolled runtime float; no intermediate rounding without approved rule pack; final reporting rounding remains blocked until expert approval; snapshots store raw normalized Decimal strings. |
| Resolution date | |

## D-037 — Unit-catalog pinning

| Field | Value |
|-------|--------|
| Title | Unit catalog and conversion-factor version pinning |
| Question | How are unit definitions and conversion factors versioned/pinned for CBAM, and who publishes updates? |
| Reason | Approved calculations must not drift when generic units change |
| Affected modules | reference_data units (read), cbam snapshots |
| Affected calculations | Unit-normalization boundary |
| Affected reports | Unit labels |
| Owner | Engineering + domain |
| Priority | HIGH |
| Blocking phase | 5 / 9 |
| Required evidence or authority | Unit pinning design sign-off |
| Current status | HIGH |
| Resolution | Architectural requirement: snapshots must preserve source unit, normalized unit, conversion-factor value, conversion-factor version or stable definition, conversion direction, and precision policy. |
| Resolution date | |

## D-038 — Verifier authorization

| Field | Value |
|-------|--------|
| Title | Verifier read-only authorization model |
| Question | What is the final verifier identity process, role mapping, and time-bound access policy? |
| Reason | Structure must support verifier read-only access without inventing external process |
| Affected modules | authz, evidence, reports, verification package |
| Affected calculations | Read of approved runs only |
| Affected reports | Download authz |
| Owner | Security + compliance |
| Priority | HIGH |
| Blocking phase | 11 |
| Required evidence or authority | Verifier access SOP |
| Current status | HIGH |
| Resolution | Structural requirements only: org-authorized read-only verifier access; explicit installation/period scope; optional time-bounded access; no mutation; evidence/report access separately controlled; verifier access audited. Final business role TBD. |
| Resolution date | |

## D-039 — Calculation cancellation and superseding

| Field | Value |
|-------|--------|
| Title | Calculation cancellation and superseding timing |
| Question | Which statuses may be cancelled, who may cancel, and when does a new run supersede a prior calculated/approved run? |
| Reason | Must not misuse `failed` as cancelled |
| Affected modules | calculation runs, workflows, API |
| Affected calculations | Run lifecycle |
| Affected reports | Runs eligible for reporting |
| Owner | Product + engineering |
| Priority | BLOCKED_DECISION |
| Blocking phase | 9 / 11 |
| Required evidence or authority | Lifecycle SOP |
| Current status | BLOCKED_DECISION |
| Resolution | Structural retention: optional `cancelled` status may exist in the model; until this decision is resolved, cancellation transitions must not be activated. `failed` must not mean cancelled. All history preserved. |
| Resolution date | |

## D-040 — Idempotency-store requirements

| Field | Value |
|-------|--------|
| Title | CBAM idempotency-store scope and retention |
| Question | Which store, retention TTL, and key scope apply for CBAM idempotent commands? |
| Reason | No general Idempotency-Key infrastructure exists in the repository today |
| Affected modules | cbam API, job execution (optional) |
| Affected calculations | Calculation request idempotency |
| Affected reports | Report/package generation idempotency |
| Owner | Engineering |
| Priority | HIGH |
| Blocking phase | Before first REQUIRED operation (import confirm / calc / report / package) |
| Required evidence or authority | Engineering design note |
| Current status | HIGH |
| Resolution | Capability is new. Operation matrix: staged-import confirmation REQUIRED; calculation request REQUIRED; report generation REQUIRED; verification-package generation REQUIRED; retryable background ops RECOMMENDED. See api-boundaries and roadmap. |
| Resolution date | |

## D-041 — Facility to installation cardinality

| Field | Value |
|-------|--------|
| Title | Facility ↔ CBAM installation cardinality |
| Question | Can one Facility have multiple CBAM installation profiles? Can one CBAM installation span multiple Facilities? |
| Reason | Must not silently hard-code 1:1 as permanent law |
| Affected modules | installation profiles |
| Affected calculations | Installation pinning |
| Affected reports | Installation identity |
| Owner | Domain + product |
| Priority | BLOCKED_DOMAIN |
| Blocking phase | 2 |
| Required evidence or authority | Pilot identity model |
| Current status | BLOCKED_DOMAIN |
| Resolution | Pilot constraint (temporary, not permanent): assume at most one active CBAM installation profile per Facility for the first pilot unless D-041 is resolved otherwise. Multi-facility spanning installations are out of scope until resolved. |
| Resolution date | |

## D-042 — Evidence storage implementation choice

| Field | Value |
|-------|--------|
| Title | CBAM evidence storage implementation choice |
| Question | Extract a shared evidence-storage port, or implement a CBAM-owned evidence service copying the established security pattern? |
| Reason | No shared attachment-storage port exists today (`activity_data.attachment_service` pattern only) |
| Affected modules | cbam evidence, optional shared port |
| Affected calculations | Trace to evidence checksum |
| Affected reports | Verification package files |
| Owner | Engineering |
| Priority | HIGH |
| Blocking phase | 2 (evidence links) |
| Required evidence or authority | Engineering ADR/note |
| Current status | HIGH |
| Resolution | |
| Resolution date | |

---

## Rules for implementers

1. Any feature depending on `BLOCKED_DOMAIN` / unresolved `BLOCKED_DECISION` must fail closed (`blocked` status with detail code `BLOCKED_DOMAIN` where applicable).
2. Closing a decision requires Resolution + Resolution date + authority evidence.
3. Golden tests only after closed D-007, D-008, D-014, D-015, D-036 (and related).
4. Architectural constraints marked in Resolution fields are binding; blank regulatory content remains blocked.
