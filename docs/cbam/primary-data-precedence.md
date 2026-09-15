# Primary Data Precedence (Phase 4B)

Initial deterministic policy:

1. ACTIVE compatible **PRIMARY** value on the source record (`CbamActivityProperty` or purchased embedded PRIMARY)
2. ACTIVE compatible organization-level **PRIMARY** factor value
3. ACTIVE compatible **DEFAULT_REFERENCE** factor value
4. **UNRESOLVED**

Equal-rank ties → **AMBIGUOUS** (never arbitrary selection).

This policy is intentionally simple. Do not assume PRIMARY always wins for every future regulatory parameter until domain experts confirm per-parameter rules.
