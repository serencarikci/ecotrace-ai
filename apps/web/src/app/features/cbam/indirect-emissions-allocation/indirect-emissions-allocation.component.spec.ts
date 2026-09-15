import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamIndirectEmissionsAllocationPeriodSummary,
  CbamIndirectEmissionsAllocationReadiness,
  CbamIndirectEmissionsAllocationResultDetail,
  CbamIndirectEmissionsAllocationResultSummary,
} from '../cbam-api.service';
import { CbamIndirectEmissionsAllocationComponent } from './indirect-emissions-allocation.component';
import {
  createClientRequestId,
  formatDecimalDisplay,
  mapAllocationError,
  mapAllocationIssueCode,
  mapAllocationStaleReason,
  mapBalanceStatusLabel,
  mapExecutionStatusLabel,
  mapResultLifecycleLabel,
} from './indirect-emissions-allocation.util';

describe('CbamIndirectEmissionsAllocationComponent', () => {
  let fixture: ComponentFixture<CbamIndirectEmissionsAllocationComponent>;
  let component: CbamIndirectEmissionsAllocationComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const bindingBase = `${orgBase}/reporting-period-bindings/binding-1/indirect-emissions-allocation`;

  const notReady: CbamIndirectEmissionsAllocationReadiness = {
    status: 'NOT_READY',
    allocationReady: false,
    blockingIssueCodes: ['INDIRECT_EMISSIONS_NOT_READY', 'MONTHLY_PRODUCTION_BASIS_NOT_READY'],
    purchasedElectricityStatus: 'INCOMPLETE',
    monthlyProductionBasisStatus: 'INCOMPLETE',
    productionProfileStatus: 'NOT_READY',
    productionReconciliationStatus: 'UNAVAILABLE',
    sourceResultCount: 0,
    monthCount: 12,
    participatingProductionRecordCount: 0,
    productProfileGroupCount: 0,
    currentAllocationId: null,
    currentAllocationStale: false,
    staleReasonCodes: [],
  };

  const ready: CbamIndirectEmissionsAllocationReadiness = {
    ...notReady,
    status: 'READY',
    allocationReady: true,
    blockingIssueCodes: [],
    purchasedElectricityStatus: 'READY',
    monthlyProductionBasisStatus: 'READY',
    productionProfileStatus: 'READY',
    productionReconciliationStatus: 'EXACT_MATCH',
    sourceResultCount: 3,
    participatingProductionRecordCount: 3,
    productProfileGroupCount: 2,
  };

  const emptySummary: CbamIndirectEmissionsAllocationPeriodSummary = {
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1',
    currentResultId: null,
    currentIsStale: false,
    staleReasonCodes: [],
    facilityElectricityMwh: null,
    cbamElectricityMwh: null,
    nonCbamElectricityMwh: null,
    allocatedElectricityMwh: null,
    remainingElectricityMwh: null,
    facilityIndirectEmissionsTco2e: null,
    cbamIndirectEmissionsTco2e: null,
    allocatedIndirectEmissionsTco2e: null,
    remainingIndirectEmissionsTco2e: null,
    exportedElectricityMwh: null,
    electricityUnit: 'MWh',
    emissionsUnit: 'tCO2e',
    balanceStatus: null,
    totalsByMonth: {},
    totalsByProductProfile: [],
  };

  const currentSummary: CbamIndirectEmissionsAllocationPeriodSummary = {
    ...emptySummary,
    currentResultId: 'res-1',
    currentIsStale: false,
    facilityElectricityMwh: '501.76628000',
    cbamElectricityMwh: '41.29445720',
    nonCbamElectricityMwh: '460.47182280',
    allocatedElectricityMwh: '41.29445720',
    remainingElectricityMwh: '0.00000000',
    facilityIndirectEmissionsTco2e: '220.27539692',
    cbamIndirectEmissionsTco2e: '18.12826671',
    allocatedIndirectEmissionsTco2e: '18.12826671',
    remainingIndirectEmissionsTco2e: '0.00000000',
    exportedElectricityMwh: '5.00000000',
    balanceStatus: 'BALANCED',
  };

  const resultRow: CbamIndirectEmissionsAllocationResultSummary = {
    resultId: 'res-1',
    runId: 'res-1',
    methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1',
    methodologyVersion: '1.0.0',
    status: 'COMPLETED',
    balanceStatus: 'BALANCED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    facilityElectricityMwh: '501.76628000',
    cbamElectricityMwh: '41.29445720',
    nonCbamElectricityMwh: '460.47182280',
    allocatedElectricityMwh: '41.29445720',
    remainingElectricityMwh: '0.00000000',
    facilityIndirectEmissionsTco2e: '220.27539692',
    cbamIndirectEmissionsTco2e: '18.12826671',
    allocatedIndirectEmissionsTco2e: '18.12826671',
    remainingIndirectEmissionsTco2e: '0.00000000',
    exportedElectricityMwh: '5.00000000',
    electricityUnit: 'MWh',
    emissionsUnit: 'tCO2e',
    createdAt: '2024-06-01T10:00:00Z',
  };

  const detail: CbamIndirectEmissionsAllocationResultDetail = {
    resultId: 'res-1',
    runId: 'res-1',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1',
    methodologyVersion: '1.0.0',
    workbookFilename: 'SKDM_Alokasyon_Sablon.xlsx',
    workbookSha256: '62300e30193aa2e696d07977697833431dcf782684cf61cace4e7e5f524cef72',
    workbookFormulaRefs: 'C9=IF(D3=0,0,(E3/D3)*(B3/1000))',
    clientRequestId: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
    requestFingerprint: 'fp',
    status: 'COMPLETED',
    balanceStatus: 'BALANCED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    facilityElectricityMwhRaw: '501.766280000000000000',
    cbamElectricityMwhRaw: '41.294457198595287166',
    nonCbamElectricityMwhRaw: '460.471822801404712834',
    facilityElectricityMwh: '501.76628000',
    cbamElectricityMwh: '41.29445720',
    nonCbamElectricityMwh: '460.47182280',
    allocatedElectricityMwh: '41.29445720',
    remainingElectricityMwh: '0.00000000',
    facilityIndirectEmissionsTco2eRaw: '220.275396920000000000',
    cbamIndirectEmissionsTco2eRaw: '18.128266710183331066',
    nonCbamIndirectEmissionsTco2eRaw: '202.147130209816668934',
    facilityIndirectEmissionsTco2e: '220.27539692',
    cbamIndirectEmissionsTco2e: '18.12826671',
    nonCbamIndirectEmissionsTco2e: '202.14713021',
    allocatedIndirectEmissionsTco2e: '18.12826671',
    remainingIndirectEmissionsTco2e: '0.00000000',
    exportedElectricityMwh: '5.00000000',
    electricityUnit: 'MWh',
    emissionsUnit: 'tCO2e',
    sourceResultCount: 1,
    monthCount: 1,
    participatingProductionRecordCount: 1,
    productProfileGroupCount: 1,
    totalsByMonth: {
      '2024-07-01': {
        cbamElectricityMwh: '15.68171195',
        cbamIndirectEmissionsTco2e: '6.88427154',
      },
    },
    monthlyBasis: [
      {
        monthStart: '2024-07-01',
        basisRecordId: 'mb-1',
        basisRowVersion: 1,
        totalProductionQuantity: '506',
        cbamQuantity: '39.34',
        quantityUnit: 't',
        normalizedTotalProductionTonnes: '506',
        normalizedCbamQuantityTonnes: '39.34',
        monthlyShareRaw: '0.07774703557312252964',
      },
    ],
    sources: [
      {
        sourceResultId: 'pe-1',
        activityRecordId: 'act-1',
        activityDate: '2024-07-15',
        monthStart: '2024-07-01',
        activityQuantity: '176034.53',
        activityUnit: 'kWh',
        electricityMwh: '176.03453',
        factorSourceMode: 'MANUAL',
        factorValue: '0.439',
        factorUnit: 'tCO2e/MWh',
        factorTco2ePerMwh: '0.439',
        factorSourceName: 'Workbook H4',
        factorSourceDocument: null,
        factorDatasetVersion: null,
        factorReferenceDescription: null,
        monthlyShareRaw: '0.07774703557312252964',
        facilityElectricityMwh: '176.03453',
        cbamElectricityMwh: '13.685',
        nonCbamElectricityMwh: '162.34953',
        facilityIndirectEmissionsTco2e: '77.27915867',
        cbamIndirectEmissionsTco2e: '6.007715',
        nonCbamIndirectEmissionsTco2e: '71.27144367',
        exportedElectricityMwh: '5.00000000',
      },
    ],
    products: [
      {
        productId: 'prod-1',
        productProfileVersionId: 'ppv-1',
        profileVersion: 1,
        cnNormalizedCode: '73181595',
        cnDisplayCode: '7318 15 95',
        productName: 'Screws',
        productionRecordIds: ['pr-1'],
        productionQuantitySnapshots: [],
        normalizedQuantityTonnes: '39.34',
        denominatorTonnes: '103.59',
        rawShare: '0.379766',
        rawAllocatedElectricityMwh: '15.68224680',
        finalAllocatedElectricityMwh: '15.68224680',
        electricityRoundingAdjustment: '0.00000000',
        rawAllocatedIndirectEmissionsTco2e: '6.88450635',
        finalAllocatedIndirectEmissionsTco2e: '6.88450635',
        emissionsRoundingAdjustment: '0.00000000',
        electricityUnit: 'MWh',
        emissionsUnit: 'tCO2e',
      },
    ],
    createdAt: '2024-06-01T10:00:00Z',
    createdByUserId: 'user-1',
  };

  function executionBody(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1',
      methodologyVersion: '1.0.0',
      balanceStatus: 'BALANCED',
      facilityElectricityMwh: '501.76628000',
      cbamElectricityMwh: '41.29445720',
      nonCbamElectricityMwh: '460.47182280',
      allocatedElectricityMwh: '41.29445720',
      remainingElectricityMwh: '0.00000000',
      facilityIndirectEmissionsTco2e: '220.27539692',
      cbamIndirectEmissionsTco2e: '18.12826671',
      nonCbamIndirectEmissionsTco2e: '202.14713021',
      allocatedIndirectEmissionsTco2e: '18.12826671',
      remainingIndirectEmissionsTco2e: '0.00000000',
      exportedElectricityMwh: '5.00000000',
      electricityUnit: 'MWh',
      emissionsUnit: 'tCO2e',
      clientRequestId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
      ...overrides,
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamIndirectEmissionsAllocationComponent],
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
    fixture = TestBed.createComponent(CbamIndirectEmissionsAllocationComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('bindingId', 'binding-1');
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushLoad(options?: {
    readiness?: CbamIndirectEmissionsAllocationReadiness;
    summary?: CbamIndirectEmissionsAllocationPeriodSummary;
    results?: CbamIndirectEmissionsAllocationResultSummary[];
    detail?: CbamIndirectEmissionsAllocationResultDetail | null;
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
    expect(mapAllocationIssueCode('INDIRECT_EMISSIONS_NOT_READY')).toContain('electricity');
    expect(mapAllocationIssueCode('UNKNOWN_CODE_XYZ')).toBe('More information is needed.');
    expect(mapAllocationStaleReason('UNKNOWN')).toBe('Some source data has changed.');
    expect(mapResultLifecycleLabel(true, true)).toBe('Out of date');
    expect(mapBalanceStatusLabel('BALANCED')).toBe('Balanced');
    expect(mapExecutionStatusLabel('COMPLETED')).toBe('Completed');
    expect(formatDecimalDisplay('41.29445720')).toBe('41.29445720');
  });

  it('maps API errors without raw backend text', () => {
    const err = new HttpErrorResponse({
      status: 409,
      error: {
        error: {
          code: 'INDIRECT_EMISSIONS_STALE',
          message: 'SQL DETAIL: relation foo',
          details: [{ code: 'INDIRECT_EMISSIONS_STALE' }],
        },
      },
    });
    expect(mapAllocationError(err)).toBe('Update the out-of-date electricity calculations.');
    expect(mapAllocationError(err)).not.toContain('SQL');
    expect(
      mapAllocationError(new HttpErrorResponse({ status: 403, error: {} })),
    ).toContain('permission');
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
    expect(text).toContain('Complete the electricity calculations.');
    expect(text).toContain('Enter monthly production data.');

    const btn = fixture.debugElement.query(
      By.css('button[aria-label="Calculate allocation"]'),
    );
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
    first.flush({ error: { code: 'NETWORK' } }, { status: 0, statusText: 'Unknown Error' });
    tick();
    expect(component.peekClientRequestId()).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');

    component.executeAllocation();
    const retry = httpMock.expectOne(`${bindingBase}/executions`);
    expect(retry.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    retry.flush(executionBody());
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
    again.flush(executionBody({ resultId: 'res-2', clientRequestId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' }));
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
    httpMock
      .expectOne(`${bindingBase}/executions`)
      .flush(executionBody({ clientRequestId: 'cccccccc-cccc-cccc-cccc-cccccccccccc', idempotentReplay: true }));
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
  }));

  it('success refreshes readiness, summary, list and detail with tCO2e and exported electricity', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({ readiness: ready });
    tick();

    component.executeAllocation();
    httpMock.expectOne(`${bindingBase}/executions`).flush(executionBody());
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('41.29445720');
    expect(text).toContain('18.12826671');
    expect(text).toContain('tCO2e');
    expect(text).not.toMatch(/\btCO2\b(?!e)/);
    expect(text).toContain('Exported electricity is reported separately');
    expect(text).toContain('5.00000000');
    expect(component.selectedDetail()?.sources[0].activityUnit).toBe('kWh');
    expect(component.selectedDetail()?.products[0].productName).toBe('Screws');
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
    expect(fixture.nativeElement.textContent).toContain('41.29445720');

    component.executeAllocation();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      {
        error: {
          code: 'INDIRECT_EMISSIONS_STALE',
          details: [{ code: 'INDIRECT_EMISSIONS_STALE' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('41.29445720');
    expect(component.summary()?.currentResultId).toBe('res-1');
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
    expect(component.executeButtonLabel()).toBe('Update allocation');
  }));

  it('displays immutable monthly/source/product detail without live catalogs', fakeAsync(() => {
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentAllocationId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    component.toggleSection('monthly');
    component.toggleSection('sources');
    component.toggleSection('products');
    component.toggleSection('exported');
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('July 2024');
    expect(text).toContain('kWh');
    expect(text).toContain('7318 15 95');
    expect(text).toContain('6.88450635');
    expect(text).toContain('Exported electricity is reported separately');

    const pending = httpMock.match(() => true);
    expect(pending.filter((r) => r.request.url.includes('/cn-codes')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/product-profile')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/purchased-electricity/factors')).length).toBe(0);
  }));

  it('createClientRequestId returns a UUID-like string', () => {
    expect(createClientRequestId()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });
});
