# CBAM Release Readiness

## Classification

**READY_FOR_DOMAIN_VALIDATION**

Not:

- READY_FOR_INTERNAL_PILOT (optional next step after expert review)  
- BLOCKED_BY_TECHNICAL_DEFECTS  
- PRODUCTION_READY  
- REGULATORY_READY  
- OFFICIAL_CBAM_READY  

## Why this classification

Technical Phase 2–6 workflow is implemented, audited, and gated (Phase 7).  
Official workbook, regulatory mappings, and authoritative factor/activity rules remain blocked pending domain experts.

## Preconditions for advancing

| Next class | Requires |
|------------|----------|
| READY_FOR_INTERNAL_PILOT | Domain walkthrough of MVP + accepted limitation sign-off |
| REGULATORY / OFFICIAL | Approved official workbook + cell mappings + authoritative rules |

## Module status API

`status = mvp_ready_for_domain_validation`  
`complianceClaim = false`  
`official mapping` remains BLOCKED in export readiness and docs.
