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
}

export interface CbamProductionRecordCreate {
  installationProfileId: string;
  productProfileVersionId?: string | null;
  productionDate?: string | null;
  quantity: string;
  unit: string;
  notes?: string | null;
  sourceType?: string;
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
