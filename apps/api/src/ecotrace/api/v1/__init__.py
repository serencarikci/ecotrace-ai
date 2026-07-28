from fastapi import APIRouter

from ecotrace.api.v1 import (
    activity_records,
    attachments,
    auth,
    carbon_inventories,
    carbon_preferences,
    data_sources,
    emission_factor_sources,
    emission_factors,
    equipment,
    facilities,
    health,
    imports,
    organizations,
    production_lines,
    reference,
    reporting_periods,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(facilities.router)
api_router.include_router(production_lines.router)
api_router.include_router(equipment.router)
api_router.include_router(data_sources.router)
api_router.include_router(reference.router)
api_router.include_router(reporting_periods.router)
api_router.include_router(activity_records.router)
api_router.include_router(attachments.router)
api_router.include_router(imports.router)
api_router.include_router(emission_factor_sources.router)
api_router.include_router(emission_factors.router)
api_router.include_router(carbon_preferences.router)
api_router.include_router(carbon_inventories.router)
api_router.include_router(carbon_inventories.items_router)
api_router.include_router(health.meta_router)
