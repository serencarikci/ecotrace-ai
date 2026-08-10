from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
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
    export_readiness_service,
    export_template_service,
    factor_catalog_service,
    factor_resolution_service,
    installation_service,
    period_binding_service,
    period_summary_service,
    product_profile_service,
    production_record_service,
    purchased_input_service,
    reference_source_service,
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
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingResponse,
    PeriodBindingUpdate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.period_summary_service import PeriodSummaryResponse
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileResponse,
    ProductProfileVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordCreate,
    ProductionRecordResponse,
    ProductionRecordUpdate,
    ProductionRecordVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_input_service import (
    PurchasedInputCreate,
    PurchasedInputResponse,
    PurchasedInputUpdate,
    PurchasedInputVersionRequest,
)
from ecotrace.modules.cbam.application.reference_source_service import (
    ReferenceSourceCreate,
    ReferenceSourceResponse,
    ReferenceSourceUpdate,
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
    return production_record_service.get_production_record(
        db, user, organization_id, record_id
    )


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
    return reference_source_service.get_reference_source(
        db, user, organization_id, source_id
    )


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
    return factor_catalog_service.get_factor_definition(
        db, user, organization_id, definition_id
    )


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
    return factor_resolution_service.get_factor_resolution(
        db, user, organization_id, resolution_id
    )


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
    return calculation_service.get_calculation_result(
        db, user, organization_id, result_id
    )


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
    return export_template_service.get_export_template(
        db, user, organization_id, template_id
    )


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
    return period_summary_service.get_period_summary(
        db, user, organization_id, binding_id
    )


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
    return workbook_export_service.get_export_run(
        db, user, organization_id, export_run_id
    )


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
    return workbook_export_service.list_export_artifacts(
        db, user, organization_id, export_run_id
    )


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
