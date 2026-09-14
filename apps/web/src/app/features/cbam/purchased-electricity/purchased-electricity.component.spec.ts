import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamActivityRecord,
  CbamPurchasedElectricityFactorResolution,
  CbamPurchasedElectricityPeriodSummary,
  CbamPurchasedElectricityResultDetail,
  CbamPurchasedElectricityResultSummary,
} from '../cbam-api.service';
import { CbamPurchasedElectricityComponent } from './purchased-electricity.component';
import {
  createClientRequestId,
  formatDecimalDisplay,
  isBlankDecimalInput,
  isEligibleElectricityActivity,
  isNegativeDecimalString,
  isZeroDecimalString,
  mapElectricityInfoCode,
  mapElectricityIssueCode,
  mapPurchasedElectricityError,
  mapResultLifecycleLabel,
} from './purchased-electricity.util';

describe('CbamPurchasedElectricityComponent', () => {
  let fixture: ComponentFixture<CbamPurchasedElectricityComponent>;
  let component: CbamPurchasedElectricityComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const bindingBase = `${orgBase}/reporting-period-bindings/binding-1`;

  const emptySummary: CbamPurchasedElectricityPeriodSummary = {
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1',
    readinessStatus: 'EMPTY',
    allocationReady: false,
    blockingIssueCodes: ['ELECTRICITY_ACTIVITIES_REQUIRED'],
    informationalIssueCodes: ['TURKEY_ELECTRICITY_DEFAULT_FACTOR_PROVENANCE_MISSING'],
    eligibleActivityCount: 0,
    validCurrentResultCount: 0,
    missingResultCount: 0,
    staleResultCount: 0,
    totalElectricityMwh: null,
    totalIndirectEmissionsTco2e: null,
    totalExportedElectricityMwh: null,
    resultUnit: 'tCO2e',
  };

  const readySummary: CbamPurchasedElectricityPeriodSummary = {
    ...emptySummary,
    readinessStatus: 'READY',
    blockingIssueCodes: [],
    eligibleActivityCount: 1,
    validCurrentResultCount: 1,
    totalElectricityMwh: '100.000000000000000000',
    totalIndirectEmissionsTco2e: '43.90000000',
    totalExportedElectricityMwh: '10.000000000000000000',
  };

  const unresolvedDefault: CbamPurchasedElectricityFactorResolution = {
    resolved: false,
    factorSourceMode: 'PLATFORM_DEFAULT',
    factorValue: null,
    factorUnit: null,
    factorValueId: null,
    factorDefinitionId: 'def-1',
    sourceName: null,
    sourceDocument: null,
    datasetVersion: null,
    referenceDescription: null,
    validFrom: null,
    validUntil: null,
    referenceDate: '2024-06-15',
    blockingIssueCodes: ['UNRESOLVED_PLATFORM_DEFAULT'],
    informationalIssueCodes: ['TURKEY_ELECTRICITY_DEFAULT_FACTOR_PROVENANCE_MISSING'],
  };

  const resolvedDefault: CbamPurchasedElectricityFactorResolution = {
    ...unresolvedDefault,
    resolved: true,
    factorValue: '0.41000000',
    factorUnit: 'tCO2e/MWh',
    factorValueId: 'fv-1',
    sourceName: 'TEST_PLATFORM',
    sourceDocument: 'DOC',
    datasetVersion: 'v1',
    referenceDescription: 'Test default',
    blockingIssueCodes: [],
  };

  const elecActivity: CbamActivityRecord = {
    id: 'act-elec',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    installationProfileId: 'inst-1',
    activityGroup: 'PURCHASED_ENERGY',
    activityType: 'ELECTRICITY',
    activityDate: '2024-06-15',
    quantity: '100',
    unit: 'MWh',
    dataSourceType: 'PRIMARY',
    sourceReference: null,
    notes: null,
    status: 'active',
    rowVersion: 1,
  };

  const gasActivity: CbamActivityRecord = {
    ...elecActivity,
    id: 'act-gas',
    activityType: 'NATURAL_GAS',
    quantity: '50',
    unit: 'Sm3',
  };

  const kwhActivity: CbamActivityRecord = {
    ...elecActivity,
    id: 'act-kwh',
    quantity: '50000',
    unit: 'kWh',
  };

  const resultSummary: CbamPurchasedElectricityResultSummary = {
    resultId: 'res-1',
    runId: 'run-1',
    activityRecordId: 'act-elec',
    status: 'COMPLETED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    electricityMwh: '100.000000000000000000',
    factorSourceMode: 'MANUAL',
    factorValue: '0.43900000',
    factorUnit: 'tCO2e/MWh',
    indirectEmissionsTco2e: '43.90000000',
    resultUnit: 'tCO2e',
    exportedElectricityMwh: '10.000000000000000000',
    createdAt: '2024-06-20T10:00:00Z',
  };

  const resultDetail: CbamPurchasedElectricityResultDetail = {
    resultId: 'res-1',
    runId: 'run-1',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    activityRecordId: 'act-elec',
    methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1',
    methodologyVersion: '1',
    formulaVersion: 'purchased-electricity-indirect-v1',
    workbookFormulaRefs: 'SEE!T66',
    clientRequestId: '11111111-1111-4111-8111-111111111111',
    requestFingerprint: 'abc',
    status: 'COMPLETED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    calculationReferenceDate: '2024-06-15',
    activityQuantity: '100',
    activityUnit: 'MWh',
    electricityMwh: '100.000000000000000000',
    factorSourceMode: 'MANUAL',
    factorValue: '0.43900000',
    factorUnit: 'tCO2e/MWh',
    factorTco2ePerMwh: '0.439000000000000000',
    factorValueId: null,
    factorDefinitionId: 'def-1',
    factorSourceName: 'Org verified',
    factorSourceDocument: 'Supplier declaration',
    factorDatasetVersion: 'ORG-2024',
    factorReferenceDescription: 'Manual',
    factorEffectiveDate: '2024-01-01',
    factorValidFrom: null,
    factorValidUntil: null,
    exportedElectricityQuantity: '10',
    exportedElectricityUnit: 'MWh',
    exportedElectricityMwh: '10.000000000000000000',
    indirectEmissionsTco2e: '43.90000000',
    resultValue: '43.90000000',
    resultUnit: 'tCO2e',
    evidenceNotes: null,
    createdAt: '2024-06-20T10:00:00Z',
    createdByUserId: 'user-1',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamPurchasedElectricityComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
            currentRoles: signal(['organization_admin']),
          },
        },
      ],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(CbamPurchasedElectricityComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('bindingId', 'binding-1');
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
  });

  afterEach(() => {
    httpMock?.verify();
  });

  function flushDefaultFactorIfPending(
    body: CbamPurchasedElectricityFactorResolution = unresolvedDefault,
  ): void {
    const pending = httpMock.match((r) => r.url.includes('/purchased-electricity/factors/default'));
    pending.forEach((r) => r.flush(body));
  }

  function flushLoad(options?: {
    activities?: CbamActivityRecord[];
    readiness?: CbamPurchasedElectricityPeriodSummary;
    summary?: CbamPurchasedElectricityPeriodSummary;
    results?: CbamPurchasedElectricityResultSummary[];
    detail?: CbamPurchasedElectricityResultDetail | null;
  }): void {
    fixture.detectChanges();
    httpMock
      .expectOne((r) => r.url.includes('/activity-records'))
      .flush({
        items: options?.activities ?? [elecActivity, gasActivity],
        page: 1,
        pageSize: 100,
        totalItems: (options?.activities ?? [elecActivity, gasActivity]).length,
        totalPages: 1,
      });
    httpMock
      .expectOne(`${bindingBase}/purchased-electricity/readiness`)
      .flush(options?.readiness ?? readySummary);
    httpMock
      .expectOne(`${bindingBase}/purchased-electricity/summary`)
      .flush(options?.summary ?? readySummary);
    const results = options?.results ?? [resultSummary];
    httpMock
      .expectOne((r) => r.url.includes('/purchased-electricity/results') && !r.url.includes('/results/'))
      .flush({
        items: results,
        page: 1,
        pageSize: 10,
        totalItems: results.length,
        totalPages: 1,
      });
    const detail = options?.detail === undefined ? resultDetail : options.detail;
    if (detail && results.some((r) => r.isCurrent)) {
      httpMock
        .expectOne(`${bindingBase}/purchased-electricity/results/${detail.resultId}`)
        .flush(detail);
    }
    flushDefaultFactorIfPending();
    fixture.detectChanges();
  }

  it('shows empty activity state with Activities link', () => {
    flushLoad({
      activities: [gasActivity],
      readiness: emptySummary,
      summary: emptySummary,
      results: [],
      detail: null,
    });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('No electricity records are available.');
    expect(text).toContain('Go to Activities');
    expect(text).toContain('A verified Turkey default factor is not available yet.');
  });

  it('lists only eligible kWh/MWh electricity activities', () => {
    flushLoad({ activities: [elecActivity, gasActivity, kwhActivity], results: [], detail: null });
    expect(component.eligibleActivities().map((a) => a.id).sort()).toEqual(
      ['act-elec', 'act-kwh'].sort(),
    );
    expect(isEligibleElectricityActivity(gasActivity)).toBe(false);
    expect(isEligibleElectricityActivity(elecActivity)).toBe(true);
    expect(isEligibleElectricityActivity(kwhActivity)).toBe(true);
  });

  it('loads platform default from API and never substitutes 0.439 when unresolved', () => {
    flushLoad({ results: [], detail: null });
    component.form.controls.activityRecordId.setValue('act-elec');
    component.form.controls.factorSourceMode.setValue('PLATFORM_DEFAULT');
    fixture.detectChanges();
    httpMock
      .expectOne(`${bindingBase}/purchased-electricity/factors/default?referenceDate=2024-06-15`)
      .flush(unresolvedDefault);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('A verified default factor is not available');
    expect(text).not.toContain('0.439');
    expect(component.platformDefaultAvailable()).toBe(false);
  });

  it('shows resolved platform default values from API', () => {
    flushLoad({ results: [], detail: null });
    component.form.controls.activityRecordId.setValue('act-elec');
    component.form.controls.factorSourceMode.setValue('PLATFORM_DEFAULT');
    fixture.detectChanges();
    httpMock
      .expectOne(`${bindingBase}/purchased-electricity/factors/default?referenceDate=2024-06-15`)
      .flush(resolvedDefault);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('0.41000000');
    expect(text).toContain('tCO2e/MWh');
    expect(text).toContain('TEST_PLATFORM');
  });

  it('requires manual provenance before enabling calculate', () => {
    flushLoad({ results: [], detail: null });
    component.form.patchValue({
      activityRecordId: 'act-elec',
      factorSourceMode: 'MANUAL',
      manualValue: '0.439',
      manualUnit: 'tCO2e/MWh',
      sourceName: '',
      sourceDocument: '',
      datasetVersion: '',
      referenceDescription: '',
    });
    fixture.detectChanges();
    expect(component.canExecute()).toBe(false);
    component.form.patchValue({
      sourceName: 'Org',
      sourceDocument: 'Doc',
      datasetVersion: 'v1',
      referenceDescription: 'Ref',
    });
    fixture.detectChanges();
    expect(component.canExecute()).toBe(true);
  });

  it('preserves blank and zero Decimal string behavior without Number conversion', () => {
    expect(isBlankDecimalInput('')).toBe(true);
    expect(isBlankDecimalInput('  ')).toBe(true);
    expect(isBlankDecimalInput('0')).toBe(false);
    expect(isZeroDecimalString('0')).toBe(true);
    expect(isZeroDecimalString('0.000')).toBe(true);
    expect(isNegativeDecimalString('-1')).toBe(true);
    expect(formatDecimalDisplay('43.90000000')).toBe('43.90000000');
    expect(formatDecimalDisplay(null)).toBe('—');
  });

  it('does not compute emissions client-side; uses backend summary totals', () => {
    flushLoad();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('43.90000000');
    expect(text).toContain('tCO2e');
    expect(text).toContain('100.000000000000000000');
    expect(text).toContain('Exported electricity');
    // No local multiply helpers exposed
    expect((component as unknown as { calculateLocal?: unknown }).calculateLocal).toBeUndefined();
  });

  it('keeps exported electricity separate in execution payload', fakeAsync(() => {
    flushLoad({ results: [], detail: null });
    component.form.patchValue({
      activityRecordId: 'act-elec',
      factorSourceMode: 'MANUAL',
      manualValue: '0.439',
      manualUnit: 'tCO2e/MWh',
      sourceName: 'Org',
      sourceDocument: 'Doc',
      datasetVersion: 'v1',
      referenceDescription: 'Ref',
      exportedQuantity: '10',
      exportedUnit: 'MWh',
    });
    fixture.detectChanges();
    component.runCalculationAction();
    const req = httpMock.expectOne(`${bindingBase}/purchased-electricity/executions`);
    expect(req.request.body.exportedElectricityQuantity).toBe('10');
    expect(req.request.body.exportedElectricityUnit).toBe('MWh');
    expect(req.request.body.indirectEmissionsTco2e).toBeUndefined();
    req.flush({
      resultId: 'res-2',
      runId: 'run-2',
      status: 'COMPLETED',
      methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1',
      methodologyVersion: '1',
      activityRecordId: 'act-elec',
      electricityMwh: '100',
      factorSourceMode: 'MANUAL',
      factorValue: '0.439',
      factorUnit: 'tCO2e/MWh',
      indirectEmissionsTco2e: '43.9',
      resultUnit: 'tCO2e',
      exportedElectricityMwh: '10',
      clientRequestId: req.request.body.clientRequestId,
      idempotentReplay: false,
      createdAt: '2024-06-20T11:00:00Z',
    });
    tick();
    // refresh calls
    httpMock.expectOne((r) => r.url.includes('/activity-records')).flush({
      items: [elecActivity],
      page: 1,
      pageSize: 100,
      totalItems: 1,
      totalPages: 1,
    });
    httpMock.expectOne(`${bindingBase}/purchased-electricity/readiness`).flush(readySummary);
    httpMock.expectOne(`${bindingBase}/purchased-electricity/summary`).flush(readySummary);
    httpMock
      .expectOne((r) => r.url.includes('/purchased-electricity/results') && !r.url.includes('/results/'))
      .flush({
        items: [resultSummary],
        page: 1,
        pageSize: 10,
        totalItems: 1,
        totalPages: 1,
      });
    // detail from reload + explicit loadDetail
    const detailReqs = httpMock.match(`${bindingBase}/purchased-electricity/results/res-1`);
    detailReqs.forEach((r) => r.flush(resultDetail));
    const newDetail = httpMock.match(`${bindingBase}/purchased-electricity/results/res-2`);
    newDetail.forEach((r) =>
      r.flush({ ...resultDetail, resultId: 'res-2', exportedElectricityMwh: '10' }),
    );
  }));

  it('hides execution for view-only permissions', () => {
    fixture.componentRef.setInput('canConfigure', false);
    fixture.componentRef.setInput('canMutate', false);
    flushLoad({ results: [], detail: null });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('View only');
    expect(component.canExecute()).toBe(false);
  });

  it('reuses clientRequestId on transport retry and clears on IDEMPOTENCY_KEY_REUSED', fakeAsync(() => {
    flushLoad({ results: [], detail: null });
    component.form.patchValue({
      activityRecordId: 'act-elec',
      factorSourceMode: 'MANUAL',
      manualValue: '0.439',
      manualUnit: 'tCO2e/MWh',
      sourceName: 'Org',
      sourceDocument: 'Doc',
      datasetVersion: 'v1',
      referenceDescription: 'Ref',
    });
    const seeded = createClientRequestId();
    component.seedClientRequestIdForRetry(seeded);
    component.runCalculationAction();
    const first = httpMock.expectOne(`${bindingBase}/purchased-electricity/executions`);
    expect(first.request.body.clientRequestId).toBe(seeded);
    first.flush(
      {
        error: {
          code: 'IDEMPOTENCY_KEY_REUSED',
          message: 'conflict',
          details: [{ code: 'IDEMPOTENCY_KEY_REUSED' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    tick();
    expect(component.peekClientRequestId()).toBeNull();
    expect(component.actionError()).toContain('Start a new calculation');
  }));

  it('preserves last successful detail when recalculation fails', fakeAsync(() => {
    flushLoad();
    expect(component.selectedDetail()?.resultId).toBe('res-1');
    component.form.patchValue({
      activityRecordId: 'act-elec',
      factorSourceMode: 'MANUAL',
      manualValue: '0.5',
      manualUnit: 'tCO2e/MWh',
      sourceName: 'Org',
      sourceDocument: 'Doc',
      datasetVersion: 'v1',
      referenceDescription: 'Ref',
    });
    component.runCalculationAction();
    httpMock
      .expectOne(`${bindingBase}/purchased-electricity/executions`)
      .flush(
        {
          error: {
            code: 'UNRESOLVED_PLATFORM_DEFAULT',
            message: 'fail',
            details: [{ code: 'MISSING_FACTOR' }],
          },
        },
        { status: 400, statusText: 'Bad Request' },
      );
    tick();
    expect(component.selectedDetail()?.resultId).toBe('res-1');
    expect(component.summary()?.totalIndirectEmissionsTco2e).toBe('43.90000000');
  }));

  it('loads immutable detail without calling live factor default endpoint', () => {
    flushLoad();
    const pending = httpMock.match(() => true);
    expect(pending.filter((r) => r.request.url.includes('/factors/default')).length).toBe(0);
    expect(component.selectedDetail()?.factorSourceName).toBe('Org verified');
  });

  it('maps unknown error codes to fallback message', () => {
    const msg = mapPurchasedElectricityError(
      new HttpErrorResponse({
        status: 500,
        error: { error: { code: 'SOMETHING_WEIRD', message: 'internal sql boom' } },
      }),
    );
    expect(msg.toLowerCase()).not.toContain('sql');
    expect(mapElectricityIssueCode('UNKNOWN_CODE')).toBe('More information is needed.');
    expect(mapElectricityInfoCode('TURKEY_ELECTRICITY_DEFAULT_FACTOR_PROVENANCE_MISSING')).toContain(
      'Turkey default factor',
    );
    expect(mapResultLifecycleLabel(true, true)).toBe('Out of date');
  });

  it('shows current/history/stale labels from backend flags', () => {
    flushLoad({
      results: [
        resultSummary,
        {
          ...resultSummary,
          resultId: 'res-old',
          isCurrent: false,
          isStale: false,
          createdAt: '2024-06-19T10:00:00Z',
        },
        {
          ...resultSummary,
          resultId: 'res-stale',
          isCurrent: true,
          isStale: true,
          staleReasonCodes: ['ACTIVITY_INPUT_CHANGED'],
        },
      ],
    });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Current');
    expect(text).toContain('History');
    expect(text).toContain('Out of date');
  });
});

describe('purchased-electricity util eligibility', () => {
  it('rejects mass and fuel-volume activities', () => {
    const mass: CbamActivityRecord = {
      id: '1',
      organizationId: 'o',
      reportingPeriodBindingId: 'b',
      installationProfileId: 'i',
      activityGroup: 'FUEL',
      activityType: 'ELECTRICITY',
      activityDate: '2024-01-01',
      quantity: '10',
      unit: 'kg',
      dataSourceType: 'PRIMARY',
      sourceReference: null,
      notes: null,
      status: 'active',
      rowVersion: 1,
    };
    expect(isEligibleElectricityActivity(mass)).toBe(false);
  });
});
