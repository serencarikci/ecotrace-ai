# SKDM MVP Workflow

## Navigation

SKDM → Tesisler → Dönemler → Dönem Detayı

## Period tabs

1. **Üretim** — production records  
2. **Faaliyet** — activity records (+ primary properties via Faktörler)  
3. **Satın Alınan Girdiler** — purchased/consumed inputs  
4. **Alokasyon** — rules + results  
5. **Faktörler** — resolve primary/default factors  
6. **Hesaplama** — execute minimal multiply engine  
7. **Rapor / Excel** — readiness, SKDM Dönem Özeti, internal workbook

## Happy path (technical fixture)

1. Create installation + open period data collection  
2. Production: 500 t base, 100 t target  
3. Activity: 100 MWh electricity  
4. Allocation PRODUCTION_QUANTITY_RATIO → 0.2 → 20 MWh  
5. Activate synthetic factor 0.4 tCO2e/MWh (**not** a regulatory claim)  
6. Resolve factor → execute calculation → **8 tCO2e**  
7. Summary + export readiness → generate internal XLSX  
8. Workbook contains 20 MWh, 0.4, 8 tCO2e from Phase 5 results

## Labels

- Use **Excel Oluştur** / **SKDM Dönem Özeti**  
- Do **not** use “Resmi CBAM Gönder” until an official template exists
