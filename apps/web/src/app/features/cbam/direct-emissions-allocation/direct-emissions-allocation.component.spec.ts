import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamDirectEmissionsAllocationPeriodSummary,
  CbamDirectEmissionsAllocationReadiness,
  CbamDirectEmissionsAllocationResultDetail,
  CbamDirectEmissionsAllocationResultSummary,
} from '../cbam-api.service';
import { CbamDirectEmissionsAllocationComponent } from './direct-emissions-allocation.component';
import {
  createClientRequestId,
  formatDecimalDisplay,
  mapAllocationError,
  mapAllocationIssueCode,
  mapAllocationStaleReason,
  mapBalanceStatusLabel,
  mapExecutionStatusLabel,
  mapResultLifecycleLabel,
} from './direct-emissions-allocation.util';

describe('CbamDirectEmissionsAllocationComponent', () => {
  let fixture: ComponentFixture<CbamDirectEmissionsAllocationComponent>;
  let component: CbamDirectEmissionsAllocationComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const bindingBase = `${orgBase}/reporting-period-bindings/binding-1/direct-emissions-allocation`;

  const notReady: CbamDirectEmissionsAllocationReadiness = {
    status: 'NOT_READY',
    allocationReady: false,
    blockingIssueCodes: ['DIRECT_EMISSIONS_NOT_READY', 'MONTHLY_PRODUCTION_BASIS_NOT_READY'],
    stationaryCombustionStatus: 'INCOMPLETE',
    monthlyProductionBasisStatus: 'INCOMPLETE',
    productionProfileStatus: 'NOT_READY',
    productionReconciliationStatus: 'UNAVAILABLE',
    sourceResultCount: 0,
    monthCount: 12,
    fuelCount: 0,
    participatingProductionRecordCount: 0,
    productProfileGroupCount: 0,
    currentAllocationId: null,
    currentAllocationStale: false,
    staleReasonCodes: [],
  };

  const ready: CbamDirectEmissionsAllocationReadiness = {
    ...notReady,
    status: 'READY',
    allocationReady: true,
    blockingIssueCodes: [],
    stationaryCombustionStatus: 'READY',
    monthlyProductionBasisStatus: 'READY',
    productionProfileStatus: 'READY',
    productionReconciliationStatus: 'EXACT_MATCH',
    sourceResultCount: 2,
    fuelCount: 1,
    participatingProductionRecordCount: 3,
    productProfileGroupCount: 2,
  };

  const emptySummary: CbamDirectEmissionsAllocationPeriodSummary = {
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
    currentResultId: null,
    currentIsStale: false,
    staleReasonCodes: [],
    facilityFossilCo2Tonnes: null,
    cbamFossilCo2Tonnes: null,
    nonCbamFossilCo2Tonnes: null,
    allocatedFossilCo2Tonnes: null,
    remainingFossilCo2Tonnes: null,
    resultUnit: 'tCO2',
    workbookReportingUnit: 'tCO2e',
    balanceStatus: null,
    totalsByMonth: {},
    totalsByFuel: {},
    totalsByProductProfile: [],
  };

  const currentSummary: CbamDirectEmissionsAllocationPeriodSummary = {
    ...emptySummary,
    currentResultId: 'res-1',
    currentIsStale: false,
    facilityFossilCo2Tonnes: '1.576580544',
    cbamFossilCo2Tonnes: '0.14240957',
    nonCbamFossilCo2Tonnes: '1.434170974',
    allocatedFossilCo2Tonnes: '0.14240957',
    remainingFossilCo2Tonnes: '0.00000000',
    balanceStatus: 'BALANCED',
  };

  const resultRow: CbamDirectEmissionsAllocationResultSummary = {
    resultId: 'res-1',
    runId: 'res-1',
    methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
    methodologyVersion: '1',
    status: 'COMPLETED',
    balanceStatus: 'BALANCED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    facilityFossilCo2Tonnes: '1.576580544',
    cbamFossilCo2Tonnes: '0.14240957',
    nonCbamFossilCo2Tonnes: '1.434170974',
    allocatedFossilCo2Tonnes: '0.14240957',
    remainingFossilCo2Tonnes: '0.00000000',
    resultUnit: 'tCO2',
    workbookReportingUnit: 'tCO2e',
    createdAt: '2024-06-01T10:00:00Z',
  };

  const detail: CbamDirectEmissionsAllocationResultDetail = {
    resultId: 'res-1',
    runId: 'res-1',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
    methodologyVersion: '1',
    workbookFilename: 'SKDM.xlsx',
    workbookSha256: 'abc',
    workbookFormulaRefs: 'D/E',
    clientRequestId: '11111111-1111-1111-1111-111111111111',
    requestFingerprint: 'fp',
    status: 'COMPLETED',
    balanceStatus: 'BALANCED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    facilityFossilCo2TonnesRaw: '1.576580544',
    cbamFossilCo2TonnesRaw: '0.14240957',
    nonCbamFossilCo2TonnesRaw: '1.434170974',
    facilityFossilCo2Tonnes: '1.576580544',
    cbamFossilCo2Tonnes: '0.14240957',
    nonCbamFossilCo2Tonnes: '1.434170974',
    allocatedFossilCo2Tonnes: '0.14240957',
    remainingFossilCo2Tonnes: '0.00000000',
    resultUnit: 'tCO2',
    workbookReportingUnit: 'tCO2e',
    workbookGas: 'CO2',
    workbookGwp: '1',
    workbookGwpFactor: '1',
    totalsByMonth: { '2024-01-01': '0.05000000' },
    totalsByFuel: {},
    monthlyBasis: [
      {
        basisRecordId: 'mb-1',
        basisRowVersion: 1,
        monthStart: '2024-01-01',
        totalProductionQuantity: '100',
        cbamQuantity: '40',
        quantityUnit: 't',
        normalizedTotalProductionTonnes: '100',
        normalizedCbamQuantityTonnes: '40',
        monthlyShareRaw: '0.4',
      },
    ],
    sourceCalculations: [
      {
        sourceResultId: 'sc-1',
        sourceRunId: 'sc-1',
        activityRecordId: 'act-1',
        activityDate: '2024-01-15',
        monthStart: '2024-01-01',
        fuelCode: 'NATURAL_GAS',
        fuelName: 'Natural gas',
        datasetCode: 'IPCC',
        datasetVersion: '2006',
        activityQuantity: '1000',
        activityUnit: 'Sm3',
        facilityFossilCo2Tonnes: '1.00000000',
        cbamFossilCo2Tonnes: '0.40000000',
        nonCbamFossilCo2Tonnes: '0.60000000',
        monthlyShareRaw: '0.4',
        facilityFuelMassKg: '680',
        cbamFuelMassKg: '272',
        facilityEnergyContentTj: '0.03',
        cbamEnergyContentTj: '0.012',
      },
    ],
    productAllocations: [
      {
        productId: 'prod-1',
        productProfileVersionId: 'ppv-1',
        profileVersion: 1,
        cnNormalizedCode: '73181542',
        cnDisplayCode: '7318 15 42',
        productName: 'Screws',
        productionRecordIds: ['pr-1'],
        productionQuantitySnapshots: [],
        normalizedQuantityTonnes: '10',
        denominatorTonnes: '20',
        rawShare: '0.5',
        rawAllocatedFossilCo2Tonnes: '0.071204785',
        finalAllocatedFossilCo2Tonnes: '0.07120479',
        roundingAdjustment: '0.000000005',
        resultUnit: 'tCO2',
      },
    ],
    createdAt: '2024-06-01T10:00:00Z',
    createdByUserId: 'user-1',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamDirectEmissionsAllocationComponent],
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
    fixture = TestBed.createComponent(CbamDirectEmissionsAllocationComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('bindingId', 'binding-1');
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushLoad(options?: {
    readiness?: CbamDirectEmissionsAllocationReadiness;
    summary?: CbamDirectEmissionsAllocationPeriodSummary;
    results?: CbamDirectEmissionsAllocationResultSummary[];
    detail?: CbamDirectEmissionsAllocationResultDetail | null;
  }): void {
    const readiness = options?.readiness ?? notReady;
    const summary = options?.summary ?? emptySummary;
    const results = options?.results ?? [];
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readiness);
    httpMock.expectOne(`${bindingBase}/summary`).flush(summary);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/results`) && r.method === 'GET')
      .flush({
        items: results,
        page: 1,
        pageSize: 10,
        totalItems: results.length,
        totalPages: 1,
      });
    const currentId = readiness.currentAllocationId ?? results.find((r) => r.isCurrent)?.resultId;
    if (currentId && options?.detail !== null) {
      httpMock
        .expectOne(`${bindingBase}/results/${currentId}`)
        .flush(options?.detail ?? { ...detail, resultId: currentId });
    }
    fixture.detectChanges();
  }

  it('maps issue codes and unknown fallback', () => {
    expect(mapAllocationIssueCode('DIRECT_EMISSIONS_NOT_READY')).toContain('direct emissions');
    expect(mapAllocationIssueCode('UNKNOWN_CODE_XYZ')).toBe('More information is needed.');
    expect(mapAllocationStaleReason('UNKNOWN')).toBe('Some source data has changed.');
    expect(mapResultLifecycleLabel(true, true)).toBe('Out of date');
    expect(mapResultLifecycleLabel(true, false)).toBe('Current');
    expect(mapResultLifecycleLabel(false, false)).toBe('History');
    expect(mapBalanceStatusLabel('BALANCED')).toBe('Balanced');
    expect(mapBalanceStatusLabel('UNBALANCED')).toBe('Not balanced');
    expect(mapExecutionStatusLabel('COMPLETED')).toBe('Completed');
    expect(mapExecutionStatusLabel('FAILED')).toBe('Failed');
    expect(formatDecimalDisplay('0.14240957')).toBe('0.14240957');
    expect(formatDecimalDisplay('9007199254740993')).toBe('9007199254740993');
  });

  it('maps API errors without raw backend text', () => {
    const err = new HttpErrorResponse({
      status: 409,
      error: {
        error: {
          code: 'DIRECT_EMISSIONS_STALE',
          message: 'SQL DETAIL: relation foo',
          details: [{ code: 'DIRECT_EMISSIONS_STALE' }],
        },
      },
    });
    expect(mapAllocationError(err)).toBe('Update the out-of-date direct emissions.');
    expect(mapAllocationError(err)).not.toContain('SQL');
    expect(
      mapAllocationError(new HttpErrorResponse({ status: 403, error: {} })),
    ).toContain('permission');
    expect(
      mapAllocationError(new HttpErrorResponse({ status: 404, error: {} })),
    ).toContain('not found');
    expect(
      mapAllocationError(
        new HttpErrorResponse({
          status: 409,
          error: { error: { code: 'IDEMPOTENCY_KEY_REUSED' } },
        }),
      ),
    ).toContain('Try again');
  });

  it('uses backend readiness to control the UI and blocks execution', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad();
    tick();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Not ready');
    expect(text).toContain('Complete the required data before allocation.');
    expect(text).toContain('Complete the direct emissions calculations.');
    expect(text).toContain('Enter monthly production data.');

    const btn = fixture.debugElement.query(
      By.css('button[aria-label="Calculate allocation"]'),
    );
    expect(btn).toBeTruthy();
    expect(btn.nativeElement.disabled).toBe(true);
    expect(component.canExecute()).toBe(false);
  }));

  it('view-only user cannot execute', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', false);
    fixture.componentRef.setInput('canMutate', false);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button[aria-label="Calculate allocation"]'))).toBeNull();
    expect(component.canExecute()).toBe(false);
  }));

  it('configure user can execute when ready', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();
    fixture.detectChanges();

    const btn = fixture.debugElement.query(
      By.css('button[aria-label="Calculate allocation"]'),
    );
    expect(btn.nativeElement.disabled).toBe(false);
    expect(component.canExecute()).toBe(true);
  }));

  it('reuses clientRequestId on transport retry and creates a new ID for recalculation', fakeAsync(() => {
    spyOn(crypto, 'randomUUID').and.returnValues(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    );
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();
    fixture.detectChanges();

    component.executeAllocation();
    const first = httpMock.expectOne(`${bindingBase}/executions`);
    expect(first.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    first.flush(
      { error: { code: 'NETWORK' } },
      { status: 0, statusText: 'Unknown Error' },
    );
    tick();
    expect(component.peekClientRequestId()).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');

    component.executeAllocation();
    const retry = httpMock.expectOne(`${bindingBase}/executions`);
    expect(retry.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    retry.flush({
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
      methodologyVersion: '1',
      balanceStatus: 'BALANCED',
      facilityFossilCo2Tonnes: '1.576580544',
      cbamFossilCo2Tonnes: '0.14240957',
      nonCbamFossilCo2Tonnes: '1.434170974',
      allocatedFossilCo2Tonnes: '0.14240957',
      remainingFossilCo2Tonnes: '0.00000000',
      resultUnit: 'tCO2',
      workbookReportingUnit: 'tCO2e',
      clientRequestId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    expect(component.executeButtonLabel()).toBe('Calculate again');
    component.executeAllocation();
    const again = httpMock.expectOne(`${bindingBase}/executions`);
    expect(again.request.body.clientRequestId).toBe('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');
    again.flush({
      resultId: 'res-2',
      runId: 'res-2',
      status: 'COMPLETED',
      methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
      methodologyVersion: '1',
      balanceStatus: 'BALANCED',
      facilityFossilCo2Tonnes: '1.576580544',
      cbamFossilCo2Tonnes: '0.14240957',
      nonCbamFossilCo2Tonnes: '1.434170974',
      allocatedFossilCo2Tonnes: '0.14240957',
      remainingFossilCo2Tonnes: '0.00000000',
      resultUnit: 'tCO2',
      workbookReportingUnit: 'tCO2e',
      clientRequestId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      idempotentReplay: false,
      createdAt: '2024-06-02T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-2' },
      summary: { ...currentSummary, currentResultId: 'res-2' },
      results: [{ ...resultRow, resultId: 'res-2' }],
      detail: { ...detail, resultId: 'res-2' },
    });
    tick();
  }));

  it('idempotent replay does not invent a second history row on the client', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();

    component.seedClientRequestIdForRetry('cccccccc-cccc-cccc-cccc-cccccccccccc');
    component.executeAllocation();
    httpMock.expectOne(`${bindingBase}/executions`).flush({
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
      methodologyVersion: '1',
      balanceStatus: 'BALANCED',
      facilityFossilCo2Tonnes: '1.576580544',
      cbamFossilCo2Tonnes: '0.14240957',
      nonCbamFossilCo2Tonnes: '1.434170974',
      allocatedFossilCo2Tonnes: '0.14240957',
      remainingFossilCo2Tonnes: '0.00000000',
      resultUnit: 'tCO2',
      workbookReportingUnit: 'tCO2e',
      clientRequestId: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
      idempotentReplay: true,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('already completed');
    expect(component.results().length).toBe(1);
  }));

  it('clears stale clientRequestId on IDEMPOTENCY_KEY_REUSED', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();

    component.seedClientRequestIdForRetry('dddddddd-dddd-dddd-dddd-dddddddddddd');
    component.executeAllocation();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      {
        error: {
          code: 'IDEMPOTENCY_KEY_REUSED',
          details: [{ code: 'IDEMPOTENCY_KEY_REUSED' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    tick();
    expect(component.peekClientRequestId()).toBeNull();
    expect(component.actionError()).toContain('Try again');
  }));

  it('success refreshes readiness, summary, list and detail', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();

    component.executeAllocation();
    httpMock.expectOne(`${bindingBase}/executions`).flush({
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1',
      methodologyVersion: '1',
      balanceStatus: 'BALANCED',
      facilityFossilCo2Tonnes: '1.576580544',
      cbamFossilCo2Tonnes: '0.14240957',
      nonCbamFossilCo2Tonnes: '1.434170974',
      allocatedFossilCo2Tonnes: '0.14240957',
      remainingFossilCo2Tonnes: '0.00000000',
      resultUnit: 'tCO2',
      workbookReportingUnit: 'tCO2e',
      clientRequestId: createClientRequestId(),
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('0.14240957');
    expect(text).toContain('Ready');
    expect(text).toContain('Current');
    expect(component.selectedDetail()?.sourceCalculations[0].fuelName).toBe('Natural gas');
    expect(component.selectedDetail()?.productAllocations[0].productName).toBe('Screws');
  }));

  it('failure preserves the last successful result', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('0.14240957');

    component.executeAllocation();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      {
        error: {
          code: 'DIRECT_EMISSIONS_STALE',
          details: [{ code: 'DIRECT_EMISSIONS_STALE' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('0.14240957');
    expect(component.summary()?.currentResultId).toBe('res-1');
    expect(component.selectedDetail()?.resultId).toBe('res-1');
  }));

  it('shows Update allocation CTA when current result is stale', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({
      readiness: {
        ...ready,
        currentAllocationId: 'res-1',
        currentAllocationStale: true,
        staleReasonCodes: ['MONTHLY_PRODUCTION_BASIS_CHANGED'],
      },
      summary: {
        ...currentSummary,
        currentIsStale: true,
        staleReasonCodes: ['MONTHLY_PRODUCTION_BASIS_CHANGED'],
      },
      results: [{ ...resultRow, isStale: true }],
      detail: { ...detail, isStale: true, staleReasonCodes: ['MONTHLY_PRODUCTION_BASIS_CHANGED'] },
    });
    tick();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Update allocation');
    expect(text).toContain('The source data changed after this allocation.');
    expect(text).toContain('Out of date');
    expect(component.executeButtonLabel()).toBe('Update allocation');
  }));

  it('displays snapshot detail without calling live catalog APIs', fakeAsync(() => {
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    component.toggleSection('monthly');
    component.toggleSection('fuels');
    component.toggleSection('products');
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('January 2024');
    expect(text).toContain('Natural gas');
    expect(text).toContain('7318 15 42');
    expect(text).toContain('0.07120479');

    const pending = httpMock.match(() => true);
    expect(pending.filter((r) => r.request.url.includes('/stationary-combustion/fuels')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/cn-codes')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/product-profiles')).length).toBe(0);
  }));

  it('respects writable-period rules', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', false);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('not writable');
    expect(component.canExecute()).toBe(false);
  }));

  it('createClientRequestId returns a UUID-like string', () => {
    expect(createClientRequestId()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });
});
