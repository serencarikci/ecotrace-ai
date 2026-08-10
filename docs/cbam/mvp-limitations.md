# SKDM MVP Limitations

## Technical (accepted)

- Official CBAM workbook mapping unavailable (**BLOCKED**)
- Only one calculation formula family: `MULTIPLY_ACTIVITY_BY_FACTOR`
- Only three allocation methods
- Same-unit technical totals are optional and non-regulatory
- Binary XLSX checksum may vary with ZIP metadata; manifest is authoritative
- No PDF generation in CBAM module
- No approve/lock period workflow yet
- Idempotency store (D-040) deferred

## Regulatory / domain (blocked)

See [domain-expert-open-questions.md](domain-expert-open-questions.md).

## Security posture (MVP)

- Tenant isolation via organization scope + 404 non-disclosure
- Export path traversal guards
- `.xlsm` rejected
- Spreadsheet formula-injection neutralization for exported data text
- Template formulas preserved and not overwritten by data writes

## Classification constraints

Do not label the module:

- PRODUCTION_READY  
- REGULATORY_READY  
- OFFICIAL_CBAM_READY  

while official mapping and domain rules remain unresolved.
