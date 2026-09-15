# User-Facing Language Audit

Date: 2026-08-09  
Target language: English (A2–B1)  
Scope: end-user visible UI and API messages (not historical docs / migrations / comments)

## Screens reviewed

| Screen | Path / area | Result |
|--------|-------------|--------|
| App shell navigation | `shell.component.html` | English |
| SKDM shell | `cbam-shell.component.*` | English |
| Installation list | `installation-list.component.*` | English |
| New installation | `installation-form.component.*` | English |
| Installation details | `installation-detail.component.*` | English |
| Reporting periods list | `period-list.component.*` | English |
| Reporting period details (all tabs) | `period-detail.component.*` | English |
| Shared 409 / API errors | `error.util.ts` | English |
| Export readiness labels | `export_readiness_service.py` | English |
| Period summary title/HTML | `period_summary_service.py` | English |
| Calculation user messages | `calculation_service.py` | English |
| Internal Excel banner | template builder / export services | English |

## Turkish labels replaced (examples)

### Navigation / titles

| Before | After |
|--------|-------|
| Tesisler | Installations |
| Dönemler | Reporting Periods |
| SKDM Tesisleri | SKDM Installations |
| Yeni tesis / Yeni SKDM tesisi | New Installation |
| SKDM Dönemleri | Reporting Periods |
| SKDM dönem bağlama | Reporting Period Details |
| Listeye dön | Back |

### Tabs

| Before | After |
|--------|-------|
| Üretim | Production |
| Faaliyet Verileri | Activities |
| Satın Alınan Girdiler | Purchased Inputs |
| Alokasyon | Allocation |
| Faktörler | Factors |
| Hesaplama | Calculation |
| Rapor / Excel | Report / Excel |

### Buttons / actions

| Before | After |
|--------|-------|
| Kaydet | Save |
| Arşivle | Archive |
| Aktifleştir | Activate |
| Detay | View |
| Filtrele | Filter |
| Excel Oluştur | Generate Excel |
| Hesaplamayı çalıştır | Calculate |
| Çözümle / Yeniden Çözümle | Resolve / Resolve Again |
| Yeniden hesapla | Recalculate |
| Veri toplamayı aç | Open Data Collection |

### Empty states

| Before | After |
|--------|-------|
| Bu dönem için henüz üretim verisi girilmedi. | No production data has been added for this period. |
| Bu dönem için henüz faaliyet verisi girilmedi. | No activity data has been added for this period. |
| Bu dönem için henüz satın alınan girdi kaydı bulunmuyor. | No purchased inputs have been added for this period. |
| Bu dönem için henüz alokasyon kuralı yok. | No allocation rules have been added for this period. |

### Validation / UI errors

| Before | After |
|--------|-------|
| Manuel oran için gerekçe zorunludur. | Reason is required. |
| Üretim oranı için hedef ve baz üretim kayıtları seçilmelidir. | Select target production and total base production. |
| Çözümlemek için bir kaynak seçin. | Select a source to resolve. |
| 409 Turkish conflict wording | This record was changed by another user. Please refresh the page and try again. |

### Status display labels (enums unchanged)

| Internal value | Display label |
|----------------|---------------|
| RESOLVED_PRIMARY | Primary Data Used |
| RESOLVED_DEFAULT | Default Reference Used |
| UNRESOLVED | Not Resolved |
| AMBIGUOUS | More Than One Match |
| INCOMPATIBLE_UNIT | Unit Does Not Match |
| OUTSIDE_VALIDITY | Value Is Not Valid for This Date |
| BLOCKED | Blocked |
| CALCULATED | Calculated |
| INVALID_INPUT | Invalid Input |
| UNRESOLVED_FACTOR | Factor Not Resolved |
| AMBIGUOUS_FACTOR | More Than One Factor Match |
| UNSUPPORTED_FORMULA | Formula Not Supported |
| READY | Ready |
| READY_WITH_WARNINGS | Ready with Warnings |
| NOT_READY | Not Ready |

Canonical frontend mapping: `apps/web/src/app/features/cbam/cbam-display-labels.ts`

### Report / export

| Before | After |
|--------|-------|
| SKDM Dönem Özeti | SKDM Period Summary |
| Üretim verisi | Production Data |
| Faaliyet verisi | Activity Data |
| Satın alınan girdiler | Purchased Inputs |
| Alokasyon | Allocation |
| Faktör çözümleme | Factor Resolution |
| Hesaplama | Calculation |
| Excel eşlemeleri | Excel Mapping |
| Hazır / Uyarılarla Hazır / Hazır Değil | Ready / Ready with Warnings / Not Ready |
| Excel Oluştur | Generate Excel |
| Dışa aktarım geçmişi | Export History |

### Calculation messages (API → UI)

| Before | After |
|--------|-------|
| Faktör çözümlenemedi. | Factor could not be resolved. |
| Birim uyumsuz … | Units do not match. |
| Alokasyon gerekli — … | Allocation is required. … |
| Formül desteklenmiyor. | Formula is not supported. |
| Faktör çözümü belirsiz … | More than one factor matches this record. |

## Intentionally retained technical terms

- CBAM, SKDM
- Allocation, Emission Factor / Factor, Primary Data, Default Reference
- Reporting Period, Installation, Activity, Production, Purchased Input
- Calculation, Excel, CO2e
- Internal status/enum codes shown only as technical codes when needed (e.g. `draft`, `ACTIVE`)
- Route URLs unchanged (`/app/cbam/installations`, etc.)
- API paths, DB tables, Python class names unchanged

## Remaining Turkish user-facing text

**0**

Justified exceptions: none.

Non-user-facing Turkish may remain in:

- historical documentation under `docs/cbam/`
- migration descriptions
- internal comments
- implementation/audit reports

These were intentionally not rewritten.

## Post-change search

- `apps/web/src/**/*.{ts,html}`: no Turkish characters (`ğüşıöç…`)
- `apps/api/src/ecotrace/modules/cbam/**/*.py`: no Turkish characters
- Keyword sweep for common Turkish UI words in CBAM frontend/backend: clear
