# CBAM Activity Data Model (Phase 3)

## Entities

| Entity | Table | Purpose |
|--------|-------|---------|
| `CbamProductionRecord` | `cbam_production_records` | Production quantity per installation/period |
| `CbamActivityRecord` | `cbam_activity_records` | Energy/fuel/process activity quantities |
| `CbamActivityProperty` | `cbam_activity_properties` | Optional PRIMARY property overrides |
| `CbamPurchasedInputRecord` | `cbam_purchased_input_records` | Purchased material quantities |

## Activity groups (collection groupings only)

`DIRECT` · `PURCHASED_ENERGY` · `PROCESS` · `OTHER`

These are **not** claimed to be final CBAM regulatory categories (see B-01).

## Activity types (controlled allow-list)

`ELECTRICITY`, `NATURAL_GAS`, `DIESEL`, `GASOLINE`, `LPG`, `PURCHASED_STEAM`, `PROCESS_ACTIVITY`, `OTHER_FUEL`, `OTHER`

Each type declares an allowed unit family. No emission factors are attached.

## Units

Energy: `kWh`, `MWh`, `GJ`  
Volume: `L`, `m3`  
Mass: `kg`, `t`  
Count: `unit`

No automatic conversion between incompatible dimensions.
