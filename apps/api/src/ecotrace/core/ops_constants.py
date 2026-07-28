from typing import Final

FACILITY_TYPES: Final[frozenset[str]] = frozenset(
    {
        "manufacturing",
        "warehouse",
        "office",
        "laboratory",
        "wastewater_treatment",
        "energy_generation",
        "logistics_center",
        "agricultural_site",
        "other",
    }
)

EQUIPMENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "electricity_meter",
        "gas_meter",
        "water_meter",
        "fuel_tank",
        "boiler",
        "generator",
        "vehicle",
        "refrigeration_system",
        "production_machine",
        "wastewater_unit",
        "sensor",
        "other",
    }
)

DATA_SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "manual_entry",
        "csv_import",
        "excel_import",
        "utility_invoice",
        "erp",
        "scada",
        "meter",
        "sensor",
        "api",
        "mqtt",
        "other",
    }
)

UNIT_DIMENSIONS: Final[frozenset[str]] = frozenset(
    {
        "energy",
        "volume",
        "mass",
        "distance",
        "area",
        "count",
        "time",
        "transport_work",
        "percentage",
        "temperature",
        "other",
    }
)

ACTIVITY_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "electricity",
        "natural_gas",
        "stationary_fuel",
        "mobile_fuel",
        "water",
        "waste",
        "transport",
        "purchased_material",
        "production_output",
        "refrigerant",
        "steam",
        "heat",
        "cooling",
        "other",
    }
)

PERIOD_TYPES: Final[frozenset[str]] = frozenset({"monthly", "quarterly", "annual", "custom"})
PERIOD_STATUSES: Final[frozenset[str]] = frozenset({"open", "under_review", "locked", "archived"})

ACTIVITY_STATUSES: Final[frozenset[str]] = frozenset(
    {"draft", "submitted", "approved", "rejected", "archived"}
)

IMPORT_JOB_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "uploaded",
        "validating",
        "validation_failed",
        "ready",
        "importing",
        "completed",
        "completed_with_errors",
        "failed",
    }
)


ORG_ACCESS_DENIED_AS_NOT_FOUND: Final[bool] = True
