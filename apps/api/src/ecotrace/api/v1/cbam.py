from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse

from ecotrace.api.dependencies.auth import (
    ClientIp,
    CurrentUser,
    DbSession,
    RequestId,
    UserAgentHeader,
)
from ecotrace.modules.cbam.application import (
    activity_record_service,
    allocation_rule_service,
    allocation_service,
    calculation_service,
    cn_catalog_service,
    direct_emissions_allocation_service,
    export_readiness_service,
    export_template_service,
    factor_catalog_service,
    factor_resolution_service,
    indirect_emissions_allocation_service,
    installation_service,
    monthly_production_basis_service,
    period_binding_service,
    period_summary_service,
    precursor_default_catalog_service,
    product_embedded_emissions_service,
    product_profile_service,
    production_process_service,
    production_record_service,
    purchased_electricity_service,
    purchased_input_service,
    purchased_precursor_service,
    reference_source_service,
    stationary_combustion_api_service,
    workbook_export_service,
)
from ecotrace.modules.cbam.application.activity_record_service import (
    ActivityPropertyInput,
    ActivityPropertyResponse,
    ActivityRecordCreate,
    ActivityRecordResponse,
    ActivityRecordUpdate,
    ActivityRecordVersionRequest,
)
from ecotrace.modules.cbam.application.allocation_rule_service import (
    AllocationRuleCreate,
    AllocationRuleResponse,
    AllocationRuleUpdate,
    AllocationRuleVersionRequest,
)
from ecotrace.modules.cbam.application.allocation_service import AllocationResultResponse
from ecotrace.modules.cbam.application.calculation_service import (
    CalculationDefinitionResponse,
    CalculationResultResponse,
    CalculationRunCreate,
    CalculationRunExecuteRequest,
    CalculationRunResponse,
)
from ecotrace.modules.cbam.application.catalogs import (
    ActivityPropertyTypeResponse,
    ActivityTypeResponse,
    UnitResponse,
    list_activity_property_type_responses,
    list_activity_type_responses,
    list_unit_responses,
)
from ecotrace.modules.cbam.application.cn_catalog_service import (
    CnCodeResponse,
    ControlledListValueResponse,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
    DirectEmissionsAllocationExecutionResponse,
    DirectEmissionsAllocationPeriodSummary,
    DirectEmissionsAllocationReadiness,
    DirectEmissionsAllocationResultDetail,
    DirectEmissionsAllocationResultSummary,
)
from ecotrace.modules.cbam.application.export_readiness_service import ExportReadinessResponse
from ecotrace.modules.cbam.application.export_template_service import ExportTemplateResponse
from ecotrace.modules.cbam.application.factor_catalog_service import (
    FactorDefinitionResponse,
    FactorValueCreate,
    FactorValueResponse,
    FactorValueUpdate,
    FactorValueVersionRequest,
)
from ecotrace.modules.cbam.application.factor_resolution_service import FactorResolutionResponse
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    IndirectEmissionsAllocationExecuteRequest,
    IndirectEmissionsAllocationExecutionResponse,
    IndirectEmissionsAllocationPeriodSummary,
    IndirectEmissionsAllocationReadiness,
    IndirectEmissionsAllocationResultDetail,
    IndirectEmissionsAllocationResultSummary,
)
from ecotrace.modules.cbam.application.installation_service import (
    InstallationCreate,
    InstallationResponse,
    InstallationUpdate,
    InstallationVersionRequest,
)
from ecotrace.modules.cbam.application.module_status_service import (
    CbamModuleStatusResponse,
    get_module_status,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
    MonthlyProductionBasisResponse,
    MonthlyProductionBasisSummary,
    MonthlyProductionBasisUpdate,
)
from ecotrace.modules.cbam.application.official_see_export import (
    service as official_see_export_service,
)
from ecotrace.modules.cbam.application.official_see_export.schemas import (
    OfficialSeeExportArtifactResponse,
    OfficialSeeExportCreateRequest,
    OfficialSeeExportReadiness,
    OfficialSeeExportRunResponse,
)
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingResponse,
    PeriodBindingUpdate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.period_summary_service import PeriodSummaryResponse
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.precursor_default_catalog_service import (
    PrecursorDefaultResolution,
    PrecursorDefaultResolveRequest,
    PrecursorDefaultValueResponse,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_service import (
    ProductEmbeddedEmissionsExecuteRequest,
    ProductEmbeddedEmissionsExecutionResponse,
    ProductEmbeddedEmissionsPeriodSummary,
    ProductEmbeddedEmissionsReadiness,
    ProductEmbeddedEmissionsResultDetail,
    ProductEmbeddedEmissionsResultSummary,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileResponse,
    ProductProfileUpdate,
    ProductProfileVersionRequest,
)
from ecotrace.modules.cbam.application.production_process_service import (
    ControlledListResponse,
    ProductionProcessCreate,
    ProductionProcessMetadataResponse,
    ProductionProcessReadiness,
    ProductionProcessResponse,
    ProductionProcessSummary,
    ProductionProcessUpdate,
    ProductionProcessVersionRequest,
    ProductUseCreate,
    ProductUseResponse,
    ProductUseUpdate,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionProfileLinkSummary,
    ProductionRecordCreate,
    ProductionRecordResponse,
    ProductionRecordUpdate,
    ProductionRecordVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    PurchasedElectricityExecuteRequest,
    PurchasedElectricityExecutionResponse,
    PurchasedElectricityFactorResolution,
    PurchasedElectricityPeriodSummary,
    PurchasedElectricityResultDetail,
    PurchasedElectricityResultSummary,
)
from ecotrace.modules.cbam.application.purchased_input_service import (
    PurchasedInputCreate,
    PurchasedInputResponse,
    PurchasedInputUpdate,
    PurchasedInputVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PrecursorProductUseCreate,
    PrecursorProductUseResponse,
    PrecursorProductUseUpdate,
    PurchasedPrecursorCreate,
    PurchasedPrecursorMetadataResponse,
    PurchasedPrecursorReadiness,
    PurchasedPrecursorResponse,
    PurchasedPrecursorSummary,
    PurchasedPrecursorUpdate,
    PurchasedPrecursorVersionRequest,
)
from ecotrace.modules.cbam.application.reference_source_service import (
    ReferenceSourceCreate,
    ReferenceSourceResponse,
    ReferenceSourceUpdate,
)
from ecotrace.modules.cbam.application.stationary_combustion_api_service import (
    StationaryCombustionExecutionApiRequest,
    StationaryCombustionExecutionApiResponse,
    StationaryCombustionFuelResponse,
    StationaryCombustionParametersResponse,
    StationaryCombustionResultSummaryResponse,
)
from ecotrace.modules.cbam.application.stationary_combustion_coverage_service import (
    StationaryCombustionActivityCoverageItem,
)
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    StationaryCombustionResultResponse,
)
from ecotrace.modules.cbam.application.stationary_combustion_summary_service import (
    StationaryCombustionPeriodSummaryResponse,
)
from ecotrace.modules.cbam.application.workbook_export_service import (
    ExportArtifactResponse,
    ExportCreateRequest,
    ExportRunResponse,
)
from ecotrace.shared.domain.schemas import Page

router = APIRouter(prefix="/cbam", tags=["CBAM"])


@router.get(
    "/organizations/{organization_id}/module-status",
    response_model=CbamModuleStatusResponse,
    summary="CBAM module foundation status",
    description=(
        "Reports CBAM foundation aggregate availability. "
        "Does not perform calculations, reporting, or compliance assessment."
    ),
)
def cbam_module_status(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> CbamModuleStatusResponse:
    return get_module_status(db, user, organization_id)


@router.get(
    "/organizations/{organization_id}/installations",
    response_model=Page[InstallationResponse],
)
def list_installations(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    search: str | None = None,
) -> Page[InstallationResponse]:
    return installation_service.list_installations(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
    )


@router.post(
    "/organizations/{organization_id}/installations",
    response_model=InstallationResponse,
    status_code=201,
)
def create_installation(
    organization_id: UUID,
    payload: InstallationCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InstallationResponse:
    return installation_service.create_installation(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/installations/{installation_id}",
    response_model=InstallationResponse,
)
def get_installation(
    organization_id: UUID,
    installation_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> InstallationResponse:
    return installation_service.get_installation(db, user, organization_id, installation_id)


@router.patch(
    "/organizations/{organization_id}/installations/{installation_id}",
    response_model=InstallationResponse,
)
def update_installation(
    organization_id: UUID,
    installation_id: UUID,
    payload: InstallationUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InstallationResponse:
    return installation_service.update_installation(
        db,
        user,
        organization_id,
        installation_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/installations/{installation_id}/activate",
    response_model=InstallationResponse,
)
def activate_installation(
    organization_id: UUID,
    installation_id: UUID,
    payload: InstallationVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InstallationResponse:
    return installation_service.activate_installation(
        db,
        user,
        organization_id,
        installation_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/installations/{installation_id}/archive",
    response_model=InstallationResponse,
)
def archive_installation(
    organization_id: UUID,
    installation_id: UUID,
    payload: InstallationVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InstallationResponse:
    return installation_service.archive_installation(
        db,
        user,
        organization_id,
        installation_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings",
    response_model=Page[PeriodBindingResponse],
)
def list_period_bindings(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
) -> Page[PeriodBindingResponse]:
    return period_binding_service.list_period_bindings(
        db, user, organization_id, page=page, page_size=page_size, status=status
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings",
    response_model=PeriodBindingResponse,
    status_code=201,
)
def create_period_binding(
    organization_id: UUID,
    payload: PeriodBindingCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodBindingResponse:
    return period_binding_service.create_period_binding(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}",
    response_model=PeriodBindingResponse,
)
def get_period_binding(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PeriodBindingResponse:
    return period_binding_service.get_period_binding(db, user, organization_id, binding_id)


@router.patch(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}",
    response_model=PeriodBindingResponse,
)
def update_period_binding(
    organization_id: UUID,
    binding_id: UUID,
    payload: PeriodBindingUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodBindingResponse:
    return period_binding_service.update_period_binding(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/open-data-collection",
    response_model=PeriodBindingResponse,
)
def open_data_collection(
    organization_id: UUID,
    binding_id: UUID,
    payload: PeriodBindingVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodBindingResponse:
    return period_binding_service.open_data_collection(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/archive",
    response_model=PeriodBindingResponse,
)
def archive_period_binding(
    organization_id: UUID,
    binding_id: UUID,
    payload: PeriodBindingVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodBindingResponse:
    return period_binding_service.archive_period_binding(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/cn-codes",
    response_model=Page[CnCodeResponse],
    summary="Search active CBAM CN codes",
)
def list_cn_codes(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    q: str | None = Query(None),
    sector: str | None = Query(None),
) -> Page[CnCodeResponse]:
    return cn_catalog_service.list_cn_codes(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        q=q,
        sector=sector,
    )


@router.get(
    "/organizations/{organization_id}/cn-codes/{cn_code_id}",
    response_model=CnCodeResponse,
    summary="Get one CBAM CN code with dataset provenance",
)
def get_cn_code(
    organization_id: UUID,
    cn_code_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> CnCodeResponse:
    return cn_catalog_service.get_cn_code(db, user, organization_id, cn_code_id)


@router.get(
    "/organizations/{organization_id}/cn-controlled-lists/{list_code}",
    response_model=list[ControlledListValueResponse],
    summary="List controlled values for a CN-related code list",
)
def list_cn_controlled_list_values(
    organization_id: UUID,
    list_code: str,
    db: DbSession,
    user: CurrentUser,
) -> list[ControlledListValueResponse]:
    from ecotrace.modules.cbam.application.permissions import require_cbam_view

    require_cbam_view(db, user, organization_id)
    return cn_catalog_service.list_controlled_list_values(db, list_code=list_code)


@router.get(
    "/organizations/{organization_id}/product-profile-versions",
    response_model=Page[ProductProfileResponse],
)
def list_product_profiles(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    product_id: UUID | None = Query(None, alias="productId"),
    status: str | None = None,
) -> Page[ProductProfileResponse]:
    return product_profile_service.list_product_profiles(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        product_id=product_id,
        status=status,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-profiles",
    response_model=Page[ProductProfileResponse],
    summary="List product profiles available for a reporting-period binding",
)
def list_product_profiles_for_binding(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
) -> Page[ProductProfileResponse]:
    return product_profile_service.list_product_profiles_for_binding(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.post(
    "/organizations/{organization_id}/product-profile-versions",
    response_model=ProductProfileResponse,
    status_code=201,
)
def create_product_profile(
    organization_id: UUID,
    payload: ProductProfileCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductProfileResponse:
    return product_profile_service.create_product_profile(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.patch(
    "/organizations/{organization_id}/product-profile-versions/{profile_id}",
    response_model=ProductProfileResponse,
    summary="Update a draft product profile",
)
def update_product_profile_draft(
    organization_id: UUID,
    profile_id: UUID,
    payload: ProductProfileUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductProfileResponse:
    return product_profile_service.update_product_profile_draft(
        db,
        user,
        organization_id,
        profile_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/product-profile-versions/{profile_id}/publish",
    response_model=ProductProfileResponse,
    summary="Publish a classification-ready draft product profile",
)
def publish_product_profile(
    organization_id: UUID,
    profile_id: UUID,
    payload: ProductProfileVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductProfileResponse:
    return product_profile_service.publish_product_profile(
        db,
        user,
        organization_id,
        profile_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/product-profile-versions/{profile_id}",
    response_model=ProductProfileResponse,
)
def get_product_profile(
    organization_id: UUID,
    profile_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductProfileResponse:
    return product_profile_service.get_product_profile(db, user, organization_id, profile_id)


@router.post(
    "/organizations/{organization_id}/product-profile-versions/{profile_id}/archive",
    response_model=ProductProfileResponse,
)
def archive_product_profile(
    organization_id: UUID,
    profile_id: UUID,
    payload: ProductProfileVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductProfileResponse:
    return product_profile_service.archive_product_profile(
        db,
        user,
        organization_id,
        profile_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/activity-types",
    response_model=list[ActivityTypeResponse],
)
def list_activity_types(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[ActivityTypeResponse]:
    require_cbam_view(db, user, organization_id)
    return list_activity_type_responses()


@router.get(
    "/organizations/{organization_id}/units",
    response_model=list[UnitResponse],
)
def list_units(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[UnitResponse]:
    require_cbam_view(db, user, organization_id)
    return list_unit_responses()


@router.get(
    "/organizations/{organization_id}/activity-property-types",
    response_model=list[ActivityPropertyTypeResponse],
)
def list_activity_property_types(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[ActivityPropertyTypeResponse]:
    require_cbam_view(db, user, organization_id)
    return list_activity_property_type_responses()


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-profile-link-summary",
    response_model=ProductionProfileLinkSummary,
    summary="Authoritative production↔profile link readiness for a binding",
)
def get_production_profile_link_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductionProfileLinkSummary:
    return production_record_service.get_production_profile_link_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/monthly-production-basis",
    response_model=Page[MonthlyProductionBasisResponse],
    summary="List monthly production-basis rows (workbook D/E)",
)
def list_monthly_production_basis(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[MonthlyProductionBasisResponse]:
    return monthly_production_basis_service.list_monthly_production_basis(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/monthly-production-basis",
    response_model=MonthlyProductionBasisResponse,
    status_code=201,
    summary="Create a monthly production-basis row (workbook D/E)",
)
def create_monthly_production_basis(
    organization_id: UUID,
    binding_id: UUID,
    payload: MonthlyProductionBasisCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> MonthlyProductionBasisResponse:
    return monthly_production_basis_service.create_monthly_production_basis(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/monthly-production-basis-summary",
    response_model=MonthlyProductionBasisSummary,
    summary="Authoritative monthly D/E coverage and compatibility summary",
)
def get_monthly_production_basis_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> MonthlyProductionBasisSummary:
    return monthly_production_basis_service.get_monthly_production_basis_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/monthly-production-basis/{record_id}",
    response_model=MonthlyProductionBasisResponse,
)
def get_monthly_production_basis(
    organization_id: UUID,
    record_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> MonthlyProductionBasisResponse:
    return monthly_production_basis_service.get_monthly_production_basis(
        db, user, organization_id, record_id
    )


@router.patch(
    "/organizations/{organization_id}/monthly-production-basis/{record_id}",
    response_model=MonthlyProductionBasisResponse,
)
def update_monthly_production_basis(
    organization_id: UUID,
    record_id: UUID,
    payload: MonthlyProductionBasisUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> MonthlyProductionBasisResponse:
    return monthly_production_basis_service.update_monthly_production_basis(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.delete(
    "/organizations/{organization_id}/monthly-production-basis/{record_id}",
    status_code=204,
    response_class=Response,
    summary="Delete a monthly production-basis draft row",
)
def delete_monthly_production_basis(
    organization_id: UUID,
    record_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> Response:
    monthly_production_basis_service.delete_monthly_production_basis(
        db,
        user,
        organization_id,
        record_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    return Response(status_code=204)


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/readiness",
    response_model=DirectEmissionsAllocationReadiness,
    summary="Direct-emissions allocation readiness (authoritative binding-wide)",
)
def get_direct_emissions_allocation_readiness(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> DirectEmissionsAllocationReadiness:
    return direct_emissions_allocation_service.get_direct_emissions_allocation_readiness(
        db, user, organization_id, binding_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/executions",
    response_model=DirectEmissionsAllocationExecutionResponse,
    status_code=201,
    summary="Execute stationary-combustion direct-emissions allocation (Phase 7A-2)",
    responses={
        200: {
            "description": "Exact idempotent replay",
            "model": DirectEmissionsAllocationExecutionResponse,
        },
        201: {
            "description": "First successful execution",
            "model": DirectEmissionsAllocationExecutionResponse,
        },
        409: {"description": "IDEMPOTENCY_KEY_REUSED or referenced-input conflict"},
    },
)
def execute_direct_emissions_allocation(
    organization_id: UUID,
    binding_id: UUID,
    body: DirectEmissionsAllocationExecuteRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    response: Response,
) -> DirectEmissionsAllocationExecutionResponse:
    result = direct_emissions_allocation_service.execute_direct_emissions_allocation(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    response.status_code = 200 if result.idempotent_replay else 201
    return result


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/results",
    response_model=Page[DirectEmissionsAllocationResultSummary],
    summary="List direct-emissions allocation results (newest first)",
)
def list_direct_emissions_allocation_results(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[DirectEmissionsAllocationResultSummary]:
    return direct_emissions_allocation_service.list_direct_emissions_allocation_results(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/results/{result_id}",
    response_model=DirectEmissionsAllocationResultDetail,
    summary="Direct-emissions allocation result detail (immutable snapshot)",
)
def get_direct_emissions_allocation_result(
    organization_id: UUID,
    binding_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> DirectEmissionsAllocationResultDetail:
    return direct_emissions_allocation_service.get_direct_emissions_allocation_result(
        db, user, organization_id, binding_id, result_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/summary",
    response_model=DirectEmissionsAllocationPeriodSummary,
    summary="Direct-emissions allocation period summary (current pointer)",
)
def get_direct_emissions_allocation_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> DirectEmissionsAllocationPeriodSummary:
    return direct_emissions_allocation_service.get_direct_emissions_allocation_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/factors/default",
    response_model=PurchasedElectricityFactorResolution,
    summary="Resolve platform-default electricity factor (Phase 8A; may be unresolved)",
)
def get_purchased_electricity_default_factor(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    reference_date: date | None = Query(None, alias="referenceDate"),
) -> PurchasedElectricityFactorResolution:
    return purchased_electricity_service.get_purchased_electricity_default_factor(
        db, user, organization_id, binding_id, reference_date=reference_date
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/readiness",
    response_model=PurchasedElectricityPeriodSummary,
    summary="Purchased-electricity readiness / period summary (Phase 8A)",
)
def get_purchased_electricity_readiness(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedElectricityPeriodSummary:
    return purchased_electricity_service.get_purchased_electricity_readiness(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/summary",
    response_model=PurchasedElectricityPeriodSummary,
    summary="Purchased-electricity period summary (Phase 8A)",
)
def get_purchased_electricity_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedElectricityPeriodSummary:
    return purchased_electricity_service.get_purchased_electricity_summary(
        db, user, organization_id, binding_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/executions",
    response_model=PurchasedElectricityExecutionResponse,
    status_code=201,
    summary="Execute purchased-electricity indirect emissions (Phase 8A)",
    responses={
        200: {
            "description": "Exact idempotent replay",
            "model": PurchasedElectricityExecutionResponse,
        },
        201: {
            "description": "First successful execution",
            "model": PurchasedElectricityExecutionResponse,
        },
        409: {"description": "IDEMPOTENCY_KEY_REUSED"},
    },
)
def execute_purchased_electricity(
    organization_id: UUID,
    binding_id: UUID,
    body: PurchasedElectricityExecuteRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    response: Response,
) -> PurchasedElectricityExecutionResponse:
    result = purchased_electricity_service.execute_purchased_electricity(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    response.status_code = 200 if result.idempotent_replay else 201
    return result


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/results",
    response_model=Page[PurchasedElectricityResultSummary],
    summary="List purchased-electricity results (newest first)",
)
def list_purchased_electricity_results(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[PurchasedElectricityResultSummary]:
    return purchased_electricity_service.list_purchased_electricity_results(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/results/{result_id}",
    response_model=PurchasedElectricityResultDetail,
    summary="Purchased-electricity result detail (immutable snapshot)",
)
def get_purchased_electricity_result(
    organization_id: UUID,
    binding_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedElectricityResultDetail:
    return purchased_electricity_service.get_purchased_electricity_result(
        db, user, organization_id, binding_id, result_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/readiness",
    response_model=IndirectEmissionsAllocationReadiness,
    summary="Indirect-emissions allocation readiness (authoritative binding-wide)",
)
def get_indirect_emissions_allocation_readiness(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> IndirectEmissionsAllocationReadiness:
    return indirect_emissions_allocation_service.get_indirect_emissions_allocation_readiness(
        db, user, organization_id, binding_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/executions",
    response_model=IndirectEmissionsAllocationExecutionResponse,
    status_code=201,
    summary="Execute purchased-electricity indirect-emissions allocation (Phase 8C)",
    responses={
        200: {
            "description": "Exact idempotent replay",
            "model": IndirectEmissionsAllocationExecutionResponse,
        },
        201: {
            "description": "First successful execution",
            "model": IndirectEmissionsAllocationExecutionResponse,
        },
        409: {"description": "IDEMPOTENCY_KEY_REUSED or referenced-input conflict"},
    },
)
def execute_indirect_emissions_allocation(
    organization_id: UUID,
    binding_id: UUID,
    body: IndirectEmissionsAllocationExecuteRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    response: Response,
) -> IndirectEmissionsAllocationExecutionResponse:
    result = indirect_emissions_allocation_service.execute_indirect_emissions_allocation(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    response.status_code = 200 if result.idempotent_replay else 201
    return result


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/results",
    response_model=Page[IndirectEmissionsAllocationResultSummary],
    summary="List indirect-emissions allocation results (newest first)",
)
def list_indirect_emissions_allocation_results(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[IndirectEmissionsAllocationResultSummary]:
    return indirect_emissions_allocation_service.list_indirect_emissions_allocation_results(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/results/{result_id}",
    response_model=IndirectEmissionsAllocationResultDetail,
    summary="Indirect-emissions allocation result detail (immutable snapshot)",
)
def get_indirect_emissions_allocation_result(
    organization_id: UUID,
    binding_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> IndirectEmissionsAllocationResultDetail:
    return indirect_emissions_allocation_service.get_indirect_emissions_allocation_result(
        db, user, organization_id, binding_id, result_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/summary",
    response_model=IndirectEmissionsAllocationPeriodSummary,
    summary="Indirect-emissions allocation period summary",
)
def get_indirect_emissions_allocation_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> IndirectEmissionsAllocationPeriodSummary:
    return indirect_emissions_allocation_service.get_indirect_emissions_allocation_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/production-processes/metadata",
    response_model=ProductionProcessMetadataResponse,
    summary="Production-process controlled lists and workbook metadata (Phase 9A)",
)
def get_production_process_metadata(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductionProcessMetadataResponse:
    return production_process_service.get_production_process_metadata(db, user, organization_id)


@router.get(
    "/organizations/{organization_id}/production-processes/controlled-lists",
    response_model=list[ControlledListResponse],
    summary="Production-process controlled lists (workbook extraction)",
)
def list_production_process_controlled_lists(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[ControlledListResponse]:
    return production_process_service.list_controlled_lists_for_processes(db, user, organization_id)


@router.get(
    "/organizations/{organization_id}/production-processes/controlled-lists/{list_code}",
    response_model=ControlledListResponse,
    summary="Single production-process controlled list",
)
def get_production_process_controlled_list(
    organization_id: UUID,
    list_code: str,
    db: DbSession,
    user: CurrentUser,
) -> ControlledListResponse:
    return production_process_service.get_controlled_list_for_processes(
        db, user, organization_id, list_code
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/summary",
    response_model=ProductionProcessSummary,
    summary="Production-process binding summary / readiness rollup",
)
def get_production_process_binding_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductionProcessSummary:
    return production_process_service.get_production_process_binding_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes",
    response_model=Page[ProductionProcessResponse],
    summary="List Conventional production processes",
)
def list_production_processes(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[ProductionProcessResponse]:
    return production_process_service.list_production_processes(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes",
    response_model=ProductionProcessResponse,
    status_code=201,
    summary="Create Conventional production process draft",
)
def create_production_process(
    organization_id: UUID,
    binding_id: UUID,
    payload: ProductionProcessCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductionProcessResponse:
    return production_process_service.create_production_process(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}",
    response_model=ProductionProcessResponse,
    summary="Production process detail",
)
def get_production_process(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductionProcessResponse:
    return production_process_service.get_production_process(
        db, user, organization_id, binding_id, process_id
    )


@router.patch(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}",
    response_model=ProductionProcessResponse,
    summary="Patch production process draft (unbalanced drafts allowed)",
)
def update_production_process_draft(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    payload: ProductionProcessUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductionProcessResponse:
    return production_process_service.update_production_process_draft(
        db,
        user,
        organization_id,
        binding_id,
        process_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/readiness",
    response_model=ProductionProcessReadiness,
    summary="Server-authoritative production-process readiness",
)
def get_production_process_readiness(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductionProcessReadiness:
    return production_process_service.get_production_process_readiness(
        db, user, organization_id, binding_id, process_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/archive",
    response_model=ProductionProcessResponse,
    summary="Archive production process",
)
def archive_production_process(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    payload: ProductionProcessVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductionProcessResponse:
    return production_process_service.archive_production_process(
        db,
        user,
        organization_id,
        binding_id,
        process_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/product-uses",
    response_model=ProductUseResponse,
    status_code=201,
    summary="Add typed use-in-other-CBAM-product distribution row",
)
def create_production_process_product_use(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    payload: ProductUseCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductUseResponse:
    return production_process_service.create_product_use(
        db,
        user,
        organization_id,
        binding_id,
        process_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.patch(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/product-uses/{use_id}",
    response_model=ProductUseResponse,
    summary="Update product-use distribution row",
)
def update_production_process_product_use(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    use_id: UUID,
    payload: ProductUseUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductUseResponse:
    return production_process_service.update_product_use(
        db,
        user,
        organization_id,
        binding_id,
        process_id,
        use_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.delete(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/product-uses/{use_id}",
    status_code=204,
    summary="Delete product-use distribution row",
)
def delete_production_process_product_use(
    organization_id: UUID,
    binding_id: UUID,
    process_id: UUID,
    use_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> Response:
    production_process_service.delete_product_use(
        db,
        user,
        organization_id,
        binding_id,
        process_id,
        use_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    return Response(status_code=204)


@router.get(
    "/organizations/{organization_id}/purchased-precursors/metadata",
    response_model=PurchasedPrecursorMetadataResponse,
    summary="Purchased-precursor controlled lists, units and workbook metadata (Phase 10A)",
)
def get_purchased_precursor_metadata(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedPrecursorMetadataResponse:
    return purchased_precursor_service.get_purchased_precursor_metadata(db, user, organization_id)


@router.get(
    "/organizations/{organization_id}/purchased-precursors/default-values/search",
    response_model=Page[PrecursorDefaultValueResponse],
    summary="Search EU precursor default values (Implementing Regulation (EU) 2025/2621)",
)
def search_precursor_default_values(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    country: str | None = Query(None),
    cn: str | None = Query(None),
    route: str | None = Query(None),
    description: str | None = Query(None),
    q: str | None = Query(None),
    include_other_countries_group: bool = Query(True, alias="includeOtherCountriesGroup"),
) -> Page[PrecursorDefaultValueResponse]:
    return precursor_default_catalog_service.search_default_values(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        country=country,
        cn=cn,
        route=route,
        description=description,
        q=q,
        include_other_countries_group=include_other_countries_group,
    )


@router.post(
    "/organizations/{organization_id}/purchased-precursors/default-values/resolve",
    response_model=PrecursorDefaultResolution,
    summary="Resolve one EU precursor default value (RESOLVED / UNRESOLVED / AMBIGUOUS)",
)
def resolve_precursor_default_value(
    organization_id: UUID,
    payload: PrecursorDefaultResolveRequest,
    db: DbSession,
    user: CurrentUser,
) -> PrecursorDefaultResolution:
    return precursor_default_catalog_service.resolve_default_value_for_org(
        db, user, organization_id, payload
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/summary",
    response_model=PurchasedPrecursorSummary,
    summary="Purchased-precursor binding summary / readiness rollup",
)
def get_purchased_precursor_binding_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedPrecursorSummary:
    return purchased_precursor_service.get_purchased_precursor_binding_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors",
    response_model=Page[PurchasedPrecursorResponse],
    summary="List purchased precursors",
)
def list_purchased_precursors(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[PurchasedPrecursorResponse]:
    return purchased_precursor_service.list_purchased_precursors(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors",
    response_model=PurchasedPrecursorResponse,
    status_code=201,
    summary="Create purchased-precursor draft (SUPPLIER_DATA or EU_DEFAULT)",
)
def create_purchased_precursor(
    organization_id: UUID,
    binding_id: UUID,
    payload: PurchasedPrecursorCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PurchasedPrecursorResponse:
    return purchased_precursor_service.create_purchased_precursor(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}",
    response_model=PurchasedPrecursorResponse,
    summary="Purchased-precursor detail",
)
def get_purchased_precursor(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedPrecursorResponse:
    return purchased_precursor_service.get_purchased_precursor(
        db, user, organization_id, binding_id, precursor_id
    )


@router.patch(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}",
    response_model=PurchasedPrecursorResponse,
    summary="Patch purchased-precursor draft (re-resolves and re-snapshots EU defaults)",
)
def update_purchased_precursor_draft(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    payload: PurchasedPrecursorUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PurchasedPrecursorResponse:
    return purchased_precursor_service.update_purchased_precursor_draft(
        db,
        user,
        organization_id,
        binding_id,
        precursor_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/readiness",
    response_model=PurchasedPrecursorReadiness,
    summary="Server-authoritative purchased-precursor readiness",
)
def get_purchased_precursor_readiness(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedPrecursorReadiness:
    return purchased_precursor_service.get_purchased_precursor_readiness(
        db, user, organization_id, binding_id, precursor_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/archive",
    response_model=PurchasedPrecursorResponse,
    summary="Archive purchased precursor",
)
def archive_purchased_precursor(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    payload: PurchasedPrecursorVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PurchasedPrecursorResponse:
    return purchased_precursor_service.archive_purchased_precursor(
        db,
        user,
        organization_id,
        binding_id,
        precursor_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/product-uses",
    response_model=PrecursorProductUseResponse,
    status_code=201,
    summary="Distribute a purchased precursor to a CBAM product profile",
)
def create_purchased_precursor_product_use(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    payload: PrecursorProductUseCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PrecursorProductUseResponse:
    return purchased_precursor_service.create_precursor_product_use(
        db,
        user,
        organization_id,
        binding_id,
        precursor_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.patch(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/product-uses/{use_id}",
    response_model=PrecursorProductUseResponse,
    summary="Update purchased-precursor distribution row",
)
def update_purchased_precursor_product_use(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    use_id: UUID,
    payload: PrecursorProductUseUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PrecursorProductUseResponse:
    return purchased_precursor_service.update_precursor_product_use(
        db,
        user,
        organization_id,
        binding_id,
        precursor_id,
        use_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.delete(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/product-uses/{use_id}",
    status_code=204,
    summary="Delete purchased-precursor distribution row",
)
def delete_purchased_precursor_product_use(
    organization_id: UUID,
    binding_id: UUID,
    precursor_id: UUID,
    use_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> Response:
    purchased_precursor_service.delete_precursor_product_use(
        db,
        user,
        organization_id,
        binding_id,
        precursor_id,
        use_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    return Response(status_code=204)


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/readiness",
    response_model=ProductEmbeddedEmissionsReadiness,
    summary="Product embedded-emissions roll-up readiness (Phase 10C)",
)
def get_product_embedded_emissions_readiness(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductEmbeddedEmissionsReadiness:
    return product_embedded_emissions_service.get_product_embedded_emissions_readiness(
        db, user, organization_id, binding_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/executions",
    response_model=ProductEmbeddedEmissionsExecutionResponse,
    status_code=201,
    summary="Execute the product embedded-emissions roll-up (Phase 10C)",
    responses={
        200: {
            "description": "Exact idempotent replay",
            "model": ProductEmbeddedEmissionsExecutionResponse,
        },
        201: {
            "description": "First successful execution",
            "model": ProductEmbeddedEmissionsExecutionResponse,
        },
        409: {"description": "IDEMPOTENCY_KEY_REUSED or persistence conflict"},
    },
)
def execute_product_embedded_emissions(
    organization_id: UUID,
    binding_id: UUID,
    body: ProductEmbeddedEmissionsExecuteRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    response: Response,
) -> ProductEmbeddedEmissionsExecutionResponse:
    result = product_embedded_emissions_service.execute_product_embedded_emissions(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    response.status_code = 200 if result.idempotent_replay else 201
    return result


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/results",
    response_model=Page[ProductEmbeddedEmissionsResultSummary],
    summary="List product embedded-emissions results (newest first)",
)
def list_product_embedded_emissions_results(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[ProductEmbeddedEmissionsResultSummary]:
    return product_embedded_emissions_service.list_product_embedded_emissions_results(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/results/{result_id}",
    response_model=ProductEmbeddedEmissionsResultDetail,
    summary="Product embedded-emissions result detail (immutable snapshot)",
)
def get_product_embedded_emissions_result(
    organization_id: UUID,
    binding_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductEmbeddedEmissionsResultDetail:
    return product_embedded_emissions_service.get_product_embedded_emissions_result(
        db, user, organization_id, binding_id, result_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/summary",
    response_model=ProductEmbeddedEmissionsPeriodSummary,
    summary="Product embedded-emissions period summary (current pointer)",
)
def get_product_embedded_emissions_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductEmbeddedEmissionsPeriodSummary:
    return product_embedded_emissions_service.get_product_embedded_emissions_summary(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-records",
    response_model=Page[ProductionRecordResponse],
)
def list_production_records(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[ProductionRecordResponse]:
    return production_record_service.list_production_records(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-records",
    response_model=ProductionRecordResponse,
    status_code=201,
)
def create_production_record(
    organization_id: UUID,
    binding_id: UUID,
    payload: ProductionRecordCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductionRecordResponse:
    return production_record_service.create_production_record(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/production-records/{record_id}",
    response_model=ProductionRecordResponse,
)
def get_production_record(
    organization_id: UUID,
    record_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProductionRecordResponse:
    return production_record_service.get_production_record(db, user, organization_id, record_id)


@router.patch(
    "/organizations/{organization_id}/production-records/{record_id}",
    response_model=ProductionRecordResponse,
)
def update_production_record(
    organization_id: UUID,
    record_id: UUID,
    payload: ProductionRecordUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductionRecordResponse:
    return production_record_service.update_production_record(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/production-records/{record_id}/archive",
    response_model=ProductionRecordResponse,
)
def archive_production_record(
    organization_id: UUID,
    record_id: UUID,
    payload: ProductionRecordVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ProductionRecordResponse:
    return production_record_service.archive_production_record(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/activity-records",
    response_model=Page[ActivityRecordResponse],
)
def list_activity_records(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    activity_type: str | None = Query(None, alias="activityType"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[ActivityRecordResponse]:
    return activity_record_service.list_activity_records(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        activity_type=activity_type,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/activity-records",
    response_model=ActivityRecordResponse,
    status_code=201,
)
def create_activity_record(
    organization_id: UUID,
    binding_id: UUID,
    payload: ActivityRecordCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ActivityRecordResponse:
    return activity_record_service.create_activity_record(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/activity-records/{record_id}",
    response_model=ActivityRecordResponse,
)
def get_activity_record(
    organization_id: UUID,
    record_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ActivityRecordResponse:
    return activity_record_service.get_activity_record(db, user, organization_id, record_id)


@router.patch(
    "/organizations/{organization_id}/activity-records/{record_id}",
    response_model=ActivityRecordResponse,
)
def update_activity_record(
    organization_id: UUID,
    record_id: UUID,
    payload: ActivityRecordUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ActivityRecordResponse:
    return activity_record_service.update_activity_record(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/activity-records/{record_id}/archive",
    response_model=ActivityRecordResponse,
)
def archive_activity_record(
    organization_id: UUID,
    record_id: UUID,
    payload: ActivityRecordVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ActivityRecordResponse:
    return activity_record_service.archive_activity_record(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-inputs",
    response_model=Page[PurchasedInputResponse],
)
def list_purchased_inputs(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[PurchasedInputResponse]:
    return purchased_input_service.list_purchased_inputs(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-inputs",
    response_model=PurchasedInputResponse,
    status_code=201,
)
def create_purchased_input(
    organization_id: UUID,
    binding_id: UUID,
    payload: PurchasedInputCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PurchasedInputResponse:
    return purchased_input_service.create_purchased_input(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/purchased-inputs/{record_id}",
    response_model=PurchasedInputResponse,
)
def get_purchased_input(
    organization_id: UUID,
    record_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PurchasedInputResponse:
    return purchased_input_service.get_purchased_input(db, user, organization_id, record_id)


@router.patch(
    "/organizations/{organization_id}/purchased-inputs/{record_id}",
    response_model=PurchasedInputResponse,
)
def update_purchased_input(
    organization_id: UUID,
    record_id: UUID,
    payload: PurchasedInputUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PurchasedInputResponse:
    return purchased_input_service.update_purchased_input(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/purchased-inputs/{record_id}/archive",
    response_model=PurchasedInputResponse,
)
def archive_purchased_input(
    organization_id: UUID,
    record_id: UUID,
    payload: PurchasedInputVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PurchasedInputResponse:
    return purchased_input_service.archive_purchased_input(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/allocation-rules",
    response_model=Page[AllocationRuleResponse],
)
def list_allocation_rules(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[AllocationRuleResponse]:
    return allocation_rule_service.list_allocation_rules(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/allocation-rules",
    response_model=AllocationRuleResponse,
    status_code=201,
)
def create_allocation_rule(
    organization_id: UUID,
    binding_id: UUID,
    payload: AllocationRuleCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationRuleResponse:
    return allocation_rule_service.create_allocation_rule(
        db,
        user,
        organization_id,
        binding_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/allocation-rules/{rule_id}",
    response_model=AllocationRuleResponse,
)
def get_allocation_rule(
    organization_id: UUID,
    rule_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> AllocationRuleResponse:
    return allocation_rule_service.get_allocation_rule(db, user, organization_id, rule_id)


@router.patch(
    "/organizations/{organization_id}/allocation-rules/{rule_id}",
    response_model=AllocationRuleResponse,
)
def update_allocation_rule(
    organization_id: UUID,
    rule_id: UUID,
    payload: AllocationRuleUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationRuleResponse:
    return allocation_rule_service.update_allocation_rule(
        db,
        user,
        organization_id,
        rule_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/allocation-rules/{rule_id}/activate",
    response_model=AllocationRuleResponse,
)
def activate_allocation_rule(
    organization_id: UUID,
    rule_id: UUID,
    payload: AllocationRuleVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationRuleResponse:
    return allocation_rule_service.activate_allocation_rule(
        db,
        user,
        organization_id,
        rule_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/allocation-rules/{rule_id}/archive",
    response_model=AllocationRuleResponse,
)
def archive_allocation_rule(
    organization_id: UUID,
    rule_id: UUID,
    payload: AllocationRuleVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationRuleResponse:
    return allocation_rule_service.archive_allocation_rule(
        db,
        user,
        organization_id,
        rule_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/allocation-rules/{rule_id}"
    "/allocate/activity-records/{activity_record_id}",
    response_model=AllocationResultResponse,
    status_code=201,
)
def allocate_activity_record(
    organization_id: UUID,
    rule_id: UUID,
    activity_record_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationResultResponse:
    return allocation_service.allocate_activity_record(
        db,
        user,
        organization_id,
        rule_id,
        activity_record_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/allocation-rules/{rule_id}"
    "/allocate/purchased-inputs/{input_record_id}",
    response_model=AllocationResultResponse,
    status_code=201,
)
def allocate_purchased_input(
    organization_id: UUID,
    rule_id: UUID,
    input_record_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationResultResponse:
    return allocation_service.allocate_purchased_input(
        db,
        user,
        organization_id,
        rule_id,
        input_record_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/allocation-results/{result_id}/recalculate",
    response_model=AllocationResultResponse,
    status_code=201,
)
def recalculate_allocation_result(
    organization_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> AllocationResultResponse:
    return allocation_service.recalculate_allocation_result(
        db,
        user,
        organization_id,
        result_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/allocation-results",
    response_model=Page[AllocationResultResponse],
)
def list_allocation_results(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_only: bool = Query(True, alias="currentOnly"),
) -> Page[AllocationResultResponse]:
    return allocation_service.list_allocation_results(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        current_only=current_only,
    )


@router.get(
    "/organizations/{organization_id}/allocation-results/{result_id}",
    response_model=AllocationResultResponse,
)
def get_allocation_result(
    organization_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> AllocationResultResponse:
    return allocation_service.get_allocation_result(db, user, organization_id, result_id)


@router.get(
    "/organizations/{organization_id}/reference-sources",
    response_model=Page[ReferenceSourceResponse],
)
def list_reference_sources(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[ReferenceSourceResponse]:
    return reference_source_service.list_reference_sources(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/reference-sources",
    response_model=ReferenceSourceResponse,
    status_code=201,
)
def create_reference_source(
    organization_id: UUID,
    payload: ReferenceSourceCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ReferenceSourceResponse:
    return reference_source_service.create_reference_source(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reference-sources/{source_id}",
    response_model=ReferenceSourceResponse,
)
def get_reference_source(
    organization_id: UUID,
    source_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ReferenceSourceResponse:
    return reference_source_service.get_reference_source(db, user, organization_id, source_id)


@router.patch(
    "/organizations/{organization_id}/reference-sources/{source_id}",
    response_model=ReferenceSourceResponse,
)
def update_reference_source(
    organization_id: UUID,
    source_id: UUID,
    payload: ReferenceSourceUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ReferenceSourceResponse:
    return reference_source_service.update_reference_source(
        db,
        user,
        organization_id,
        source_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reference-sources/{source_id}/archive",
    response_model=ReferenceSourceResponse,
)
def archive_reference_source(
    organization_id: UUID,
    source_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ReferenceSourceResponse:
    return reference_source_service.archive_reference_source(
        db,
        user,
        organization_id,
        source_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/factor-definitions",
    response_model=Page[FactorDefinitionResponse],
)
def list_factor_definitions(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[FactorDefinitionResponse]:
    return factor_catalog_service.list_factor_definitions(
        db, user, organization_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/factor-definitions/{definition_id}",
    response_model=FactorDefinitionResponse,
)
def get_factor_definition(
    organization_id: UUID,
    definition_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> FactorDefinitionResponse:
    return factor_catalog_service.get_factor_definition(db, user, organization_id, definition_id)


@router.get(
    "/organizations/{organization_id}/factor-definitions/{definition_id}/values",
    response_model=Page[FactorValueResponse],
)
def list_factor_values(
    organization_id: UUID,
    definition_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    include_archived: bool = Query(False, alias="includeArchived"),
) -> Page[FactorValueResponse]:
    return factor_catalog_service.list_factor_values(
        db,
        user,
        organization_id,
        definition_id,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
    )


@router.post(
    "/organizations/{organization_id}/factor-definitions/{definition_id}/values",
    response_model=FactorValueResponse,
    status_code=201,
)
def create_factor_value(
    organization_id: UUID,
    definition_id: UUID,
    payload: FactorValueCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorValueResponse:
    return factor_catalog_service.create_factor_value(
        db,
        user,
        organization_id,
        definition_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/factor-values/{value_id}",
    response_model=FactorValueResponse,
)
def get_factor_value(
    organization_id: UUID,
    value_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> FactorValueResponse:
    return factor_catalog_service.get_factor_value(db, user, organization_id, value_id)


@router.patch(
    "/organizations/{organization_id}/factor-values/{value_id}",
    response_model=FactorValueResponse,
)
def update_factor_value(
    organization_id: UUID,
    value_id: UUID,
    payload: FactorValueUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorValueResponse:
    return factor_catalog_service.update_factor_value(
        db,
        user,
        organization_id,
        value_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/factor-values/{value_id}/activate",
    response_model=FactorValueResponse,
)
def activate_factor_value(
    organization_id: UUID,
    value_id: UUID,
    payload: FactorValueVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorValueResponse:
    return factor_catalog_service.activate_factor_value(
        db,
        user,
        organization_id,
        value_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/factor-values/{value_id}/archive",
    response_model=FactorValueResponse,
)
def archive_factor_value(
    organization_id: UUID,
    value_id: UUID,
    payload: FactorValueVersionRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorValueResponse:
    return factor_catalog_service.archive_factor_value(
        db,
        user,
        organization_id,
        value_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/activity-records/{record_id}/properties",
    response_model=ActivityPropertyResponse,
    status_code=201,
)
def add_activity_property(
    organization_id: UUID,
    record_id: UUID,
    payload: ActivityPropertyInput,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> ActivityPropertyResponse:
    return activity_record_service.add_activity_property(
        db,
        user,
        organization_id,
        record_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/activity-records/{record_id}"
    "/factor-resolutions/{factor_definition_code}/resolve",
    response_model=FactorResolutionResponse,
    status_code=201,
)
def resolve_activity_factor(
    organization_id: UUID,
    record_id: UUID,
    factor_definition_code: str,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorResolutionResponse:
    return factor_resolution_service.resolve_for_activity_record(
        db,
        user,
        organization_id,
        record_id,
        factor_definition_code,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/purchased-inputs/{record_id}"
    "/factor-resolutions/{factor_definition_code}/resolve",
    response_model=FactorResolutionResponse,
    status_code=201,
)
def resolve_purchased_factor(
    organization_id: UUID,
    record_id: UUID,
    factor_definition_code: str,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorResolutionResponse:
    return factor_resolution_service.resolve_for_purchased_input(
        db,
        user,
        organization_id,
        record_id,
        factor_definition_code,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/allocation-results/{result_id}"
    "/factor-resolutions/{factor_definition_code}/resolve",
    response_model=FactorResolutionResponse,
    status_code=201,
)
def resolve_allocation_factor(
    organization_id: UUID,
    result_id: UUID,
    factor_definition_code: str,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FactorResolutionResponse:
    return factor_resolution_service.resolve_for_allocation_result(
        db,
        user,
        organization_id,
        result_id,
        factor_definition_code,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/factor-resolutions/{resolution_id}",
    response_model=FactorResolutionResponse,
)
def get_factor_resolution(
    organization_id: UUID,
    resolution_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> FactorResolutionResponse:
    return factor_resolution_service.get_factor_resolution(db, user, organization_id, resolution_id)


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/factor-resolutions",
    response_model=Page[FactorResolutionResponse],
)
def list_factor_resolutions(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_only: bool = Query(True, alias="currentOnly"),
) -> Page[FactorResolutionResponse]:
    return factor_resolution_service.list_factor_resolutions(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
        current_only=current_only,
    )


@router.get(
    "/organizations/{organization_id}/calculation-definitions",
    response_model=Page[CalculationDefinitionResponse],
)
def list_calculation_definitions(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[CalculationDefinitionResponse]:
    return calculation_service.list_calculation_definitions(
        db, user, organization_id, page=page, page_size=page_size
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/calculation-runs",
    response_model=CalculationRunResponse,
    status_code=201,
)
def create_calculation_run(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    _body: CalculationRunCreate | None = None,
) -> CalculationRunResponse:
    return calculation_service.create_calculation_run(
        db,
        user,
        organization_id,
        binding_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/calculation-runs",
    response_model=Page[CalculationRunResponse],
)
def list_calculation_runs(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[CalculationRunResponse]:
    return calculation_service.list_calculation_runs(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/calculation-runs/{run_id}",
    response_model=CalculationRunResponse,
)
def get_calculation_run(
    organization_id: UUID,
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> CalculationRunResponse:
    return calculation_service.get_calculation_run(db, user, organization_id, run_id)


@router.post(
    "/organizations/{organization_id}/calculation-runs/{run_id}/execute",
    response_model=CalculationRunResponse,
)
def execute_calculation_run(
    organization_id: UUID,
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    body: CalculationRunExecuteRequest | None = None,
) -> CalculationRunResponse:
    return calculation_service.execute_calculation_run(
        db,
        user,
        organization_id,
        run_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/calculation-runs/{run_id}/results",
    response_model=Page[CalculationResultResponse],
)
def list_calculation_results(
    organization_id: UUID,
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_only: bool = Query(True, alias="currentOnly"),
) -> Page[CalculationResultResponse]:
    return calculation_service.list_calculation_results(
        db,
        user,
        organization_id,
        run_id,
        page=page,
        page_size=page_size,
        current_only=current_only,
    )


@router.get(
    "/organizations/{organization_id}/calculation-results/{result_id}",
    response_model=CalculationResultResponse,
)
def get_calculation_result(
    organization_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> CalculationResultResponse:
    return calculation_service.get_calculation_result(db, user, organization_id, result_id)


@router.post(
    "/organizations/{organization_id}/calculation-results/{result_id}/recalculate",
    response_model=CalculationResultResponse,
)
def recalculate_calculation_result(
    organization_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> CalculationResultResponse:
    return calculation_service.recalculate_result(
        db,
        user,
        organization_id,
        result_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/export-templates",
    response_model=Page[ExportTemplateResponse],
)
def list_export_templates(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[ExportTemplateResponse]:
    return export_template_service.list_export_templates(
        db, user, organization_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/export-templates/{template_id}",
    response_model=ExportTemplateResponse,
)
def get_export_template(
    organization_id: UUID,
    template_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ExportTemplateResponse:
    return export_template_service.get_export_template(db, user, organization_id, template_id)


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/export-readiness",
    response_model=ExportReadinessResponse,
)
def get_export_readiness(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    template_id: UUID | None = Query(None, alias="templateId"),
    calculation_run_id: UUID | None = Query(None, alias="calculationRunId"),
) -> ExportReadinessResponse:
    return export_readiness_service.assess_export_readiness(
        db,
        user,
        organization_id,
        binding_id,
        template_id=template_id,
        calculation_run_id=calculation_run_id,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/summary",
    response_model=PeriodSummaryResponse,
)
def get_period_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> PeriodSummaryResponse:
    return period_summary_service.get_period_summary(db, user, organization_id, binding_id)


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/exports",
    response_model=ExportRunResponse,
    status_code=201,
)
def create_export_run(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    body: ExportCreateRequest | None = None,
) -> ExportRunResponse:
    return workbook_export_service.create_export_run(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/exports",
    response_model=Page[ExportRunResponse],
)
def list_export_runs(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[ExportRunResponse]:
    return workbook_export_service.list_export_runs(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/exports/{export_run_id}",
    response_model=ExportRunResponse,
)
def get_export_run(
    organization_id: UUID,
    export_run_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ExportRunResponse:
    return workbook_export_service.get_export_run(db, user, organization_id, export_run_id)


@router.get(
    "/organizations/{organization_id}/exports/{export_run_id}/artifacts",
    response_model=list[ExportArtifactResponse],
)
def list_export_artifacts(
    organization_id: UUID,
    export_run_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[ExportArtifactResponse]:
    return workbook_export_service.list_export_artifacts(db, user, organization_id, export_run_id)


@router.get(
    "/organizations/{organization_id}/export-artifacts/{artifact_id}/download",
)
def download_export_artifact(
    organization_id: UUID,
    artifact_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FileResponse:
    artifact, path = workbook_export_service.download_export_artifact(
        db,
        user,
        organization_id,
        artifact_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    return FileResponse(
        path=path,
        media_type=artifact.mime_type,
        filename=artifact.file_name,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/official-see-export/readiness",
    response_model=OfficialSeeExportReadiness,
    summary="Official CBAM SEE export readiness (Phase 12A)",
)
def get_official_see_export_readiness(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> OfficialSeeExportReadiness:
    return official_see_export_service.get_official_see_export_readiness(
        db, user, organization_id, binding_id
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/official-see-export/executions",
    response_model=OfficialSeeExportRunResponse,
    status_code=201,
    summary="Generate Official CBAM SEE workbook (Phase 12A)",
    responses={
        200: {
            "description": "Exact idempotent replay",
            "model": OfficialSeeExportRunResponse,
        },
        201: {
            "description": "First successful generation",
            "model": OfficialSeeExportRunResponse,
        },
        409: {"description": "IDEMPOTENCY_KEY_REUSED or conflict"},
    },
)
def create_official_see_export_run(
    organization_id: UUID,
    binding_id: UUID,
    body: OfficialSeeExportCreateRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    response: Response,
) -> OfficialSeeExportRunResponse:
    result = official_see_export_service.create_official_see_export_run(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    response.status_code = 200 if result.idempotent_replay else 201
    return result


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/official-see-export/runs",
    response_model=Page[OfficialSeeExportRunResponse],
    summary="List Official SEE export runs",
)
def list_official_see_export_runs(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[OfficialSeeExportRunResponse]:
    return official_see_export_service.list_official_see_export_runs(
        db, user, organization_id, binding_id, page=page, page_size=page_size
    )


@router.get(
    "/organizations/{organization_id}/official-see-export/runs/{run_id}",
    response_model=OfficialSeeExportRunResponse,
    summary="Get Official SEE export run",
)
def get_official_see_export_run(
    organization_id: UUID,
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> OfficialSeeExportRunResponse:
    return official_see_export_service.get_official_see_export_run(
        db, user, organization_id, run_id
    )


@router.get(
    "/organizations/{organization_id}/official-see-export/runs/{run_id}/artifacts",
    response_model=list[OfficialSeeExportArtifactResponse],
    summary="List Official SEE export artifacts",
)
def list_official_see_export_artifacts(
    organization_id: UUID,
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[OfficialSeeExportArtifactResponse]:
    return official_see_export_service.list_official_see_export_artifacts(
        db, user, organization_id, run_id
    )


@router.get(
    "/organizations/{organization_id}/official-see-export/artifacts/{artifact_id}/download",
    summary="Download Official SEE export artifact (parity PASSED only)",
)
def download_official_see_export_artifact(
    organization_id: UUID,
    artifact_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FileResponse:
    artifact, path = official_see_export_service.download_official_see_export_artifact(
        db,
        user,
        organization_id,
        artifact_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    return FileResponse(
        path=path,
        media_type=artifact.mime_type,
        filename=artifact.file_name,
    )


@router.get(
    "/organizations/{organization_id}/stationary-combustion/fuels",
    response_model=list[StationaryCombustionFuelResponse],
    summary="List active stationary-combustion fuels",
)
def list_stationary_combustion_fuels(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> list[StationaryCombustionFuelResponse]:
    return stationary_combustion_api_service.list_active_stationary_combustion_fuels(
        db, user, organization_id
    )


@router.get(
    "/organizations/{organization_id}/stationary-combustion/fuels/{fuel_code}/parameters",
    response_model=StationaryCombustionParametersResponse,
    summary="Resolve published stationary-combustion parameters",
)
def get_stationary_combustion_fuel_parameters(
    organization_id: UUID,
    fuel_code: str,
    db: DbSession,
    user: CurrentUser,
    reference_date: date = Query(..., alias="referenceDate"),
    dataset_version: str | None = Query(None, alias="datasetVersion"),
) -> StationaryCombustionParametersResponse:
    return stationary_combustion_api_service.get_stationary_combustion_parameters(
        db,
        user,
        organization_id,
        fuel_code,
        reference_date=reference_date,
        dataset_version=dataset_version,
    )


@router.post(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
    response_model=StationaryCombustionExecutionApiResponse,
    # 201 = first successful create; 200 = exact idempotent replay (same clientRequestId + material request).
    status_code=201,
    summary="Execute stationary-combustion calculation for one activity",
    responses={
        200: {
            "description": (
                "Exact idempotent replay: same organization, binding, clientRequestId, "
                "and material execution identity. Returns the existing run/result with "
                "idempotentReplay=true. Does not create a new run or result."
            ),
            "model": StationaryCombustionExecutionApiResponse,
        },
        201: {
            "description": (
                "First successful execution for this clientRequestId. Creates run and result; "
                "idempotentReplay=false."
            ),
            "model": StationaryCombustionExecutionApiResponse,
        },
        409: {
            "description": (
                "IDEMPOTENCY_KEY_REUSED when the same clientRequestId is reused with a "
                "different material execution request."
            ),
        },
    },
)
def execute_stationary_combustion(
    organization_id: UUID,
    binding_id: UUID,
    body: StationaryCombustionExecutionApiRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    response: Response,
) -> StationaryCombustionExecutionApiResponse:
    result = stationary_combustion_api_service.execute_stationary_combustion_api(
        db,
        user,
        organization_id,
        binding_id,
        body,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    response.status_code = 200 if result.idempotent_replay else 201
    return result


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/summary",
    response_model=StationaryCombustionPeriodSummaryResponse,
    summary="Stationary-combustion reporting-period summary (current results only)",
)
def get_stationary_combustion_summary(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> StationaryCombustionPeriodSummaryResponse:
    return stationary_combustion_api_service.get_stationary_combustion_summary_for_binding(
        db, user, organization_id, binding_id
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/activity-coverage",
    response_model=Page[StationaryCombustionActivityCoverageItem],
    summary="Stationary-combustion activity coverage (current/missing/stale)",
)
def list_stationary_combustion_activity_coverage_route(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[StationaryCombustionActivityCoverageItem]:
    return (
        stationary_combustion_api_service.list_stationary_combustion_activity_coverage_for_binding(
            db,
            user,
            organization_id,
            binding_id,
            page=page,
            page_size=page_size,
        )
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
    response_model=Page[StationaryCombustionResultSummaryResponse],
    summary="List stationary-combustion results for a reporting-period binding",
)
def list_stationary_combustion_results(
    organization_id: UUID,
    binding_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[StationaryCombustionResultSummaryResponse]:
    return stationary_combustion_api_service.list_stationary_combustion_results(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/results/{result_id}",
    response_model=StationaryCombustionResultResponse,
    summary="Get immutable stationary-combustion result snapshot",
)
def get_stationary_combustion_result(
    organization_id: UUID,
    binding_id: UUID,
    result_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> StationaryCombustionResultResponse:
    return stationary_combustion_api_service.get_stationary_combustion_result_for_binding(
        db, user, organization_id, binding_id, result_id
    )
