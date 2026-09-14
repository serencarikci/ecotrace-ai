import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../../core/models/api.models';
import { AuthService } from '../../core/services/auth.service';
import { buildHttpParams } from '../../core/services/http-params.util';

export interface CbamModuleStatus {
  module: string;
  uiLabelTr: string;
  status: string;
  foundationAvailable: boolean;
  domainFunctionalityImplemented: boolean;
  complianceClaim: boolean;
  calculationImplemented: boolean;
  reportingImplemented: boolean;
  message: string;
  
  enforcedPermissions: string[];
}

export interface CbamInstallation {
  id: string;
  organizationId: string;
  facilityId: string;
  code: string;
  name: string;
  status: string;
  timezone: string;
  operatorIdentityRef: string | null;
  metadataJson: Record<string, unknown> | null;
  rowVersion: number;
}

export interface CbamInstallationCreate {
  facilityId: string;
  code: string;
  name: string;
  timezone?: string;
  operatorIdentityRef?: string | null;
}

export interface CbamInstallationUpdate {
  rowVersion: number;
  name?: string;
  timezone?: string;
  operatorIdentityRef?: string | null;
}

export interface CbamPeriodBinding {
  id: string;
  organizationId: string;
  reportingPeriodId: string;
  status: string;
  lockedAt: string | null;
  lockedByUserId: string | null;
  approvedAt: string | null;
  approvedCalculationRunId: string | null;
  revisionNumber: number;
  rowVersion: number;
}

export interface CbamPeriodBindingCreate {
  reportingPeriodId: string;
}

export interface CbamActivityType {
  code: string;
  displayName: string;
  activityGroup: string;
  allowedUnitFamily: string;
}

export interface CbamUnit {
  code: string;
  displayName: string;
  family: string;
}

export type CbamProfileLinkStatus = 'MISSING' | 'READY' | 'OUTDATED' | 'INVALID';

export interface CbamProductionRecord {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  installationProfileId: string;
  productProfileVersionId: string | null;
  productionDate: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  quantity: string;
  unit: string;
  notes: string | null;
  sourceType: string;
  status: string;
  rowVersion: number;
  /** Authoritative profile projection (Phase 6C). */
  productId?: string | null;
  productName?: string | null;
  profileVersion?: number | null;
  profileStatus?: string | null;
  cnNormalizedCode?: string | null;
  cnDisplayCode?: string | null;
  classificationReady?: boolean | null;
  profileLinkStatus: CbamProfileLinkStatus;
  profileLinkIssueCodes: string[];
}

export interface CbamProductionRecordCreate {
  installationProfileId: string;
  productProfileVersionId: string;
  productionDate?: string | null;
  quantity: string;
  unit: string;
  notes?: string | null;
  sourceType?: string;
}

export interface CbamProductionRecordUpdate {
  rowVersion: number;
  productProfileVersionId?: string | null;
  productionDate?: string | null;
  quantity?: string | null;
  unit?: string | null;
  notes?: string | null;
}

export interface CbamProductionProfileLinkSummary {
  eligibleRecordCount: number;
  missingProfileCount: number;
  outdatedProfileCount: number;
  invalidProfileCount: number;
  activeRecordCount: number;
  allocationProfileReady: boolean;
  blockingIssueCodes: string[];
}

export type CbamMonthlyBasisRowStatus = 'INCOMPLETE' | 'INVALID' | 'READY';
export type CbamMonthlyBasisCoverage = 'MISSING' | 'INCOMPLETE' | 'INVALID' | 'READY';
export type CbamMonthlyReconciliationStatus = 'EXACT_MATCH' | 'MISMATCH' | 'UNAVAILABLE';
export type CbamCombustionCompatStatus = 'READY' | 'BLOCKED';

export interface CbamMonthlyProductionBasis {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  monthStart: string;
  totalProductionQuantity: string | null;
  cbamQuantity: string | null;
  quantityUnit: string;
  normalizedTotalProductionTonnes: string | null;
  normalizedCbamQuantityTonnes: string | null;
  cbamShare: string | null;
  status: CbamMonthlyBasisRowStatus;
  issueCodes: string[];
  sourceType: string;
  notes: string | null;
  rowVersion: number;
}

export interface CbamMonthlyProductionBasisCreate {
  monthStart: string;
  totalProductionQuantity?: string | null;
  cbamQuantity?: string | null;
  quantityUnit?: string;
  sourceType?: string;
  notes?: string | null;
}

export interface CbamMonthlyProductionBasisUpdate {
  rowVersion: number;
  totalProductionQuantity?: string | null;
  cbamQuantity?: string | null;
  quantityUnit?: string | null;
  sourceType?: string | null;
  notes?: string | null;
}

export interface CbamMonthCoverageItem {
  monthStart: string;
  coverage: CbamMonthlyBasisCoverage;
  recordId: string | null;
  issueCodes: string[];
}

export interface CbamProductionReconciliationMonth {
  monthStart: string;
  explicitCbamQuantityTonnes: string | null;
  recordedCbamProductionTonnes: string | null;
  differenceTonnes: string | null;
  reconciliationStatus: CbamMonthlyReconciliationStatus;
}

export interface CbamCombustionCompatibilityItem {
  activityRecordId: string;
  currentResultId: string;
  activityDate: string | null;
  monthStart: string | null;
  status: CbamCombustionCompatStatus;
  issueCodes: string[];
}

export interface CbamMonthlyProductionBasisSummary {
  reportingPeriodBindingId: string;
  expectedMonthCount: number;
  completedMonthCount: number;
  incompleteMonthCount: number;
  invalidMonthCount: number;
  missingMonthCount: number;
  status: CbamMonthlyBasisRowStatus;
  allocationBasisReady: boolean;
  blockingIssueCodes: string[];
  monthCoverage: CbamMonthCoverageItem[];
  informationalTotalProductionTonnes: string | null;
  informationalTotalCbamQuantityTonnes: string | null;
  combustionCompatibilityStatus: CbamCombustionCompatStatus;
  combustionCompatibilityIssueCodes: string[];
  combustionItems: CbamCombustionCompatibilityItem[];
  productionReconciliation: CbamProductionReconciliationMonth[];
}

export interface CbamActivityRecord {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  installationProfileId: string;
  activityGroup: string;
  activityType: string;
  activityDate: string | null;
  quantity: string;
  unit: string;
  dataSourceType: string;
  sourceReference: string | null;
  notes: string | null;
  status: string;
  rowVersion: number;
}

export interface CbamActivityRecordCreate {
  installationProfileId: string;
  activityType: string;
  activityDate?: string | null;
  quantity: string;
  unit: string;
  dataSourceType: string;
  sourceReference?: string | null;
  measurementMethod?: string | null;
  supplierName?: string | null;
  certificateReference?: string | null;
  notes?: string | null;
}

export interface CbamPurchasedInput {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  installationProfileId: string;
  inputName: string;
  supplierName: string | null;
  quantity: string;
  unit: string;
  consumedQuantity: string | null;
  consumedUnit: string | null;
  embeddedEmissionValue: string | null;
  embeddedEmissionUnit: string | null;
  embeddedEmissionSourceType: string;
  notes: string | null;
  status: string;
  rowVersion: number;
}

export interface CbamPurchasedInputCreate {
  installationProfileId: string;
  inputName: string;
  supplierName?: string | null;
  quantity: string;
  unit: string;
  consumedQuantity?: string | null;
  consumedUnit?: string | null;
  embeddedEmissionValue?: string | null;
  embeddedEmissionUnit?: string | null;
  embeddedEmissionSourceType?: string;
  notes?: string | null;
}

export interface CbamAllocationRule {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  installationProfileId: string;
  productProfileVersionId: string | null;
  allocationMethod: string;
  name: string;
  description: string | null;
  allocationRatio: string | null;
  numeratorProductionRecordId: string | null;
  denominatorProductionRecordId: string | null;
  numeratorQuantity: string | null;
  denominatorQuantity: string | null;
  quantityUnit: string | null;
  rationale: string | null;
  sourceReference: string | null;
  status: string;
  rowVersion: number;
  archivedAt: string | null;
}

export interface CbamAllocationRuleCreate {
  installationProfileId: string;
  productProfileVersionId?: string | null;
  allocationMethod: string;
  name: string;
  description?: string | null;
  allocationRatio?: string | null;
  numeratorProductionRecordId?: string | null;
  denominatorProductionRecordId?: string | null;
  rationale?: string | null;
  sourceReference?: string | null;
}

export interface CbamAllocationResult {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  allocationRuleId: string;
  sourceType: string;
  sourceId: string;
  sourceQuantity: string;
  sourceUnit: string;
  allocationRatio: string;
  allocatedQuantity: string;
  allocatedUnit: string;
  allocationMethod: string;
  calculationVersion: string;
  isCurrent: boolean;
  supersededAt: string | null;
  createdAt: string;
}

@Injectable({ providedIn: 'root' })
export class CbamApiService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private orgBase(organizationId?: string): string {
    const id = organizationId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/${id}`;
  }

  getModuleStatus(organizationId?: string): Observable<CbamModuleStatus> {
    return this.http.get<CbamModuleStatus>(`${this.orgBase(organizationId)}/module-status`);
  }

  listInstallations(params: {
    page?: number;
    pageSize?: number;
    status?: string;
    search?: string;
  } = {}): Observable<Page<CbamInstallation>> {
    return this.http.get<Page<CbamInstallation>>(`${this.orgBase()}/installations`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        status: params.status,
        search: params.search,
      }),
    });
  }

  getInstallation(installationId: string): Observable<CbamInstallation> {
    return this.http.get<CbamInstallation>(`${this.orgBase()}/installations/${installationId}`);
  }

  createInstallation(payload: CbamInstallationCreate): Observable<CbamInstallation> {
    return this.http.post<CbamInstallation>(`${this.orgBase()}/installations`, payload);
  }

  updateInstallation(
    installationId: string,
    payload: CbamInstallationUpdate,
  ): Observable<CbamInstallation> {
    return this.http.patch<CbamInstallation>(
      `${this.orgBase()}/installations/${installationId}`,
      payload,
    );
  }

  activateInstallation(installationId: string, rowVersion: number): Observable<CbamInstallation> {
    return this.http.post<CbamInstallation>(
      `${this.orgBase()}/installations/${installationId}/activate`,
      { rowVersion },
    );
  }

  archiveInstallation(installationId: string, rowVersion: number): Observable<CbamInstallation> {
    return this.http.post<CbamInstallation>(
      `${this.orgBase()}/installations/${installationId}/archive`,
      { rowVersion },
    );
  }

  listPeriodBindings(params: {
    page?: number;
    pageSize?: number;
    status?: string;
  } = {}): Observable<Page<CbamPeriodBinding>> {
    return this.http.get<Page<CbamPeriodBinding>>(`${this.orgBase()}/reporting-period-bindings`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        status: params.status,
      }),
    });
  }

  getPeriodBinding(bindingId: string): Observable<CbamPeriodBinding> {
    return this.http.get<CbamPeriodBinding>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}`,
    );
  }

  createPeriodBinding(payload: CbamPeriodBindingCreate): Observable<CbamPeriodBinding> {
    return this.http.post<CbamPeriodBinding>(
      `${this.orgBase()}/reporting-period-bindings`,
      payload,
    );
  }

  openDataCollection(bindingId: string, rowVersion: number): Observable<CbamPeriodBinding> {
    return this.http.post<CbamPeriodBinding>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/open-data-collection`,
      { rowVersion },
    );
  }

  archivePeriodBinding(bindingId: string, rowVersion: number): Observable<CbamPeriodBinding> {
    return this.http.post<CbamPeriodBinding>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/archive`,
      { rowVersion },
    );
  }

  listActivityTypes(): Observable<CbamActivityType[]> {
    return this.http.get<CbamActivityType[]>(`${this.orgBase()}/activity-types`);
  }

  listUnits(): Observable<CbamUnit[]> {
    return this.http.get<CbamUnit[]>(`${this.orgBase()}/units`);
  }

  listProductionRecords(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamProductionRecord>> {
    return this.http.get<Page<CbamProductionRecord>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-records`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  createProductionRecord(
    bindingId: string,
    payload: CbamProductionRecordCreate,
  ): Observable<CbamProductionRecord> {
    return this.http.post<CbamProductionRecord>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-records`,
      payload,
    );
  }

  updateProductionRecord(
    recordId: string,
    payload: CbamProductionRecordUpdate,
  ): Observable<CbamProductionRecord> {
    return this.http.patch<CbamProductionRecord>(
      `${this.orgBase()}/production-records/${recordId}`,
      payload,
    );
  }

  getProductionProfileLinkSummary(
    bindingId: string,
  ): Observable<CbamProductionProfileLinkSummary> {
    return this.http.get<CbamProductionProfileLinkSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-profile-link-summary`,
    );
  }

  listMonthlyProductionBasis(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamMonthlyProductionBasis>> {
    return this.http.get<Page<CbamMonthlyProductionBasis>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/monthly-production-basis`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 100,
        }),
      },
    );
  }

  getMonthlyProductionBasisSummary(
    bindingId: string,
  ): Observable<CbamMonthlyProductionBasisSummary> {
    return this.http.get<CbamMonthlyProductionBasisSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/monthly-production-basis-summary`,
    );
  }

  createMonthlyProductionBasis(
    bindingId: string,
    payload: CbamMonthlyProductionBasisCreate,
  ): Observable<CbamMonthlyProductionBasis> {
    return this.http.post<CbamMonthlyProductionBasis>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/monthly-production-basis`,
      payload,
    );
  }

  updateMonthlyProductionBasis(
    recordId: string,
    payload: CbamMonthlyProductionBasisUpdate,
  ): Observable<CbamMonthlyProductionBasis> {
    return this.http.patch<CbamMonthlyProductionBasis>(
      `${this.orgBase()}/monthly-production-basis/${recordId}`,
      payload,
    );
  }

  deleteMonthlyProductionBasis(recordId: string): Observable<void> {
    return this.http.delete<void>(`${this.orgBase()}/monthly-production-basis/${recordId}`);
  }

  getDirectEmissionsAllocationReadiness(
    bindingId: string,
  ): Observable<CbamDirectEmissionsAllocationReadiness> {
    return this.http.get<CbamDirectEmissionsAllocationReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/direct-emissions-allocation/readiness`,
    );
  }

  executeDirectEmissionsAllocation(
    bindingId: string,
    payload: CbamDirectEmissionsAllocationExecuteRequest,
  ): Observable<CbamDirectEmissionsAllocationExecutionResponse> {
    return this.http.post<CbamDirectEmissionsAllocationExecutionResponse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/direct-emissions-allocation/executions`,
      payload,
    );
  }

  listDirectEmissionsAllocationResults(
    bindingId: string,
    params?: { page?: number; pageSize?: number },
  ): Observable<Page<CbamDirectEmissionsAllocationResultSummary>> {
    return this.http.get<Page<CbamDirectEmissionsAllocationResultSummary>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/direct-emissions-allocation/results`,
      { params: buildHttpParams(params ?? {}) },
    );
  }

  getDirectEmissionsAllocationResult(
    bindingId: string,
    resultId: string,
  ): Observable<CbamDirectEmissionsAllocationResultDetail> {
    return this.http.get<CbamDirectEmissionsAllocationResultDetail>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/direct-emissions-allocation/results/${resultId}`,
    );
  }

  getDirectEmissionsAllocationSummary(
    bindingId: string,
  ): Observable<CbamDirectEmissionsAllocationPeriodSummary> {
    return this.http.get<CbamDirectEmissionsAllocationPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/direct-emissions-allocation/summary`,
    );
  }

  getIndirectEmissionsAllocationReadiness(
    bindingId: string,
  ): Observable<CbamIndirectEmissionsAllocationReadiness> {
    return this.http.get<CbamIndirectEmissionsAllocationReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/indirect-emissions-allocation/readiness`,
    );
  }

  executeIndirectEmissionsAllocation(
    bindingId: string,
    payload: CbamIndirectEmissionsAllocationExecuteRequest,
  ): Observable<CbamIndirectEmissionsAllocationExecutionResponse> {
    return this.http.post<CbamIndirectEmissionsAllocationExecutionResponse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/indirect-emissions-allocation/executions`,
      payload,
    );
  }

  listIndirectEmissionsAllocationResults(
    bindingId: string,
    params?: { page?: number; pageSize?: number },
  ): Observable<Page<CbamIndirectEmissionsAllocationResultSummary>> {
    return this.http.get<Page<CbamIndirectEmissionsAllocationResultSummary>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/indirect-emissions-allocation/results`,
      { params: buildHttpParams(params ?? {}) },
    );
  }

  getIndirectEmissionsAllocationResult(
    bindingId: string,
    resultId: string,
  ): Observable<CbamIndirectEmissionsAllocationResultDetail> {
    return this.http.get<CbamIndirectEmissionsAllocationResultDetail>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/indirect-emissions-allocation/results/${resultId}`,
    );
  }

  getIndirectEmissionsAllocationSummary(
    bindingId: string,
  ): Observable<CbamIndirectEmissionsAllocationPeriodSummary> {
    return this.http.get<CbamIndirectEmissionsAllocationPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/indirect-emissions-allocation/summary`,
    );
  }

  getProductEmbeddedEmissionsReadiness(
    bindingId: string,
  ): Observable<CbamProductEmbeddedEmissionsReadiness> {
    return this.http.get<CbamProductEmbeddedEmissionsReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/product-embedded-emissions/readiness`,
    );
  }

  executeProductEmbeddedEmissions(
    bindingId: string,
    payload: CbamProductEmbeddedEmissionsExecuteRequest,
  ): Observable<CbamProductEmbeddedEmissionsExecutionResponse> {
    return this.http.post<CbamProductEmbeddedEmissionsExecutionResponse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/product-embedded-emissions/executions`,
      payload,
    );
  }

  listProductEmbeddedEmissionsResults(
    bindingId: string,
    params?: { page?: number; pageSize?: number },
  ): Observable<Page<CbamProductEmbeddedEmissionsResultSummary>> {
    return this.http.get<Page<CbamProductEmbeddedEmissionsResultSummary>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/product-embedded-emissions/results`,
      { params: buildHttpParams(params ?? {}) },
    );
  }

  getProductEmbeddedEmissionsResult(
    bindingId: string,
    resultId: string,
  ): Observable<CbamProductEmbeddedEmissionsResultDetail> {
    return this.http.get<CbamProductEmbeddedEmissionsResultDetail>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/product-embedded-emissions/results/${resultId}`,
    );
  }

  getProductEmbeddedEmissionsSummary(
    bindingId: string,
  ): Observable<CbamProductEmbeddedEmissionsPeriodSummary> {
    return this.http.get<CbamProductEmbeddedEmissionsPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/product-embedded-emissions/summary`,
    );
  }

  getProductionProcessMetadata(): Observable<CbamProductionProcessMetadata> {
    return this.http.get<CbamProductionProcessMetadata>(
      `${this.orgBase()}/production-processes/metadata`,
    );
  }

  listProductionProcessControlledLists(): Observable<CbamProductionProcessControlledList[]> {
    return this.http.get<CbamProductionProcessControlledList[]>(
      `${this.orgBase()}/production-processes/controlled-lists`,
    );
  }

  getProductionProcessControlledList(
    listCode: string,
  ): Observable<CbamProductionProcessControlledList> {
    return this.http.get<CbamProductionProcessControlledList>(
      `${this.orgBase()}/production-processes/controlled-lists/${encodeURIComponent(listCode)}`,
    );
  }

  getProductionProcessBindingSummary(
    bindingId: string,
  ): Observable<CbamProductionProcessBindingSummary> {
    return this.http.get<CbamProductionProcessBindingSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/summary`,
    );
  }

  listProductionProcesses(
    bindingId: string,
    params: { page?: number; pageSize?: number; includeArchived?: boolean } = {},
  ): Observable<Page<CbamProductionProcess>> {
    return this.http.get<Page<CbamProductionProcess>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
          includeArchived: params.includeArchived ?? false,
        }),
      },
    );
  }

  getProductionProcess(
    bindingId: string,
    processId: string,
  ): Observable<CbamProductionProcess> {
    return this.http.get<CbamProductionProcess>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}`,
    );
  }

  getProductionProcessReadiness(
    bindingId: string,
    processId: string,
  ): Observable<CbamProductionProcessReadiness> {
    return this.http.get<CbamProductionProcessReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}/readiness`,
    );
  }

  createProductionProcess(
    bindingId: string,
    payload: CbamProductionProcessCreate,
  ): Observable<CbamProductionProcess> {
    return this.http.post<CbamProductionProcess>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes`,
      payload,
    );
  }

  updateProductionProcessDraft(
    bindingId: string,
    processId: string,
    payload: CbamProductionProcessUpdate,
  ): Observable<CbamProductionProcess> {
    return this.http.patch<CbamProductionProcess>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}`,
      payload,
    );
  }

  archiveProductionProcess(
    bindingId: string,
    processId: string,
    payload: CbamProductionProcessVersionRequest,
  ): Observable<CbamProductionProcess> {
    return this.http.post<CbamProductionProcess>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}/archive`,
      payload,
    );
  }

  createProductionProcessProductUse(
    bindingId: string,
    processId: string,
    payload: CbamProductionProcessProductUseCreate,
  ): Observable<CbamProductionProcessProductUse> {
    return this.http.post<CbamProductionProcessProductUse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}/product-uses`,
      payload,
    );
  }

  updateProductionProcessProductUse(
    bindingId: string,
    processId: string,
    useId: string,
    payload: CbamProductionProcessProductUseUpdate,
  ): Observable<CbamProductionProcessProductUse> {
    return this.http.patch<CbamProductionProcessProductUse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}/product-uses/${useId}`,
      payload,
    );
  }

  deleteProductionProcessProductUse(
    bindingId: string,
    processId: string,
    useId: string,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/production-processes/${processId}/product-uses/${useId}`,
    );
  }

  listProductProfilesForBinding(
    bindingId: string,
    params: { page?: number; pageSize?: number; status?: string | null } = {},
  ): Observable<Page<CbamProductProfile>> {
    return this.http.get<Page<CbamProductProfile>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/product-profiles`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 100,
          status: params.status,
        }),
      },
    );
  }

  archiveProductionRecord(recordId: string, rowVersion: number): Observable<CbamProductionRecord> {
    return this.http.post<CbamProductionRecord>(
      `${this.orgBase()}/production-records/${recordId}/archive`,
      { rowVersion },
    );
  }

  listActivityRecords(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamActivityRecord>> {
    return this.http.get<Page<CbamActivityRecord>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/activity-records`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  createActivityRecord(
    bindingId: string,
    payload: CbamActivityRecordCreate,
  ): Observable<CbamActivityRecord> {
    return this.http.post<CbamActivityRecord>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/activity-records`,
      payload,
    );
  }

  archiveActivityRecord(recordId: string, rowVersion: number): Observable<CbamActivityRecord> {
    return this.http.post<CbamActivityRecord>(
      `${this.orgBase()}/activity-records/${recordId}/archive`,
      { rowVersion },
    );
  }

  listPurchasedInputs(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamPurchasedInput>> {
    return this.http.get<Page<CbamPurchasedInput>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-inputs`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  createPurchasedInput(
    bindingId: string,
    payload: CbamPurchasedInputCreate,
  ): Observable<CbamPurchasedInput> {
    return this.http.post<CbamPurchasedInput>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-inputs`,
      payload,
    );
  }

  archivePurchasedInput(recordId: string, rowVersion: number): Observable<CbamPurchasedInput> {
    return this.http.post<CbamPurchasedInput>(
      `${this.orgBase()}/purchased-inputs/${recordId}/archive`,
      { rowVersion },
    );
  }

  listAllocationRules(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamAllocationRule>> {
    return this.http.get<Page<CbamAllocationRule>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/allocation-rules`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  createAllocationRule(
    bindingId: string,
    payload: CbamAllocationRuleCreate,
  ): Observable<CbamAllocationRule> {
    return this.http.post<CbamAllocationRule>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/allocation-rules`,
      payload,
    );
  }

  activateAllocationRule(ruleId: string, rowVersion: number): Observable<CbamAllocationRule> {
    return this.http.post<CbamAllocationRule>(
      `${this.orgBase()}/allocation-rules/${ruleId}/activate`,
      { rowVersion },
    );
  }

  archiveAllocationRule(ruleId: string, rowVersion: number): Observable<CbamAllocationRule> {
    return this.http.post<CbamAllocationRule>(
      `${this.orgBase()}/allocation-rules/${ruleId}/archive`,
      { rowVersion },
    );
  }

  listAllocationResults(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamAllocationResult>> {
    return this.http.get<Page<CbamAllocationResult>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/allocation-results`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  allocateActivityRecord(
    ruleId: string,
    activityRecordId: string,
  ): Observable<CbamAllocationResult> {
    return this.http.post<CbamAllocationResult>(
      `${this.orgBase()}/allocation-rules/${ruleId}/allocate/activity-records/${activityRecordId}`,
      {},
    );
  }

  allocatePurchasedInput(
    ruleId: string,
    inputRecordId: string,
  ): Observable<CbamAllocationResult> {
    return this.http.post<CbamAllocationResult>(
      `${this.orgBase()}/allocation-rules/${ruleId}/allocate/purchased-inputs/${inputRecordId}`,
      {},
    );
  }

  recalculateAllocationResult(resultId: string): Observable<CbamAllocationResult> {
    return this.http.post<CbamAllocationResult>(
      `${this.orgBase()}/allocation-results/${resultId}/recalculate`,
      {},
    );
  }

  listReferenceSources(
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamReferenceSource>> {
    return this.http.get<Page<CbamReferenceSource>>(`${this.orgBase()}/reference-sources`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 50,
      }),
    });
  }

  listFactorDefinitions(
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamFactorDefinition>> {
    return this.http.get<Page<CbamFactorDefinition>>(`${this.orgBase()}/factor-definitions`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 50,
      }),
    });
  }

  listFactorValues(
    definitionId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamFactorValue>> {
    return this.http.get<Page<CbamFactorValue>>(
      `${this.orgBase()}/factor-definitions/${definitionId}/values`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 50,
        }),
      },
    );
  }

  listFactorResolutions(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamFactorResolution>> {
    return this.http.get<Page<CbamFactorResolution>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/factor-resolutions`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 50,
        }),
      },
    );
  }

  addActivityProperty(
    recordId: string,
    payload: {
      propertyCode: string;
      numericValue: string;
      unit: string;
      sourceType?: string;
      sourceReference?: string | null;
    },
  ): Observable<CbamActivityProperty> {
    return this.http.post<CbamActivityProperty>(
      `${this.orgBase()}/activity-records/${recordId}/properties`,
      payload,
    );
  }

  resolveActivityFactor(
    recordId: string,
    factorDefinitionCode: string,
  ): Observable<CbamFactorResolution> {
    return this.http.post<CbamFactorResolution>(
      `${this.orgBase()}/activity-records/${recordId}/factor-resolutions/${factorDefinitionCode}/resolve`,
      {},
    );
  }

  resolvePurchasedFactor(
    recordId: string,
    factorDefinitionCode: string,
  ): Observable<CbamFactorResolution> {
    return this.http.post<CbamFactorResolution>(
      `${this.orgBase()}/purchased-inputs/${recordId}/factor-resolutions/${factorDefinitionCode}/resolve`,
      {},
    );
  }

  resolveAllocationFactor(
    resultId: string,
    factorDefinitionCode: string,
  ): Observable<CbamFactorResolution> {
    return this.http.post<CbamFactorResolution>(
      `${this.orgBase()}/allocation-results/${resultId}/factor-resolutions/${factorDefinitionCode}/resolve`,
      {},
    );
  }

  listCalculationRuns(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamCalculationRun>> {
    return this.http.get<Page<CbamCalculationRun>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/calculation-runs`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  createCalculationRun(bindingId: string): Observable<CbamCalculationRun> {
    return this.http.post<CbamCalculationRun>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/calculation-runs`,
      {},
    );
  }

  executeCalculationRun(
    runId: string,
    payload: { allowUnallocatedActivity?: boolean } = {},
  ): Observable<CbamCalculationRun> {
    return this.http.post<CbamCalculationRun>(
      `${this.orgBase()}/calculation-runs/${runId}/execute`,
      payload,
    );
  }

  listCalculationResults(
    runId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamCalculationResult>> {
    return this.http.get<Page<CbamCalculationResult>>(
      `${this.orgBase()}/calculation-runs/${runId}/results`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 50,
        }),
      },
    );
  }

  recalculateCalculationResult(resultId: string): Observable<CbamCalculationResult> {
    return this.http.post<CbamCalculationResult>(
      `${this.orgBase()}/calculation-results/${resultId}/recalculate`,
      {},
    );
  }

  listExportTemplates(
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamExportTemplate>> {
    return this.http.get<Page<CbamExportTemplate>>(`${this.orgBase()}/export-templates`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
      }),
    });
  }

  getExportReadiness(
    bindingId: string,
    params: { templateId?: string; calculationRunId?: string } = {},
  ): Observable<CbamExportReadiness> {
    return this.http.get<CbamExportReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/export-readiness`,
      {
        params: buildHttpParams({
          templateId: params.templateId,
          calculationRunId: params.calculationRunId,
        }),
      },
    );
  }

  getPeriodSummary(bindingId: string): Observable<CbamPeriodSummary> {
    return this.http.get<CbamPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/summary`,
    );
  }

  createExportRun(
    bindingId: string,
    payload: { exportTemplateId?: string; calculationRunId?: string } = {},
  ): Observable<CbamExportRun> {
    return this.http.post<CbamExportRun>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/exports`,
      payload,
    );
  }

  listExportRuns(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamExportRun>> {
    return this.http.get<Page<CbamExportRun>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/exports`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  listExportArtifacts(exportRunId: string): Observable<CbamExportArtifact[]> {
    return this.http.get<CbamExportArtifact[]>(
      `${this.orgBase()}/exports/${exportRunId}/artifacts`,
    );
  }

  downloadExportArtifact(artifactId: string): Observable<Blob> {
    return this.http.get(`${this.orgBase()}/export-artifacts/${artifactId}/download`, {
      responseType: 'blob',
    });
  }

  getOfficialSeeExportReadiness(bindingId: string): Observable<CbamOfficialSeeExportReadiness> {
    return this.http.get<CbamOfficialSeeExportReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/official-see-export/readiness`,
    );
  }

  createOfficialSeeExportRun(
    bindingId: string,
    payload: { clientRequestId: string },
  ): Observable<CbamOfficialSeeExportRun> {
    return this.http.post<CbamOfficialSeeExportRun>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/official-see-export/executions`,
      payload,
    );
  }

  listOfficialSeeExportRuns(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamOfficialSeeExportRun>> {
    return this.http.get<Page<CbamOfficialSeeExportRun>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/official-see-export/runs`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  getOfficialSeeExportRun(runId: string): Observable<CbamOfficialSeeExportRun> {
    return this.http.get<CbamOfficialSeeExportRun>(
      `${this.orgBase()}/official-see-export/runs/${runId}`,
    );
  }

  listOfficialSeeExportArtifacts(runId: string): Observable<CbamOfficialSeeExportArtifact[]> {
    return this.http.get<CbamOfficialSeeExportArtifact[]>(
      `${this.orgBase()}/official-see-export/runs/${runId}/artifacts`,
    );
  }

  downloadOfficialSeeExportArtifact(artifactId: string): Observable<Blob> {
    return this.http.get(
      `${this.orgBase()}/official-see-export/artifacts/${artifactId}/download`,
      { responseType: 'blob' },
    );
  }

  listStationaryCombustionFuels(): Observable<CbamStationaryCombustionFuel[]> {
    return this.http.get<CbamStationaryCombustionFuel[]>(
      `${this.orgBase()}/stationary-combustion/fuels`,
    );
  }

  resolveStationaryCombustionParameters(
    fuelCode: string,
    params: { referenceDate: string; datasetVersion?: string | null },
  ): Observable<CbamStationaryCombustionParameters> {
    return this.http.get<CbamStationaryCombustionParameters>(
      `${this.orgBase()}/stationary-combustion/fuels/${encodeURIComponent(fuelCode)}/parameters`,
      {
        params: buildHttpParams({
          referenceDate: params.referenceDate,
          datasetVersion: params.datasetVersion ?? undefined,
        }),
      },
    );
  }

  executeStationaryCombustion(
    bindingId: string,
    payload: CbamStationaryCombustionExecutionRequest,
  ): Observable<CbamStationaryCombustionExecutionResponse> {
    return this.http.post<CbamStationaryCombustionExecutionResponse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/stationary-combustion/executions`,
      payload,
    );
  }

  listStationaryCombustionResults(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamStationaryCombustionResultSummary>> {
    return this.http.get<Page<CbamStationaryCombustionResultSummary>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/stationary-combustion/results`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  getStationaryCombustionResult(
    bindingId: string,
    resultId: string,
  ): Observable<CbamStationaryCombustionResultDetail> {
    return this.http.get<CbamStationaryCombustionResultDetail>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/stationary-combustion/results/${resultId}`,
    );
  }

  getStationaryCombustionSummary(
    bindingId: string,
  ): Observable<CbamStationaryCombustionPeriodSummary> {
    return this.http.get<CbamStationaryCombustionPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/stationary-combustion/summary`,
    );
  }

  listStationaryCombustionActivityCoverage(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamStationaryCombustionActivityCoverageItem>> {
    return this.http.get<Page<CbamStationaryCombustionActivityCoverageItem>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/stationary-combustion/activity-coverage`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  getPurchasedElectricityDefaultFactor(
    bindingId: string,
    params: { referenceDate?: string | null } = {},
  ): Observable<CbamPurchasedElectricityFactorResolution> {
    return this.http.get<CbamPurchasedElectricityFactorResolution>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-electricity/factors/default`,
      {
        params: buildHttpParams({
          referenceDate: params.referenceDate ?? undefined,
        }),
      },
    );
  }

  getPurchasedElectricityReadiness(
    bindingId: string,
  ): Observable<CbamPurchasedElectricityPeriodSummary> {
    return this.http.get<CbamPurchasedElectricityPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-electricity/readiness`,
    );
  }

  getPurchasedElectricitySummary(
    bindingId: string,
  ): Observable<CbamPurchasedElectricityPeriodSummary> {
    return this.http.get<CbamPurchasedElectricityPeriodSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-electricity/summary`,
    );
  }

  executePurchasedElectricity(
    bindingId: string,
    payload: CbamPurchasedElectricityExecuteRequest,
  ): Observable<CbamPurchasedElectricityExecutionResponse> {
    return this.http.post<CbamPurchasedElectricityExecutionResponse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-electricity/executions`,
      payload,
    );
  }

  listPurchasedElectricityResults(
    bindingId: string,
    params: { page?: number; pageSize?: number } = {},
  ): Observable<Page<CbamPurchasedElectricityResultSummary>> {
    return this.http.get<Page<CbamPurchasedElectricityResultSummary>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-electricity/results`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
        }),
      },
    );
  }

  getPurchasedElectricityResult(
    bindingId: string,
    resultId: string,
  ): Observable<CbamPurchasedElectricityResultDetail> {
    return this.http.get<CbamPurchasedElectricityResultDetail>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-electricity/results/${resultId}`,
    );
  }

  listCnCodes(
    params: {
      page?: number;
      pageSize?: number;
      q?: string | null;
      sector?: string | null;
    } = {},
  ): Observable<Page<CbamCnCode>> {
    return this.http.get<Page<CbamCnCode>>(`${this.orgBase()}/cn-codes`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        sector: params.sector,
      }),
    });
  }

  getCnCode(cnCodeId: string): Observable<CbamCnCode> {
    return this.http.get<CbamCnCode>(`${this.orgBase()}/cn-codes/${cnCodeId}`);
  }

  listCnControlledListValues(listCode: string): Observable<CbamCnControlledListValue[]> {
    return this.http.get<CbamCnControlledListValue[]>(
      `${this.orgBase()}/cn-controlled-lists/${encodeURIComponent(listCode)}`,
    );
  }

  listProductProfiles(
    params: {
      page?: number;
      pageSize?: number;
      productId?: string | null;
      status?: string | null;
    } = {},
  ): Observable<Page<CbamProductProfile>> {
    return this.http.get<Page<CbamProductProfile>>(`${this.orgBase()}/product-profile-versions`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        productId: params.productId,
        status: params.status,
      }),
    });
  }

  getProductProfile(profileId: string): Observable<CbamProductProfile> {
    return this.http.get<CbamProductProfile>(
      `${this.orgBase()}/product-profile-versions/${profileId}`,
    );
  }

  createProductProfile(payload: CbamProductProfileCreate): Observable<CbamProductProfile> {
    return this.http.post<CbamProductProfile>(
      `${this.orgBase()}/product-profile-versions`,
      payload,
    );
  }

  updateProductProfileDraft(
    profileId: string,
    payload: CbamProductProfileUpdate,
  ): Observable<CbamProductProfile> {
    return this.http.patch<CbamProductProfile>(
      `${this.orgBase()}/product-profile-versions/${profileId}`,
      payload,
    );
  }

  publishProductProfile(
    profileId: string,
    payload: CbamProductProfileVersionRequest,
  ): Observable<CbamProductProfile> {
    return this.http.post<CbamProductProfile>(
      `${this.orgBase()}/product-profile-versions/${profileId}/publish`,
      payload,
    );
  }

  archiveProductProfile(
    profileId: string,
    payload: CbamProductProfileVersionRequest,
  ): Observable<CbamProductProfile> {
    return this.http.post<CbamProductProfile>(
      `${this.orgBase()}/product-profile-versions/${profileId}/archive`,
      payload,
    );
  }

  getPurchasedPrecursorMetadata(): Observable<CbamPurchasedPrecursorMetadata> {
    return this.http.get<CbamPurchasedPrecursorMetadata>(
      `${this.orgBase()}/purchased-precursors/metadata`,
    );
  }

  searchPrecursorDefaultValues(
    params: {
      page?: number;
      pageSize?: number;
      country?: string | null;
      cn?: string | null;
      route?: string | null;
      description?: string | null;
      q?: string | null;
      includeOtherCountriesGroup?: boolean;
    } = {},
  ): Observable<Page<CbamPrecursorDefaultValue>> {
    return this.http.get<Page<CbamPrecursorDefaultValue>>(
      `${this.orgBase()}/purchased-precursors/default-values/search`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
          country: params.country,
          cn: params.cn,
          route: params.route,
          description: params.description,
          q: params.q,
          includeOtherCountriesGroup: params.includeOtherCountriesGroup ?? false,
        }),
      },
    );
  }

  resolvePrecursorDefaultValue(
    payload: CbamPrecursorDefaultResolveRequest,
  ): Observable<CbamPrecursorDefaultResolution> {
    return this.http.post<CbamPrecursorDefaultResolution>(
      `${this.orgBase()}/purchased-precursors/default-values/resolve`,
      payload,
    );
  }

  getPurchasedPrecursorBindingSummary(
    bindingId: string,
  ): Observable<CbamPurchasedPrecursorBindingSummary> {
    return this.http.get<CbamPurchasedPrecursorBindingSummary>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/summary`,
    );
  }

  listPurchasedPrecursors(
    bindingId: string,
    params: { page?: number; pageSize?: number; includeArchived?: boolean } = {},
  ): Observable<Page<CbamPurchasedPrecursor>> {
    return this.http.get<Page<CbamPurchasedPrecursor>>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors`,
      {
        params: buildHttpParams({
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 20,
          includeArchived: params.includeArchived ?? false,
        }),
      },
    );
  }

  getPurchasedPrecursor(
    bindingId: string,
    precursorId: string,
  ): Observable<CbamPurchasedPrecursor> {
    return this.http.get<CbamPurchasedPrecursor>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}`,
    );
  }

  getPurchasedPrecursorReadiness(
    bindingId: string,
    precursorId: string,
  ): Observable<CbamPurchasedPrecursorReadiness> {
    return this.http.get<CbamPurchasedPrecursorReadiness>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}/readiness`,
    );
  }

  createPurchasedPrecursor(
    bindingId: string,
    payload: CbamPurchasedPrecursorCreate,
  ): Observable<CbamPurchasedPrecursor> {
    return this.http.post<CbamPurchasedPrecursor>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors`,
      payload,
    );
  }

  updatePurchasedPrecursorDraft(
    bindingId: string,
    precursorId: string,
    payload: CbamPurchasedPrecursorUpdate,
  ): Observable<CbamPurchasedPrecursor> {
    return this.http.patch<CbamPurchasedPrecursor>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}`,
      payload,
    );
  }

  archivePurchasedPrecursor(
    bindingId: string,
    precursorId: string,
    payload: CbamPurchasedPrecursorVersionRequest,
  ): Observable<CbamPurchasedPrecursor> {
    return this.http.post<CbamPurchasedPrecursor>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}/archive`,
      payload,
    );
  }

  createPrecursorProductUse(
    bindingId: string,
    precursorId: string,
    payload: CbamPrecursorProductUseCreate,
  ): Observable<CbamPrecursorProductUse> {
    return this.http.post<CbamPrecursorProductUse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}/product-uses`,
      payload,
    );
  }

  updatePrecursorProductUse(
    bindingId: string,
    precursorId: string,
    useId: string,
    payload: CbamPrecursorProductUseUpdate,
  ): Observable<CbamPrecursorProductUse> {
    return this.http.patch<CbamPrecursorProductUse>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}/product-uses/${useId}`,
      payload,
    );
  }

  deletePrecursorProductUse(
    bindingId: string,
    precursorId: string,
    useId: string,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.orgBase()}/reporting-period-bindings/${bindingId}/purchased-precursors/${precursorId}/product-uses/${useId}`,
    );
  }
}

export interface CbamCalculationRun {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  status: string;
  calculationVersion: string;
  startedAt: string | null;
  completedAt: string | null;
  errorSummary: string | null;
  calculatedCount: number;
  blockedCount: number;
  invalidCount: number;
  primaryFactorCount: number;
  defaultFactorCount: number;
  sameUnitTotal: string | null;
  sameUnitTotalUnit: string | null;
}

export interface CbamCalculationResult {
  id: string;
  organizationId: string;
  calculationRunId: string;
  calculationDefinitionId: string;
  sourceType: string;
  sourceId: string;
  allocationResultId: string | null;
  factorResolutionId: string;
  sourceQuantity: string | null;
  sourceUnit: string | null;
  factorValue: string | null;
  factorUnit: string | null;
  resultValue: string | null;
  resultUnit: string | null;
  calculationType: string;
  formulaVersion: string;
  status: string;
  errorCode: string | null;
  errorMessage: string | null;
  inputFingerprint: string;
  isCurrent: boolean;
  supersededAt: string | null;
  factorResolutionStatus: string | null;
}

export interface CbamReferenceSource {
  id: string;
  organizationId: string | null;
  code: string;
  name: string;
  sourceType: string;
  publisher: string | null;
  versionLabel: string | null;
  publicationYear: number | null;
  referenceUrl: string | null;
  description: string | null;
  status: string;
}

export interface CbamFactorDefinition {
  id: string;
  code: string;
  name: string;
  factorCategory: string;
  activityType: string | null;
  propertyCode: string | null;
  inputUnitFamily: string | null;
  outputUnit: string | null;
  description: string | null;
  status: string;
}

export interface CbamFactorValue {
  id: string;
  organizationId: string | null;
  factorDefinitionId: string;
  referenceSourceId: string;
  activityType: string | null;
  numericValue: string;
  unit: string;
  validFrom: string | null;
  validUntil: string | null;
  geographyCode: string | null;
  supplierName: string | null;
  facilitySpecific: boolean;
  dataSourceType: string;
  sourceReference: string | null;
  notes: string | null;
  status: string;
  rowVersion: number;
}

export interface CbamFactorResolution {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  sourceType: string;
  sourceId: string;
  factorDefinitionId: string;
  resolutionStatus: string;
  selectedActivityPropertyId: string | null;
  selectedFactorValueId: string | null;
  selectedValue: string | null;
  selectedUnit: string | null;
  sourcePrecedence: string | null;
  resolutionReason: string;
  resolverVersion: string;
  resolvedAt: string;
  isCurrent: boolean;
  supersededAt: string | null;
}

export interface CbamActivityProperty {
  id: string;
  propertyCode: string;
  numericValue: string;
  unit: string;
  sourceType: string;
  sourceReference: string | null;
}

export interface CbamExportTemplate {
  id: string;
  organizationId: string | null;
  code: string;
  name: string;
  templateType: string;
  version: string;
  mappingVersion: string;
  storageUri: string;
  checksum: string;
  status: string;
  description: string | null;
  activatedAt: string | null;
  archivedAt: string | null;
}

export interface CbamExportReadinessCheck {
  code: string;
  label: string;
  status: string;
  message: string;
}

export interface CbamExportReadiness {
  status: string;
  checks: CbamExportReadinessCheck[];
  blockingIssues: string[];
  warnings: string[];
  officialMappingBlocked: boolean;
  suggestedTemplateId: string | null;
  calculationRunId: string | null;
}

export interface CbamPeriodSummary {
  title: string;
  organizationId: string;
  organizationName: string;
  reportingPeriodBindingId: string;
  reportingPeriodCode: string;
  readinessStatus: string;
  metrics: Record<string, unknown>;
  warnings: string[];
  officialMappingBlocked: boolean;
  calculationRunId: string | null;
  installations: Array<{ id: string; code: string; name: string }>;
  disclaimer: string;
}

export interface CbamExportRun {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  exportTemplateId: string;
  calculationRunId: string | null;
  status: string;
  templateVersion: string;
  mappingVersion: string;
  mappingChecksum: string;
  templateChecksum: string;
  inputChecksum: string | null;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
  warningSummary: string | null;
  applicationVersion: string | null;
}

export interface CbamOfficialSeeExportReadiness {
  ready: boolean;
  blockingIssueCodes: string[];
  warnings: string[];
  mappingVersion: string;
  templateVersion: string;
  templateSha256: string;
  capacity: {
    installations: number;
    goods: number;
    processes: number;
    precursors: number;
    fuelActivities: number;
  };
  sofficeAvailable: boolean;
  snapshotIds: Record<string, string | null>;
}

export interface CbamOfficialSeeExportRun {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  clientRequestId: string;
  generationStatus: string;
  validationStatus: string;
  formulaParityStatus: string;
  mappingVersion: string;
  templateFilename: string;
  templateVersion: string;
  templateSha256: string;
  peeResultId: string | null;
  deaResultId: string | null;
  ieaResultId: string | null;
  sourceFingerprint: string | null;
  outputSha256: string | null;
  outputSizeBytes: number | null;
  failureDiagnostics: Record<string, unknown> | null;
  generatedByUserId: string | null;
  generatedAt: string | null;
  createdAt: string;
  idempotentReplay: boolean;
}

export interface CbamOfficialSeeExportArtifact {
  id: string;
  organizationId: string;
  exportRunId: string;
  artifactType: string;
  fileName: string;
  mimeType: string;
  fileSizeBytes: number;
  sha256: string;
  createdAt: string;
}

export interface CbamExportArtifact {
  id: string;
  organizationId: string;
  exportRunId: string;
  artifactType: string;
  fileName: string;
  storageUri: string;
  mimeType: string;
  fileSizeBytes: number;
  sha256: string;
  createdAt: string;
}

export interface CbamStationaryCombustionFuel {
  code: string;
  name: string;
  inputBasis: string;
  defaultActivityUnit: string;
  densityRequired: boolean;
  status: string;
}

export interface CbamStationaryCombustionSource {
  referenceSourceId: string;
  sourceDocument: string;
  sourceTable: string;
}

export interface CbamStationaryCombustionParameters {
  fuelCode: string;
  fuelName: string;
  inputBasis: string;
  defaultActivityUnit: string;
  densityRequired: boolean;
  referenceDensity: string | null;
  referenceDensityUnit: string | null;
  netCalorificValue: string;
  netCalorificValueUnit: string;
  fossilCo2EmissionFactor: string;
  fossilCo2EmissionFactorUnit: string;
  oxidationFactor: string;
  datasetCode: string;
  datasetVersion: string;
  validFrom: string;
  validUntil: string | null;
  ncvSource: CbamStationaryCombustionSource;
  co2Source: CbamStationaryCombustionSource;
  oxidationSource: CbamStationaryCombustionSource;
  resolutionStatus: string;
  parameterSetId: string;
}

export interface CbamStationaryCombustionExecutionRequest {
  clientRequestId: string;
  activityRecordId: string;
  fuelCode: string;
  calculationReferenceDate?: string | null;
  densityValue?: string | null;
  densityUnit?: string | null;
  datasetVersion?: string | null;
}

export interface CbamStationaryCombustionExecutionResponse {
  runId: string;
  resultId: string;
  status: string;
  calculationType: string;
  calculationVersion: string;
  activityRecordId: string;
  fuelCode: string;
  referenceDate: string;
  resultValue: string;
  resultUnit: string;
  clientRequestId: string;
  idempotentReplay: boolean;
  createdAt: string;
}

export interface CbamStationaryCombustionResultSummary {
  resultId: string;
  runId: string;
  activityRecordId: string;
  fuelCode: string;
  activityQuantity: string;
  activityUnit: string;
  energyContentTj: string;
  fossilCo2Tonnes: string;
  resultValue: string;
  resultUnit: string;
  datasetVersion: string;
  clientRequestId: string | null;
  createdAt: string;
  isCurrent: boolean;
  isStale: boolean;
}

export interface CbamStationaryCombustionResultDetail {
  id: string;
  organizationId: string;
  calculationRunId: string;
  calculationDefinitionId: string;
  reportingPeriodBindingId: string;
  activityRecordId: string;
  fuelId: string;
  parameterSetId: string;
  calculationType: string;
  formulaVersion: string;
  fuelCode: string;
  fuelName: string;
  inputBasis: string;
  activityQuantity: string;
  activityUnit: string;
  densityValue: string | null;
  densityUnit: string | null;
  clientRequestId: string | null;
  requestFingerprint: string | null;
  calculationReferenceDate: string | null;
  netCalorificValue: string;
  netCalorificValueUnit: string;
  fossilCo2EmissionFactor: string;
  fossilCo2EmissionFactorUnit: string;
  oxidationFactor: string;
  datasetCode: string;
  datasetVersion: string;
  validFrom: string;
  validUntil: string | null;
  ncvReferenceSourceId: string;
  ncvSourceDocument: string;
  ncvSourceTable: string;
  co2ReferenceSourceId: string;
  co2SourceDocument: string;
  co2SourceTable: string;
  oxidationReferenceSourceId: string;
  oxidationSourceDocument: string;
  oxidationSourceTable: string;
  fuelMassKg: string;
  fuelMassGg: string;
  energyContentTj: string;
  fossilCo2Kg: string;
  fossilCo2Tonnes: string;
  resultValue: string;
  resultUnit: string;
  createdByUserId: string | null;
  createdAt: string;
  isCurrent: boolean;
  isStale: boolean;
}

export interface CbamStationaryCombustionFuelTotal {
  fuelCode: string;
  fuelName: string;
  activityCount: number;
  totalFuelMassKg: string;
  totalEnergyContentTj: string;
  totalFossilCo2Tonnes: string;
  finalResultValue: string;
  resultUnit: string;
}

export interface CbamStationaryCombustionPeriodSummary {
  organizationId: string;
  reportingPeriodBindingId: string;
  periodStart: string;
  periodEnd: string;
  periodType: string | null;
  eligibleActivityCount: number;
  currentResultCount: number;
  validCurrentResultCount: number;
  missingResultCount: number;
  staleResultCount: number;
  excludedResultCount: number;
  isComplete: boolean;
  readinessStatus: string;
  blockingIssues: string[];
  totalFuelMassKg: string;
  totalFuelMassGg: string;
  totalEnergyContentTj: string;
  totalFossilCo2Kg: string;
  totalFossilCo2Tonnes: string;
  finalResultValue: string;
  finalResultUnit: string;
  totalsByFuel: CbamStationaryCombustionFuelTotal[];
}

export type CbamStationaryCombustionCoverageStatus = 'MISSING' | 'CURRENT' | 'STALE' | string;

export interface CbamStationaryCombustionActivityCoverageItem {
  activityRecordId: string;
  activityDate: string | null;
  effectiveReferenceDate: string | null;
  activityType: string;
  fuelCode: string;
  fuelName: string;
  quantity: string;
  unit: string;
  coverageStatus: CbamStationaryCombustionCoverageStatus;
  currentResultId: string | null;
  currentRunId: string | null;
  currentResultCreatedAt: string | null;
  currentResultValue: string | null;
  currentResultUnit: string | null;
  staleReasonCodes: string[];
  blockingIssueCodes: string[];
}

/** Phase 6A+ authoritative product-field applicability (all keys always present). */
export interface CbamFieldApplicability {
  reducingAgent: boolean;
  steelMillIdentificationNumber: boolean;
  percentMn: boolean;
  percentCr: boolean;
  percentNi: boolean;
  percentOtherAlloys: boolean;
  percentOtherMaterials: boolean;
}

export interface CbamCnCode {
  id: string;
  datasetId: string;
  cnKey: string;
  normalizedCode: string;
  displayCode: string;
  descriptionEn: string;
  cbamSector: string;
  numberingLabel: string | null;
  sourceSheet: string;
  sourceRow: number;
  status: string;
  datasetCode: string;
  datasetVersion: string;
  contentChecksum: string;
  fieldApplicability: CbamFieldApplicability;
}

export interface CbamCnControlledListValue {
  listCode: string;
  valueCode: string;
  valueLabel: string;
  sortOrder: number;
}

export interface CbamProductProfileIssue {
  code: string;
  message: string;
}

export interface CbamProductProfile {
  id: string;
  organizationId: string;
  productId: string;
  version: number;
  status: string;
  validFrom: string | null;
  validTo: string | null;
  classificationReady: boolean;
  productName: string | null;
  cnCodeId: string | null;
  cnNormalizedCode: string | null;
  cnDisplayCode: string | null;
  cnDescription: string | null;
  cnSector: string | null;
  cnDatasetCode: string | null;
  cnDatasetVersion: string | null;
  fieldApplicability: CbamFieldApplicability;
  reducingAgent: string | null;
  steelMillIdentificationNumber: string | null;
  percentMn: string | null;
  percentCr: string | null;
  percentNi: string | null;
  percentOtherAlloys: string | null;
  percentOtherMaterials: string | null;
  missingRequirements: CbamProductProfileIssue[];
  validationIssues: CbamProductProfileIssue[];
  rowVersion: number;
}

export interface CbamProductProfileCreate {
  productId: string;
  productName?: string | null;
  cnCode?: string | null;
  reducingAgent?: string | null;
  steelMillIdentificationNumber?: string | null;
  percentMn?: string | null;
  percentCr?: string | null;
  percentNi?: string | null;
  percentOtherAlloys?: string | null;
  percentOtherMaterials?: string | null;
  validFrom?: string | null;
  validTo?: string | null;
}

export interface CbamProductProfileUpdate {
  rowVersion: number;
  productName?: string | null;
  cnCode?: string | null;
  reducingAgent?: string | null;
  steelMillIdentificationNumber?: string | null;
  percentMn?: string | null;
  percentCr?: string | null;
  percentNi?: string | null;
  percentOtherAlloys?: string | null;
  percentOtherMaterials?: string | null;
  validFrom?: string | null;
  validTo?: string | null;
}

export interface CbamProductProfileVersionRequest {
  rowVersion: number;
}

export type CbamPurchasedElectricityFactorSourceMode = 'PLATFORM_DEFAULT' | 'MANUAL';

export interface CbamPurchasedElectricityManualFactor {
  value: string;
  unit: string;
  sourceName: string;
  sourceDocument: string;
  datasetVersion: string;
  referenceDescription: string;
  effectiveDate?: string | null;
}

export interface CbamPurchasedElectricityExecuteRequest {
  clientRequestId: string;
  activityRecordId: string;
  factorSourceMode: CbamPurchasedElectricityFactorSourceMode;
  calculationReferenceDate?: string | null;
  manualFactor?: CbamPurchasedElectricityManualFactor | null;
  exportedElectricityQuantity?: string | null;
  exportedElectricityUnit?: string | null;
  evidenceNotes?: string | null;
}

export interface CbamPurchasedElectricityExecutionResponse {
  resultId: string;
  runId: string;
  status: string;
  methodologyCode: string;
  methodologyVersion: string;
  activityRecordId: string;
  electricityMwh: string;
  factorSourceMode: string;
  factorValue: string;
  factorUnit: string;
  indirectEmissionsTco2e: string;
  resultUnit: string;
  exportedElectricityMwh: string | null;
  clientRequestId: string;
  idempotentReplay: boolean;
  createdAt: string;
}

export interface CbamPurchasedElectricityFactorResolution {
  resolved: boolean;
  factorSourceMode: string;
  factorValue: string | null;
  factorUnit: string | null;
  factorValueId: string | null;
  factorDefinitionId: string | null;
  sourceName: string | null;
  sourceDocument: string | null;
  datasetVersion: string | null;
  referenceDescription: string | null;
  validFrom: string | null;
  validUntil: string | null;
  referenceDate: string;
  blockingIssueCodes: string[];
  informationalIssueCodes: string[];
}

export interface CbamPurchasedElectricityResultSummary {
  resultId: string;
  runId: string;
  activityRecordId: string;
  status: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  electricityMwh: string;
  factorSourceMode: string;
  factorValue: string;
  factorUnit: string;
  indirectEmissionsTco2e: string;
  resultUnit: string;
  exportedElectricityMwh: string | null;
  createdAt: string;
}

export interface CbamPurchasedElectricityResultDetail {
  resultId: string;
  runId: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  activityRecordId: string;
  methodologyCode: string;
  methodologyVersion: string;
  formulaVersion: string;
  workbookFormulaRefs: string;
  clientRequestId: string;
  requestFingerprint: string;
  status: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  calculationReferenceDate: string;
  activityQuantity: string;
  activityUnit: string;
  electricityMwh: string;
  factorSourceMode: string;
  factorValue: string;
  factorUnit: string;
  factorTco2ePerMwh: string;
  factorValueId: string | null;
  factorDefinitionId: string | null;
  factorSourceName: string;
  factorSourceDocument: string;
  factorDatasetVersion: string;
  factorReferenceDescription: string;
  factorEffectiveDate: string | null;
  factorValidFrom: string | null;
  factorValidUntil: string | null;
  exportedElectricityQuantity: string | null;
  exportedElectricityUnit: string | null;
  exportedElectricityMwh: string | null;
  indirectEmissionsTco2e: string;
  resultValue: string;
  resultUnit: string;
  evidenceNotes: string | null;
  createdAt: string;
  createdByUserId: string | null;
}

export interface CbamPurchasedElectricityPeriodSummary {
  reportingPeriodBindingId: string;
  methodologyCode: string;
  readinessStatus: string;
  allocationReady: boolean;
  blockingIssueCodes: string[];
  informationalIssueCodes: string[];
  eligibleActivityCount: number;
  validCurrentResultCount: number;
  missingResultCount: number;
  staleResultCount: number;
  totalElectricityMwh: string | null;
  totalIndirectEmissionsTco2e: string | null;
  totalExportedElectricityMwh: string | null;
  resultUnit: string;
}

export interface CbamDirectEmissionsAllocationExecuteRequest {
  clientRequestId: string;
}

export interface CbamDirectEmissionsAllocationExecutionResponse {
  resultId: string;
  runId: string;
  status: string;
  methodologyCode: string;
  methodologyVersion: string;
  balanceStatus: string;
  facilityFossilCo2Tonnes: string;
  cbamFossilCo2Tonnes: string;
  nonCbamFossilCo2Tonnes: string;
  allocatedFossilCo2Tonnes: string;
  remainingFossilCo2Tonnes: string;
  resultUnit: string;
  workbookReportingUnit: string;
  clientRequestId: string;
  idempotentReplay: boolean;
  createdAt: string;
}

export interface CbamDirectEmissionsAllocationReadiness {
  status: string;
  allocationReady: boolean;
  blockingIssueCodes: string[];
  stationaryCombustionStatus: string;
  monthlyProductionBasisStatus: string;
  productionProfileStatus: string;
  productionReconciliationStatus: string;
  sourceResultCount: number;
  monthCount: number;
  fuelCount: number;
  participatingProductionRecordCount: number;
  productProfileGroupCount: number;
  currentAllocationId: string | null;
  currentAllocationStale: boolean;
  staleReasonCodes: string[];
}

export interface CbamDirectEmissionsAllocationResultSummary {
  resultId: string;
  runId: string;
  methodologyCode: string;
  methodologyVersion: string;
  status: string;
  balanceStatus: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  facilityFossilCo2Tonnes: string;
  cbamFossilCo2Tonnes: string;
  nonCbamFossilCo2Tonnes: string;
  allocatedFossilCo2Tonnes: string;
  remainingFossilCo2Tonnes: string;
  resultUnit: string;
  workbookReportingUnit: string;
  createdAt: string;
}

export interface CbamDirectEmissionsAllocationPeriodSummary {
  reportingPeriodBindingId: string;
  methodologyCode: string;
  currentResultId: string | null;
  currentIsStale: boolean;
  staleReasonCodes: string[];
  facilityFossilCo2Tonnes: string | null;
  cbamFossilCo2Tonnes: string | null;
  nonCbamFossilCo2Tonnes: string | null;
  allocatedFossilCo2Tonnes: string | null;
  remainingFossilCo2Tonnes: string | null;
  resultUnit: string;
  workbookReportingUnit: string;
  balanceStatus: string | null;
  totalsByMonth: Record<string, unknown>;
  totalsByFuel: Record<string, unknown>;
  totalsByProductProfile: Array<Record<string, unknown>>;
}

export interface CbamDeaMonthlyBasisSnapshot {
  basisRecordId: string;
  basisRowVersion: number;
  monthStart: string;
  totalProductionQuantity: string;
  cbamQuantity: string;
  quantityUnit: string;
  normalizedTotalProductionTonnes: string;
  normalizedCbamQuantityTonnes: string;
  monthlyShareRaw: string;
}

export interface CbamDeaSourceSnapshot {
  sourceResultId: string;
  sourceRunId: string;
  activityRecordId: string;
  activityDate: string;
  monthStart: string;
  fuelCode: string;
  fuelName: string;
  datasetCode: string;
  datasetVersion: string;
  activityQuantity: string;
  activityUnit: string;
  facilityFossilCo2Tonnes: string;
  cbamFossilCo2Tonnes: string;
  nonCbamFossilCo2Tonnes: string;
  monthlyShareRaw: string;
  facilityFuelMassKg: string;
  cbamFuelMassKg: string;
  facilityEnergyContentTj: string;
  cbamEnergyContentTj: string;
}

export interface CbamDeaProductAllocationSnapshot {
  productId: string;
  productProfileVersionId: string;
  profileVersion: number;
  cnNormalizedCode: string;
  cnDisplayCode: string;
  productName: string;
  productionRecordIds: string[];
  productionQuantitySnapshots: Array<Record<string, unknown>>;
  normalizedQuantityTonnes: string;
  denominatorTonnes: string;
  rawShare: string;
  rawAllocatedFossilCo2Tonnes: string;
  finalAllocatedFossilCo2Tonnes: string;
  roundingAdjustment: string;
  resultUnit: string;
}

export interface CbamDirectEmissionsAllocationResultDetail {
  resultId: string;
  runId: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  methodologyCode: string;
  methodologyVersion: string;
  workbookFilename: string;
  workbookSha256: string;
  workbookFormulaRefs: string;
  clientRequestId: string;
  requestFingerprint: string;
  status: string;
  balanceStatus: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  facilityFossilCo2TonnesRaw: string;
  cbamFossilCo2TonnesRaw: string;
  nonCbamFossilCo2TonnesRaw: string;
  facilityFossilCo2Tonnes: string;
  cbamFossilCo2Tonnes: string;
  nonCbamFossilCo2Tonnes: string;
  allocatedFossilCo2Tonnes: string;
  remainingFossilCo2Tonnes: string;
  resultUnit: string;
  workbookReportingUnit: string;
  workbookGas: string;
  workbookGwp: string;
  workbookGwpFactor: string;
  totalsByMonth: Record<string, unknown>;
  totalsByFuel: Record<string, unknown>;
  monthlyBasis: CbamDeaMonthlyBasisSnapshot[];
  sourceCalculations: CbamDeaSourceSnapshot[];
  productAllocations: CbamDeaProductAllocationSnapshot[];
  createdAt: string;
  createdByUserId: string | null;
}

export interface CbamIndirectEmissionsAllocationExecuteRequest {
  clientRequestId: string;
}

export interface CbamIndirectEmissionsAllocationExecutionResponse {
  resultId: string;
  runId: string;
  status: string;
  methodologyCode: string;
  methodologyVersion: string;
  balanceStatus: string;
  facilityElectricityMwh: string;
  cbamElectricityMwh: string;
  nonCbamElectricityMwh: string;
  allocatedElectricityMwh: string;
  remainingElectricityMwh: string;
  facilityIndirectEmissionsTco2e: string;
  cbamIndirectEmissionsTco2e: string;
  nonCbamIndirectEmissionsTco2e: string;
  allocatedIndirectEmissionsTco2e: string;
  remainingIndirectEmissionsTco2e: string;
  exportedElectricityMwh: string | null;
  electricityUnit: string;
  emissionsUnit: string;
  clientRequestId: string;
  idempotentReplay: boolean;
  createdAt: string;
}

export interface CbamIndirectEmissionsAllocationReadiness {
  status: string;
  allocationReady: boolean;
  blockingIssueCodes: string[];
  purchasedElectricityStatus: string;
  monthlyProductionBasisStatus: string;
  productionProfileStatus: string;
  productionReconciliationStatus: string;
  sourceResultCount: number;
  monthCount: number;
  participatingProductionRecordCount: number;
  productProfileGroupCount: number;
  currentAllocationId: string | null;
  currentAllocationStale: boolean;
  staleReasonCodes: string[];
}

export interface CbamIndirectEmissionsAllocationResultSummary {
  resultId: string;
  runId: string;
  methodologyCode: string;
  methodologyVersion: string;
  status: string;
  balanceStatus: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  facilityElectricityMwh: string;
  cbamElectricityMwh: string;
  nonCbamElectricityMwh: string;
  allocatedElectricityMwh: string;
  remainingElectricityMwh: string;
  facilityIndirectEmissionsTco2e: string;
  cbamIndirectEmissionsTco2e: string;
  allocatedIndirectEmissionsTco2e: string;
  remainingIndirectEmissionsTco2e: string;
  exportedElectricityMwh: string | null;
  electricityUnit: string;
  emissionsUnit: string;
  createdAt: string;
}

export interface CbamIndirectEmissionsAllocationPeriodSummary {
  reportingPeriodBindingId: string;
  methodologyCode: string;
  currentResultId: string | null;
  currentIsStale: boolean;
  staleReasonCodes: string[];
  facilityElectricityMwh: string | null;
  cbamElectricityMwh: string | null;
  nonCbamElectricityMwh: string | null;
  allocatedElectricityMwh: string | null;
  remainingElectricityMwh: string | null;
  facilityIndirectEmissionsTco2e: string | null;
  cbamIndirectEmissionsTco2e: string | null;
  allocatedIndirectEmissionsTco2e: string | null;
  remainingIndirectEmissionsTco2e: string | null;
  exportedElectricityMwh: string | null;
  electricityUnit: string;
  emissionsUnit: string;
  balanceStatus: string | null;
  totalsByMonth: Record<string, unknown>;
  totalsByProductProfile: Array<Record<string, unknown>>;
}

export interface CbamIeaMonthlyBasisSnapshot {
  monthStart: string;
  basisRecordId: string;
  basisRowVersion: number;
  totalProductionQuantity: string;
  cbamQuantity: string;
  quantityUnit: string;
  normalizedTotalProductionTonnes: string;
  normalizedCbamQuantityTonnes: string;
  monthlyShareRaw: string;
}

export interface CbamIeaSourceSnapshot {
  sourceResultId: string;
  activityRecordId: string;
  activityDate: string;
  monthStart: string;
  activityQuantity: string;
  activityUnit: string;
  electricityMwh: string;
  factorSourceMode: string;
  factorValue: string;
  factorUnit: string;
  factorTco2ePerMwh: string;
  factorSourceName: string | null;
  factorSourceDocument: string | null;
  factorDatasetVersion: string | null;
  factorReferenceDescription: string | null;
  monthlyShareRaw: string;
  facilityElectricityMwh: string;
  cbamElectricityMwh: string;
  nonCbamElectricityMwh: string;
  facilityIndirectEmissionsTco2e: string;
  cbamIndirectEmissionsTco2e: string;
  nonCbamIndirectEmissionsTco2e: string;
  exportedElectricityMwh: string | null;
}

export interface CbamIeaProductAllocationSnapshot {
  productId: string;
  productProfileVersionId: string;
  profileVersion: number;
  cnNormalizedCode: string;
  cnDisplayCode: string;
  productName: string;
  productionRecordIds: string[];
  productionQuantitySnapshots: Array<Record<string, unknown>>;
  normalizedQuantityTonnes: string;
  denominatorTonnes: string;
  rawShare: string;
  rawAllocatedElectricityMwh: string;
  finalAllocatedElectricityMwh: string;
  electricityRoundingAdjustment: string;
  rawAllocatedIndirectEmissionsTco2e: string;
  finalAllocatedIndirectEmissionsTco2e: string;
  emissionsRoundingAdjustment: string;
  electricityUnit: string;
  emissionsUnit: string;
}

export interface CbamIndirectEmissionsAllocationResultDetail {
  resultId: string;
  runId: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  methodologyCode: string;
  methodologyVersion: string;
  workbookFilename: string;
  workbookSha256: string;
  workbookFormulaRefs: string;
  clientRequestId: string;
  requestFingerprint: string;
  status: string;
  balanceStatus: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  facilityElectricityMwhRaw: string;
  cbamElectricityMwhRaw: string;
  nonCbamElectricityMwhRaw: string;
  facilityElectricityMwh: string;
  cbamElectricityMwh: string;
  nonCbamElectricityMwh: string;
  allocatedElectricityMwh: string;
  remainingElectricityMwh: string;
  facilityIndirectEmissionsTco2eRaw: string;
  cbamIndirectEmissionsTco2eRaw: string;
  nonCbamIndirectEmissionsTco2eRaw: string;
  facilityIndirectEmissionsTco2e: string;
  cbamIndirectEmissionsTco2e: string;
  nonCbamIndirectEmissionsTco2e: string;
  allocatedIndirectEmissionsTco2e: string;
  remainingIndirectEmissionsTco2e: string;
  exportedElectricityMwh: string | null;
  electricityUnit: string;
  emissionsUnit: string;
  sourceResultCount: number;
  monthCount: number;
  participatingProductionRecordCount: number;
  productProfileGroupCount: number;
  totalsByMonth: Record<string, unknown>;
  monthlyBasis: CbamIeaMonthlyBasisSnapshot[];
  sources: CbamIeaSourceSnapshot[];
  products: CbamIeaProductAllocationSnapshot[];
  createdAt: string;
  createdByUserId: string | null;
}

/** Phase 9A/9B Conventional production processes */

export type CbamProductionProcessReadinessStatus =
  | 'EMPTY'
  | 'INCOMPLETE'
  | 'UNBALANCED'
  | 'STALE'
  | 'READY';

export type CbamProductionProcessBalanceStatus = 'BALANCED' | 'UNBALANCED' | 'INCOMPLETE';

export interface CbamProductionProcessControlledListItem {
  code: string;
  labelEn: string;
  descriptionEn: string | null;
  sortOrder: number;
  workbookRef: string;
}

export interface CbamProductionProcessControlledList {
  listCode: string;
  titleEn: string;
  workbookNamedRange: string;
  workbookSheet: string;
  helpEn: string | null;
  items: CbamProductionProcessControlledListItem[];
}

export interface CbamProductionProcessMetadata {
  methodologyCode: string;
  methodologyVersion: string;
  workbookFilename: string;
  workbookSha256: string;
  workbookFormulaRefs: string;
  supportedCalculationMethods: string[];
  disabledCalculationMethods: string[];
  productionQuantitySource: string;
  productionQuantitySourceNote: string;
  fieldMap: Record<string, Record<string, string>>;
  extraction: Record<string, string>;
  controlledLists: CbamProductionProcessControlledList[];
}

export interface CbamProductionProcessProductUse {
  id: string;
  processId: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  sourceProductProfileVersionId: string | null;
  targetProductProfileVersionId: string;
  quantity: string;
  unit: string;
  quantityTonnes: string | null;
  notes: string | null;
  rowVersion: number;
}

export interface CbamProductionProcessProductUseCreate {
  targetProductProfileVersionId: string;
  quantity: string;
  unit?: string;
  notes?: string | null;
}

export interface CbamProductionProcessProductUseUpdate {
  rowVersion: number;
  quantity?: string | null;
  unit?: string | null;
  notes?: string | null;
  targetProductProfileVersionId?: string | null;
}

export interface CbamProductionProcessAllocationLink {
  currentResultId: string | null;
  isReady: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  productAllocatedValue: string | null;
  allocatedElectricityMwh: string | null;
  allocatedIndirectEmissionsTco2e: string | null;
  resultUnit: string | null;
  electricityUnit: string | null;
  blockingCode: string | null;
}

/** Facility purchased-electricity export (read-only context for the process). */
export interface CbamProductionProcessExportedElectricity {
  exportedElectricityMwh: string | null;
  electricityUnit: string;
  source: string;
  note: string;
}

/** Process-level D_Processes L71/L72 entry; T72 attributedDirectTco2e is server-only. */
export interface CbamProductionProcessProcessExportedElectricity {
  hasExportedElectricity: boolean | null;
  quantity: string | null;
  quantityUnit: string | null;
  quantityMwh: string | null;
  emissionFactor: string | null;
  efUnit: string | null;
  provenance: string | null;
  calculationStatus: string;
  attributedDirectTco2e: string | null;
  formulaRef: string | null;
  facilityExportedElectricityMwh: string | null;
  installationFacilityExportedElectricityMwh: string | null;
  installationProcessExportedElectricityMwh: string | null;
  reconciliationStatus: string;
  reconciliationDifferenceMwh: string | null;
  reconciliationNote: string;
  electricityUnit: string;
  factorUnit: string;
}

export interface CbamProductionProcessReconciliation {
  processProducedTonnes: string | null;
  productionRecordsTonnes: string | null;
  differenceTonnes: string | null;
  source: string;
  note: string;
}

export interface CbamProductionProcessHeat {
  hasMeasurableHeat: boolean | null;
  importedQuantity: string | null;
  importedUnit: string | null;
  exportedQuantity: string | null;
  exportedUnit: string | null;
  importedEf: string | null;
  exportedEf: string | null;
  efUnit: string | null;
  factorSource: string | null;
  factorDocument: string | null;
  calculationStatus: string;
  attributedTco2: string | null;
  formulaRef: string | null;
}

export interface CbamProductionProcessWasteGas {
  hasWasteGas: boolean | null;
  importedQuantity: string | null;
  importedUnit: string | null;
  exportedQuantity: string | null;
  exportedUnit: string | null;
  provenance: string | null;
  calculationStatus: string;
  attributedTco2: string | null;
  efTco2PerTj: string | null;
  formulaRef: string | null;
  note: string | null;
}

export interface CbamProductionProcessDistribution {
  producedQuantity: string | null;
  producedQuantityUnit: string | null;
  producedTonnes: string | null;
  marketedQuantity: string | null;
  marketedQuantityUnit: string | null;
  marketedTonnes: string | null;
  otherCbamTonnes: string;
  nonCbamQuantity: string | null;
  nonCbamQuantityUnit: string | null;
  nonCbamTonnes: string | null;
  distributedTonnes: string | null;
  remainingTonnes: string | null;
  balanceStatus: string;
  allToMarket: boolean | null;
  marketShare: string | null;
  productUses: CbamProductionProcessProductUse[];
}

export interface CbamProductionProcessReadiness {
  processId: string | null;
  reportingPeriodBindingId: string;
  status: CbamProductionProcessReadinessStatus;
  blockingIssueCodes: string[];
  informationalCodes: string[];
  balanceStatus: string | null;
  remainingTonnes: string | null;
}

export interface CbamProductionProcessBindingSummary {
  reportingPeriodBindingId: string;
  processCount: number;
  draftCount: number;
  archivedCount: number;
  readyCount: number;
  unbalancedCount: number;
  processes: CbamProductionProcessReadiness[];
}

export interface CbamProductionProcess {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  installationProfileId: string;
  productProfileVersionId: string | null;
  name: string | null;
  identifier: string | null;
  calculationMethod: string;
  status: string;
  notes: string | null;
  rowVersion: number;
  readiness: CbamProductionProcessReadiness;
  distribution: CbamProductionProcessDistribution;
  productionReconciliation: CbamProductionProcessReconciliation;
  directEmissionsAllocation: CbamProductionProcessAllocationLink;
  indirectEmissionsAllocation: CbamProductionProcessAllocationLink;
  exportedElectricity: CbamProductionProcessExportedElectricity;
  processExportedElectricity: CbamProductionProcessProcessExportedElectricity;
  measurableHeat: CbamProductionProcessHeat;
  wasteGas: CbamProductionProcessWasteGas;
  dataQualityCode: string | null;
  dataVerificationCode: string | null;
  dataQualityJustificationCode: string | null;
}

export interface CbamProductionProcessCreate {
  installationProfileId: string;
  name?: string | null;
  identifier?: string | null;
  calculationMethod?: string;
  productProfileVersionId?: string | null;
  producedQuantity?: string | null;
  producedQuantityUnit?: string | null;
  marketedQuantity?: string | null;
  marketedQuantityUnit?: string | null;
  nonCbamQuantity?: string | null;
  nonCbamQuantityUnit?: string | null;
  hasMeasurableHeat?: boolean | null;
  heatImportedQuantity?: string | null;
  heatImportedUnit?: string | null;
  heatExportedQuantity?: string | null;
  heatExportedUnit?: string | null;
  heatImportedEf?: string | null;
  heatExportedEf?: string | null;
  heatEfUnit?: string | null;
  heatFactorSource?: string | null;
  heatFactorDocument?: string | null;
  hasWasteGas?: boolean | null;
  wasteGasImportedQuantity?: string | null;
  wasteGasImportedUnit?: string | null;
  wasteGasExportedQuantity?: string | null;
  wasteGasExportedUnit?: string | null;
  wasteGasProvenance?: string | null;
  hasExportedElectricity?: boolean | null;
  exportedElectricityQuantity?: string | null;
  exportedElectricityUnit?: string | null;
  exportedElectricityEmissionFactor?: string | null;
  exportedElectricityEfUnit?: string | null;
  exportedElectricityProvenance?: string | null;
  dataQualityCode?: string | null;
  dataVerificationCode?: string | null;
  dataQualityJustificationCode?: string | null;
  notes?: string | null;
}

export interface CbamProductionProcessUpdate {
  rowVersion: number;
  name?: string | null;
  identifier?: string | null;
  calculationMethod?: string | null;
  productProfileVersionId?: string | null;
  producedQuantity?: string | null;
  producedQuantityUnit?: string | null;
  marketedQuantity?: string | null;
  marketedQuantityUnit?: string | null;
  nonCbamQuantity?: string | null;
  nonCbamQuantityUnit?: string | null;
  hasMeasurableHeat?: boolean | null;
  heatImportedQuantity?: string | null;
  heatImportedUnit?: string | null;
  heatExportedQuantity?: string | null;
  heatExportedUnit?: string | null;
  heatImportedEf?: string | null;
  heatExportedEf?: string | null;
  heatEfUnit?: string | null;
  heatFactorSource?: string | null;
  heatFactorDocument?: string | null;
  hasWasteGas?: boolean | null;
  wasteGasImportedQuantity?: string | null;
  wasteGasImportedUnit?: string | null;
  wasteGasExportedQuantity?: string | null;
  wasteGasExportedUnit?: string | null;
  wasteGasProvenance?: string | null;
  hasExportedElectricity?: boolean | null;
  exportedElectricityQuantity?: string | null;
  exportedElectricityUnit?: string | null;
  exportedElectricityEmissionFactor?: string | null;
  exportedElectricityEfUnit?: string | null;
  exportedElectricityProvenance?: string | null;
  dataQualityCode?: string | null;
  dataVerificationCode?: string | null;
  dataQualityJustificationCode?: string | null;
  notes?: string | null;
}

export interface CbamProductionProcessVersionRequest {
  rowVersion: number;
}

/** Phase 10A/10B purchased precursors (CBAM SEE E_PurchPrec). */

export type CbamPurchasedPrecursorDataSourceMode = 'SUPPLIER_DATA' | 'EU_DEFAULT';

export type CbamPurchasedPrecursorReadinessStatus =
  | 'EMPTY'
  | 'INCOMPLETE'
  | 'UNBALANCED'
  | 'UNRESOLVED'
  | 'AMBIGUOUS'
  | 'READY';

export type CbamPrecursorBalanceStatus = 'BALANCED' | 'UNBALANCED' | 'INCOMPLETE';

export type CbamPrecursorResolutionStatus =
  | 'RESOLVED'
  | 'UNRESOLVED'
  | 'AMBIGUOUS'
  | 'NOT_APPLICABLE';

export interface CbamPrecursorControlledListItem {
  code: string;
  labelEn: string;
  descriptionEn: string | null;
  sortOrder: number;
  workbookRef: string;
}

export interface CbamPrecursorControlledList {
  listCode: string;
  titleEn: string;
  workbookNamedRange: string;
  workbookSheet: string;
  helpEn: string | null;
  items: CbamPrecursorControlledListItem[];
}

export interface CbamPrecursorDefaultDataset {
  id: string;
  datasetCode: string;
  datasetVersion: string;
  contentChecksum: string;
  sourceWorkbookName: string;
  sourceWorkbookSha256: string;
  sourceTemplateVersion: string;
  regulationReference: string | null;
  validFrom: string;
  validUntil: string | null;
  status: string;
  valueCount: number;
}

export interface CbamPrecursorDefaultValue {
  id: string;
  datasetId: string;
  countryName: string;
  isOtherCountriesGroup: boolean;
  cnNormalizedCode: string;
  cnDisplayCode: string | null;
  goodsCategory: string | null;
  goodsDescription: string | null;
  productionRoute: string | null;
  directValue: string | null;
  directValueStatus: string;
  indirectValue: string | null;
  indirectValueStatus: string;
  totalValue: string | null;
  totalValueStatus: string;
  directUnit: string;
  indirectUnit: string;
  unitNote: string | null;
  markedUpTotals: Record<string, unknown>;
  originalKeys: Record<string, unknown>;
  lookupKey: string;
  sourceSheet: string;
  sourceRow: number;
}

export interface CbamPrecursorDefaultResolveRequest {
  countryOfOrigin: string;
  cnCode: string;
  productionRoute?: string | null;
  goodsDescription?: string | null;
}

export interface CbamPrecursorDefaultResolution {
  status: CbamPrecursorResolutionStatus;
  issueCode: string | null;
  lookupKey: string;
  countryOfOrigin: string | null;
  cnNormalizedCode: string | null;
  productionRoute: string | null;
  goodsDescription: string | null;
  dataset: CbamPrecursorDefaultDataset | null;
  value: CbamPrecursorDefaultValue | null;
  candidateCount: number;
  candidates: CbamPrecursorDefaultValue[];
  otherCountriesNote: string;
}

export interface CbamPurchasedPrecursorMetadata {
  methodologyCode: string;
  methodologyVersion: string;
  workbookFilename: string;
  workbookSha256: string;
  workbookPrimarySheet: string;
  workbookFormulaRefs: string;
  supportedDataSourceModes: string[];
  units: Record<string, string>;
  fieldMap: Record<string, Record<string, string>>;
  extraction: Record<string, string>;
  controlledLists: CbamPrecursorControlledList[];
  defaultValueDataset: CbamPrecursorDefaultDataset;
  otherCountriesNote: string;
  rollupNote: string;
}

export interface CbamPrecursorProductUse {
  id: string;
  precursorId: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  targetProductProfileVersionId: string;
  quantity: string;
  unit: string;
  quantityTonnes: string | null;
  notes: string | null;
  rowVersion: number;
}

export interface CbamPrecursorProductUseCreate {
  targetProductProfileVersionId: string;
  quantity: string;
  unit?: string;
  notes?: string | null;
}

export interface CbamPrecursorProductUseUpdate {
  rowVersion: number;
  targetProductProfileVersionId?: string | null;
  quantity?: string | null;
  unit?: string | null;
  notes?: string | null;
}

export interface CbamPurchasedPrecursorDistribution {
  quantity: string | null;
  quantityUnit: string | null;
  purchasedTonnes: string | null;
  nonCbamQuantity: string | null;
  nonCbamQuantityUnit: string | null;
  nonCbamTonnes: string | null;
  productUseTonnes: string;
  distributedTonnes: string | null;
  remainingTonnes: string | null;
  balanceStatus: string;
  formulaRef: string;
  productUses: CbamPrecursorProductUse[];
}

export interface CbamPurchasedPrecursorSupplierData {
  applicable: boolean;
  specificDirectEmbeddedEmissions: string | null;
  specificDirectUnit: string | null;
  specificDirectSourceCode: string | null;
  electricityConsumptionIntensity: string | null;
  electricityIntensityUnit: string | null;
  electricityIntensitySourceCode: string | null;
  electricityEmissionFactor: string | null;
  electricityEfUnit: string | null;
  electricityEfSourceCode: string | null;
  specificIndirectEmbeddedEmissions: string | null;
  specificIndirectUnit: string | null;
  provenanceNotes: string | null;
  evidenceReference: string | null;
}

export interface CbamPurchasedPrecursorDefaultSource {
  applicable: boolean;
  resolutionStatus: CbamPrecursorResolutionStatus;
  issueCode: string | null;
  fromSnapshot: boolean;
  datasetId: string | null;
  datasetCode: string | null;
  datasetVersion: string | null;
  contentChecksum: string | null;
  defaultValueId: string | null;
  lookupKey: string | null;
  specificDirectEmbeddedEmissions: string | null;
  specificDirectStatus: string | null;
  specificDirectUnit: string | null;
  specificIndirectEmbeddedEmissions: string | null;
  specificIndirectStatus: string | null;
  specificIndirectUnit: string | null;
  justificationCode: string | null;
  candidateCount: number;
  snapshot: Record<string, unknown> | null;
  otherCountriesNote: string;
}

export interface CbamPurchasedPrecursorCalculation {
  status: string;
  valueSource: string | null;
  quantityTonnes: string | null;
  specificDirectEmbeddedEmissions: string | null;
  specificIndirectEmbeddedEmissions: string | null;
  totalDirectEmbeddedEmissions: string | null;
  totalIndirectEmbeddedEmissions: string | null;
  totalEmbeddedEmissions: string | null;
  resultUnit: string;
  formulaRefs: string;
  rollupNote: string;
}

export interface CbamPurchasedPrecursorReadiness {
  precursorId: string | null;
  reportingPeriodBindingId: string;
  status: CbamPurchasedPrecursorReadinessStatus;
  blockingIssueCodes: string[];
  informationalCodes: string[];
  balanceStatus: string | null;
  remainingTonnes: string | null;
  resolutionStatus: string;
}

export interface CbamPurchasedPrecursor {
  id: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  installationProfileId: string;
  purchasedInputRecordId: string | null;
  supplierId: string | null;
  name: string | null;
  identifier: string | null;
  aggregatedGoodsCategory: string | null;
  cnNormalizedCode: string | null;
  cnDisplayCode: string | null;
  countryOfOrigin: string | null;
  productionRoute: string | null;
  dataSourceMode: string;
  status: string;
  notes: string | null;
  rowVersion: number;
  readiness: CbamPurchasedPrecursorReadiness;
  distribution: CbamPurchasedPrecursorDistribution;
  supplierData: CbamPurchasedPrecursorSupplierData;
  defaultSource: CbamPurchasedPrecursorDefaultSource;
  calculation: CbamPurchasedPrecursorCalculation;
}

export interface CbamPurchasedPrecursorCreate {
  installationProfileId: string;
  dataSourceMode?: string;
  name?: string | null;
  identifier?: string | null;
  aggregatedGoodsCategory?: string | null;
  cnCode?: string | null;
  countryOfOrigin?: string | null;
  productionRoute?: string | null;
  purchasedInputRecordId?: string | null;
  supplierId?: string | null;
  quantity?: string | null;
  quantityUnit?: string | null;
  nonCbamQuantity?: string | null;
  nonCbamQuantityUnit?: string | null;
  specificDirectEmbeddedEmissions?: string | null;
  specificDirectUnit?: string | null;
  specificDirectSourceCode?: string | null;
  electricityConsumptionIntensity?: string | null;
  electricityIntensityUnit?: string | null;
  electricityIntensitySourceCode?: string | null;
  electricityEmissionFactor?: string | null;
  electricityEfUnit?: string | null;
  electricityEfSourceCode?: string | null;
  defaultValueId?: string | null;
  defaultJustificationCode?: string | null;
  provenanceNotes?: string | null;
  evidenceReference?: string | null;
  notes?: string | null;
}

export interface CbamPurchasedPrecursorUpdate {
  rowVersion: number;
  dataSourceMode?: string | null;
  name?: string | null;
  identifier?: string | null;
  aggregatedGoodsCategory?: string | null;
  cnCode?: string | null;
  countryOfOrigin?: string | null;
  productionRoute?: string | null;
  purchasedInputRecordId?: string | null;
  supplierId?: string | null;
  quantity?: string | null;
  quantityUnit?: string | null;
  nonCbamQuantity?: string | null;
  nonCbamQuantityUnit?: string | null;
  specificDirectEmbeddedEmissions?: string | null;
  specificDirectUnit?: string | null;
  specificDirectSourceCode?: string | null;
  electricityConsumptionIntensity?: string | null;
  electricityIntensityUnit?: string | null;
  electricityIntensitySourceCode?: string | null;
  electricityEmissionFactor?: string | null;
  electricityEfUnit?: string | null;
  electricityEfSourceCode?: string | null;
  defaultValueId?: string | null;
  defaultJustificationCode?: string | null;
  provenanceNotes?: string | null;
  evidenceReference?: string | null;
  notes?: string | null;
}

export interface CbamPurchasedPrecursorVersionRequest {
  rowVersion: number;
}

export interface CbamPurchasedPrecursorBindingSummary {
  reportingPeriodBindingId: string;
  precursorCount: number;
  draftCount: number;
  archivedCount: number;
  readyCount: number;
  unbalancedCount: number;
  unresolvedCount: number;
  ambiguousCount: number;
  precursors: CbamPurchasedPrecursorReadiness[];
}

export interface CbamProductEmbeddedEmissionsExecuteRequest {
  clientRequestId: string;
  /** Omit for new calculations so the backend defaults to V2. */
  methodologyCode?: string;
}

export interface CbamProductEmbeddedEmissionsExecutionResponse {
  resultId: string;
  runId: string;
  status: string;
  methodologyCode: string;
  methodologyVersion: string;
  productCount: number;
  precursorContributionCount: number;
  internalContributionCount: number;
  totalDirectTco2e: string;
  totalIndirectTco2e: string;
  totalEmbeddedTco2e: string;
  resultUnit: string;
  specificUnit: string;
  clientRequestId: string;
  idempotentReplay: boolean;
  createdAt: string;
}

export interface CbamProductEmbeddedEmissionsProductReadiness {
  productProfileVersionId: string;
  productId: string | null;
  cnNormalizedCode: string | null;
  processId: string | null;
  status: string;
  blockingIssueCodes: string[];
  informationalCodes: string[];
  denominatorTonnes: string | null;
  productionRecordsTonnes: string | null;
  precursorUseCount: number;
}

export interface CbamProductEmbeddedEmissionsReadiness {
  reportingPeriodBindingId: string;
  methodologyCode: string;
  status: string;
  rollupReady: boolean;
  blockingIssueCodes: string[];
  informationalCodes: string[];
  directEmissionsAllocationResultId: string | null;
  directEmissionsAllocationStale: boolean;
  indirectEmissionsAllocationResultId: string | null;
  indirectEmissionsAllocationStale: boolean;
  eligibleProductCount: number;
  blockedProductCount: number;
  precursorContributionCount: number;
  products: CbamProductEmbeddedEmissionsProductReadiness[];
  currentResultId: string | null;
  currentIsStale: boolean;
  staleReasonCodes: string[];
  exportedElectricityNoteCode: string;
  exportedElectricityNote: string;
  internalPrecursorNoteCode: string;
  internalPrecursorNote: string;
}

export interface CbamProductEmbeddedEmissionsResultSummary {
  resultId: string;
  runId: string;
  methodologyCode: string;
  methodologyVersion: string;
  status: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  productCount: number;
  precursorContributionCount: number;
  internalContributionCount: number;
  totalDirectTco2e: string;
  totalIndirectTco2e: string;
  totalEmbeddedTco2e: string;
  resultUnit: string;
  specificUnit: string;
  createdAt: string;
}

/** Nested product row from ResultDetail / PeriodSummary.totalsByProduct (_product_payload). */
export interface CbamProductEmbeddedEmissionsProductRow {
  productId: string;
  productProfileVersionId: string;
  profileVersion: number;
  cnNormalizedCode: string;
  cnDisplayCode: string;
  productName: string;
  processId: string;
  processRowVersion: number;
  processProducedQuantity: string;
  processProducedQuantityUnit: string;
  denominatorTonnes: string;
  productionRecordCount: number;
  productionRecordsTonnes: string | null;
  productionRecordIds: string[];
  deaResultId: string;
  deaProductAllocationId: string | null;
  deaDirectTco2: string;
  ieaResultId: string;
  ieaProductAllocationId: string | null;
  ieaIndirectTco2e: string;
  hasMeasurableHeat: boolean;
  heatAttributedTco2e: string;
  hasWasteGas: boolean;
  wasteGasAttributedTco2e: string;
  exportedElectricityDirectTco2e: string;
  exportedElectricityNoteCode: string;
  hasExportedElectricity: boolean | null;
  exportedElectricityMwh: string | null;
  exportedElectricityEmissionFactor: string | null;
  ownDirectTco2eRaw: string;
  ownIndirectTco2eRaw: string;
  precursorDirectTco2eRaw: string;
  precursorIndirectTco2eRaw: string;
  internalDirectTco2eRaw: string;
  internalIndirectTco2eRaw: string;
  totalDirectTco2eRaw: string;
  totalIndirectTco2eRaw: string;
  totalEmbeddedTco2eRaw: string;
  ownDirectTco2e: string;
  ownIndirectTco2e: string;
  precursorDirectTco2e: string;
  precursorIndirectTco2e: string;
  internalDirectTco2e: string;
  internalIndirectTco2e: string;
  totalDirectTco2e: string;
  totalIndirectTco2e: string;
  totalEmbeddedTco2e: string;
  specificDirectRaw: string;
  specificIndirectRaw: string;
  specificTotalRaw: string;
  specificDirect: string;
  specificIndirect: string;
  specificTotal: string;
  precursorContributionCount: number;
  internalContributionCount: number;
  resultUnit: string;
  specificUnit: string;
  deaSourceUnit: string;
  components: Record<string, unknown> | null;
  provenance: Record<string, unknown> | null;
}

/** Nested precursor contribution from ResultDetail (_contribution_payload). */
export interface CbamProductEmbeddedEmissionsPrecursorContribution {
  productProfileVersionId: string;
  precursorId: string;
  precursorRowVersion: number;
  precursorName: string;
  precursorCnNormalizedCode: string | null;
  precursorCnDisplayCode: string | null;
  dataSourceMode: string;
  valueSource: string;
  productUseId: string;
  productUseRowVersion: number;
  productUseQuantity: string;
  productUseUnit: string;
  quantityTonnes: string;
  specificDirect: string;
  specificIndirect: string;
  contributionDirectTco2eRaw: string;
  contributionIndirectTco2eRaw: string;
  contributionDirectTco2e: string;
  contributionIndirectTco2e: string;
  defaultDatasetId: string | null;
  defaultValueId: string | null;
  defaultSnapshot: Record<string, unknown> | null;
  resultUnit: string;
  specificUnit: string;
}

/** Nested internal contribution from ResultDetail (_internal_contribution_payload). */
export interface CbamProductEmbeddedEmissionsInternalContribution {
  consumerProductProfileVersionId: string;
  supplierProductProfileVersionId: string;
  consumerProcessId: string;
  supplierProcessId: string;
  supplierProcessRowVersion: number;
  productUseId: string;
  productUseRowVersion: number;
  productUseQuantity: string;
  productUseUnit: string;
  quantityTonnes: string;
  consumerDenominatorTonnes: string;
  aCoefficient: string;
  supplierSpecificDirect: string;
  supplierSpecificIndirect: string;
  contributionDirectTco2eRaw: string;
  contributionIndirectTco2eRaw: string;
  contributionDirectTco2e: string;
  contributionIndirectTco2e: string;
  resultUnit: string;
  specificUnit: string;
}

export interface CbamProductEmbeddedEmissionsResultDetail {
  resultId: string;
  runId: string;
  organizationId: string;
  reportingPeriodBindingId: string;
  methodologyCode: string;
  methodologyVersion: string;
  workbookFilename: string;
  workbookSha256: string;
  workbookFormulaRefs: string;
  clientRequestId: string;
  requestFingerprint: string;
  status: string;
  isCurrent: boolean;
  isStale: boolean;
  staleReasonCodes: string[];
  productCount: number;
  precursorContributionCount: number;
  internalContributionCount: number;
  totalDirectTco2eRaw: string;
  totalIndirectTco2eRaw: string;
  totalEmbeddedTco2eRaw: string;
  totalDirectTco2e: string;
  totalIndirectTco2e: string;
  totalEmbeddedTco2e: string;
  resultUnit: string;
  specificUnit: string;
  deaSourceUnit: string;
  workbookGas: string;
  workbookGwp: string;
  workbookGwpFactor: string;
  gwpEquivalenceNote: string;
  denominatorNote: string;
  exportedElectricityNoteCode: string;
  exportedElectricityNote: string;
  internalPrecursorNoteCode: string;
  internalPrecursorNote: string;
  directEmissionsAllocationResultId: string | null;
  indirectEmissionsAllocationResultId: string | null;
  informationalCodes: string[];
  products: CbamProductEmbeddedEmissionsProductRow[];
  precursorContributions: CbamProductEmbeddedEmissionsPrecursorContribution[];
  internalContributions: CbamProductEmbeddedEmissionsInternalContribution[];
  createdAt: string;
  createdByUserId: string | null;
}

export interface CbamProductEmbeddedEmissionsPeriodSummary {
  reportingPeriodBindingId: string;
  methodologyCode: string;
  currentResultId: string | null;
  currentIsStale: boolean;
  staleReasonCodes: string[];
  productCount: number | null;
  precursorContributionCount: number | null;
  internalContributionCount: number | null;
  totalDirectTco2e: string | null;
  totalIndirectTco2e: string | null;
  totalEmbeddedTco2e: string | null;
  resultUnit: string;
  specificUnit: string;
  totalsByProduct: CbamProductEmbeddedEmissionsProductRow[];
}
