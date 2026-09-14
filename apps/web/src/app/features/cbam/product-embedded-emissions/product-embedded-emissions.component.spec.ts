import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamProductEmbeddedEmissionsPeriodSummary,
  CbamProductEmbeddedEmissionsProductRow,
  CbamProductEmbeddedEmissionsReadiness,
  CbamProductEmbeddedEmissionsResultDetail,
  CbamProductEmbeddedEmissionsResultSummary,
} from '../cbam-api.service';
import { CbamProductEmbeddedEmissionsComponent } from './product-embedded-emissions.component';
import {
  createClientRequestId,
  formatDecimalDisplay,
  mapPeeError,
  mapPeeIssueCode,
  mapPeeStaleReason,
  mapResultLifecycleLabel,
  mapMethodologyLabel,
} from './product-embedded-emissions.util';

describe('CbamProductEmbeddedEmissionsComponent', () => {
  let fixture: ComponentFixture<CbamProductEmbeddedEmissionsComponent>;
  let component: CbamProductEmbeddedEmissionsComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const bindingBase = `${orgBase}/reporting-period-bindings/binding-1/product-embedded-emissions`;

  const productRow: CbamProductEmbeddedEmissionsProductRow = {
    productId: 'prod-1',
    productProfileVersionId: 'ppv-1',
    profileVersion: 2,
    cnNormalizedCode: '73181542',
    cnDisplayCode: '7318 15 42',
    productName: 'Screws',
    processId: 'proc-1',
    processRowVersion: 1,
    processProducedQuantity: '100.00000000',
    processProducedQuantityUnit: 't',
    denominatorTonnes: '100.00000000',
    productionRecordCount: 1,
    productionRecordsTonnes: '100.00000000',
    productionRecordIds: ['pr-1'],
    deaResultId: 'dea-1',
    deaProductAllocationId: 'dea-row-1',
    deaDirectTco2: '1.10000000',
    ieaResultId: 'iea-1',
    ieaProductAllocationId: 'iea-row-1',
    ieaIndirectTco2e: '0.20000000',
    hasMeasurableHeat: true,
    heatAttributedTco2e: '0.05000000',
    hasWasteGas: false,
    wasteGasAttributedTco2e: '0.00000000',
    exportedElectricityDirectTco2e: '-0.01000000',
    exportedElectricityNoteCode: 'PROCESS_LEVEL_EXPORTED_ELECTRICITY_MODELED',
    hasExportedElectricity: true,
    exportedElectricityMwh: '1.00000000',
    exportedElectricityEmissionFactor: '0.01000000',
    ownDirectTco2eRaw: '1.14000000',
    ownIndirectTco2eRaw: '0.20000000',
    precursorDirectTco2eRaw: '0.30000000',
    precursorIndirectTco2eRaw: '0.04000000',
    internalDirectTco2eRaw: '0.01000000',
    internalIndirectTco2eRaw: '0.00500000',
    totalDirectTco2eRaw: '1.45000000',
    totalIndirectTco2eRaw: '0.24500000',
    totalEmbeddedTco2eRaw: '1.69500000',
    ownDirectTco2e: '1.14000000',
    ownIndirectTco2e: '0.20000000',
    precursorDirectTco2e: '0.30000000',
    precursorIndirectTco2e: '0.04000000',
    internalDirectTco2e: '0.01000000',
    internalIndirectTco2e: '0.00500000',
    totalDirectTco2e: '1.45000000',
    totalIndirectTco2e: '0.24500000',
    totalEmbeddedTco2e: '1.69500000',
    specificDirectRaw: '0.01450000',
    specificIndirectRaw: '0.00245000',
    specificTotalRaw: '0.01695000',
    specificDirect: '0.01450000',
    specificIndirect: '0.00245000',
    specificTotal: '0.01695000',
    precursorContributionCount: 1,
    internalContributionCount: 1,
    resultUnit: 'tCO2e',
    specificUnit: 'tCO2e/t',
    deaSourceUnit: 'tCO2',
    components: null,
    provenance: null,
  };

  const notReady: CbamProductEmbeddedEmissionsReadiness = {
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
    status: 'NOT_READY',
    rollupReady: false,
    blockingIssueCodes: [
      'DIRECT_EMISSIONS_ALLOCATION_NOT_READY',
      'PROCESS_NOT_READY',
      'UNKNOWN_CODE_XYZ',
    ],
    informationalCodes: [],
    directEmissionsAllocationResultId: null,
    directEmissionsAllocationStale: false,
    indirectEmissionsAllocationResultId: null,
    indirectEmissionsAllocationStale: false,
    eligibleProductCount: 0,
    blockedProductCount: 1,
    precursorContributionCount: 0,
    products: [],
    currentResultId: null,
    currentIsStale: false,
    staleReasonCodes: [],
    exportedElectricityNoteCode: 'PROCESS_LEVEL_EXPORTED_ELECTRICITY_MODELED',
    exportedElectricityNote: 'T72 modeled',
    internalPrecursorNoteCode: 'INTERNAL_PROCESS_PRECURSOR_LEONTIEF_MODELED',
    internalPrecursorNote: 'Internal flows modeled',
  };

  const ready: CbamProductEmbeddedEmissionsReadiness = {
    ...notReady,
    status: 'READY',
    rollupReady: true,
    blockingIssueCodes: [],
    eligibleProductCount: 1,
    blockedProductCount: 0,
    directEmissionsAllocationResultId: 'dea-1',
    indirectEmissionsAllocationResultId: 'iea-1',
    precursorContributionCount: 1,
  };

  const emptySummary: CbamProductEmbeddedEmissionsPeriodSummary = {
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
    currentResultId: null,
    currentIsStale: false,
    staleReasonCodes: [],
    productCount: null,
    precursorContributionCount: null,
    internalContributionCount: null,
    totalDirectTco2e: null,
    totalIndirectTco2e: null,
    totalEmbeddedTco2e: null,
    resultUnit: 'tCO2e',
    specificUnit: 'tCO2e/t',
    totalsByProduct: [],
  };

  const currentSummary: CbamProductEmbeddedEmissionsPeriodSummary = {
    ...emptySummary,
    currentResultId: 'res-1',
    productCount: 1,
    precursorContributionCount: 1,
    internalContributionCount: 1,
    totalDirectTco2e: '1.45000000',
    totalIndirectTco2e: '0.24500000',
    totalEmbeddedTco2e: '1.69500000',
    totalsByProduct: [productRow],
  };

  const resultRow: CbamProductEmbeddedEmissionsResultSummary = {
    resultId: 'res-1',
    runId: 'res-1',
    methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
    methodologyVersion: '2.0.0',
    status: 'COMPLETED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    productCount: 1,
    precursorContributionCount: 1,
    internalContributionCount: 1,
    totalDirectTco2e: '1.45000000',
    totalIndirectTco2e: '0.24500000',
    totalEmbeddedTco2e: '1.69500000',
    resultUnit: 'tCO2e',
    specificUnit: 'tCO2e/t',
    createdAt: '2024-06-01T10:00:00Z',
  };

  const detail: CbamProductEmbeddedEmissionsResultDetail = {
    resultId: 'res-1',
    runId: 'res-1',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
    methodologyVersion: '2.0.0',
    workbookFilename: 'SEE.xlsx',
    workbookSha256: 'abc',
    workbookFormulaRefs: 'T54/T72',
    clientRequestId: '11111111-1111-1111-1111-111111111111',
    requestFingerprint: 'fp',
    status: 'COMPLETED',
    isCurrent: true,
    isStale: false,
    staleReasonCodes: [],
    productCount: 1,
    precursorContributionCount: 1,
    internalContributionCount: 1,
    totalDirectTco2eRaw: '1.45000000',
    totalIndirectTco2eRaw: '0.24500000',
    totalEmbeddedTco2eRaw: '1.69500000',
    totalDirectTco2e: '1.45000000',
    totalIndirectTco2e: '0.24500000',
    totalEmbeddedTco2e: '1.69500000',
    resultUnit: 'tCO2e',
    specificUnit: 'tCO2e/t',
    deaSourceUnit: 'tCO2',
    workbookGas: 'CO2',
    workbookGwp: '1',
    workbookGwpFactor: '1',
    gwpEquivalenceNote: 'GWP=1',
    denominatorNote: 'L24',
    exportedElectricityNoteCode: 'PROCESS_LEVEL_EXPORTED_ELECTRICITY_MODELED',
    exportedElectricityNote: 'T72 modeled',
    internalPrecursorNoteCode: 'INTERNAL_PROCESS_PRECURSOR_LEONTIEF_MODELED',
    internalPrecursorNote: 'Internal flows modeled',
    directEmissionsAllocationResultId: 'dea-1',
    indirectEmissionsAllocationResultId: 'iea-1',
    informationalCodes: [],
    products: [productRow],
    precursorContributions: [
      {
        productProfileVersionId: 'ppv-1',
        precursorId: 'prec-1',
        precursorRowVersion: 1,
        precursorName: 'Wire rod',
        precursorCnNormalizedCode: '72139110',
        precursorCnDisplayCode: '7213 91 10',
        dataSourceMode: 'SUPPLIER_DATA',
        valueSource: 'SUPPLIER',
        productUseId: 'use-1',
        productUseRowVersion: 1,
        productUseQuantity: '10',
        productUseUnit: 't',
        quantityTonnes: '10.00000000',
        specificDirect: '0.03000000',
        specificIndirect: '0.00400000',
        contributionDirectTco2eRaw: '0.30000000',
        contributionIndirectTco2eRaw: '0.04000000',
        contributionDirectTco2e: '0.30000000',
        contributionIndirectTco2e: '0.04000000',
        defaultDatasetId: null,
        defaultValueId: null,
        defaultSnapshot: null,
        resultUnit: 'tCO2e',
        specificUnit: 'tCO2e/t',
      },
    ],
    internalContributions: [
      {
        consumerProductProfileVersionId: 'ppv-1',
        supplierProductProfileVersionId: 'ppv-2',
        consumerProcessId: 'proc-1',
        supplierProcessId: 'proc-2',
        supplierProcessRowVersion: 1,
        productUseId: 'iuse-1',
        productUseRowVersion: 1,
        productUseQuantity: '2',
        productUseUnit: 't',
        quantityTonnes: '2.00000000',
        consumerDenominatorTonnes: '100.00000000',
        aCoefficient: '0.02000000',
        supplierSpecificDirect: '0.00500000',
        supplierSpecificIndirect: '0.00250000',
        contributionDirectTco2eRaw: '0.01000000',
        contributionIndirectTco2eRaw: '0.00500000',
        contributionDirectTco2e: '0.01000000',
        contributionIndirectTco2e: '0.00500000',
        resultUnit: 'tCO2e',
        specificUnit: 'tCO2e/t',
      },
    ],
    createdAt: '2024-06-01T10:00:00Z',
    createdByUserId: 'user-1',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamProductEmbeddedEmissionsComponent],
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
    fixture = TestBed.createComponent(CbamProductEmbeddedEmissionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('bindingId', 'binding-1');
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushLoad(options?: {
    readiness?: CbamProductEmbeddedEmissionsReadiness;
    summary?: CbamProductEmbeddedEmissionsPeriodSummary;
    results?: CbamProductEmbeddedEmissionsResultSummary[];
    detail?: CbamProductEmbeddedEmissionsResultDetail | null;
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
    const currentId = readiness.currentResultId ?? results.find((r) => r.isCurrent)?.resultId;
    if (currentId && options?.detail !== null) {
      httpMock
        .expectOne(`${bindingBase}/results/${currentId}`)
        .flush(options?.detail ?? { ...detail, resultId: currentId });
    }
    fixture.detectChanges();
  }

  it('maps issue codes, unknown fallback, methodology and lifecycle labels', () => {
    expect(mapPeeIssueCode('DIRECT_EMISSIONS_ALLOCATION_NOT_READY')).toContain(
      'direct emissions allocation',
    );
    expect(mapPeeIssueCode('INTERNAL_PRODUCT_FLOW_SINGULAR')).toBe(
      'The internal product flow cannot be calculated.',
    );
    expect(mapPeeIssueCode('INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO')).toBe(
      'A product output quantity is missing.',
    );
    expect(mapPeeIssueCode('UNKNOWN_CODE_XYZ')).toBe(
      'More information is needed. (UNKNOWN_CODE_XYZ)',
    );
    expect(mapPeeStaleReason('INTERNAL_PRODUCT_FLOW_CHANGED')).toBe(
      'Check the quantities used in other products.',
    );
    expect(mapResultLifecycleLabel(true, true)).toBe('Out of date');
    expect(mapResultLifecycleLabel(true, false)).toBe('Current');
    expect(mapResultLifecycleLabel(false, false)).toBe('History');
    expect(mapMethodologyLabel('CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2')).toBe('V2');
    expect(mapMethodologyLabel('CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1')).toBe('V1');
    expect(formatDecimalDisplay('0.01695000')).toBe('0.01695000');
    expect(formatDecimalDisplay('9007199254740993')).toBe('9007199254740993');
  });

  it('maps API errors without raw backend text', () => {
    const err = new HttpErrorResponse({
      status: 409,
      error: {
        error: {
          code: 'DIRECT_EMISSIONS_ALLOCATION_STALE',
          message: 'SQL DETAIL: relation foo',
          details: [{ code: 'DIRECT_EMISSIONS_ALLOCATION_STALE' }],
        },
      },
    });
    expect(mapPeeError(err)).toContain('direct emissions allocation');
    expect(mapPeeError(err)).not.toContain('SQL');
    expect(mapPeeError(new HttpErrorResponse({ status: 403, error: {} }))).toContain('permission');
    expect(mapPeeError(new HttpErrorResponse({ status: 404, error: {} }))).toContain('not found');
    expect(
      mapPeeError(
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
    expect(text).toContain('Complete the direct emissions allocation.');
    expect(text).toContain('Complete the process data.');
    expect(text).toContain('More information is needed. (UNKNOWN_CODE_XYZ)');
    expect(text).toContain('Product Profiles');
    expect(text).toContain('Allocation');

    const btn = fixture.debugElement.query(
      By.css('button[aria-label="Calculate product results"]'),
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

    expect(
      fixture.debugElement.query(By.css('button[aria-label="Calculate product results"]')),
    ).toBeNull();
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
      By.css('button[aria-label="Calculate product results"]'),
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

    component.executeRollup();
    const first = httpMock.expectOne(`${bindingBase}/executions`);
    expect(first.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    expect(first.request.body.methodologyCode).toBeUndefined();
    first.flush({ error: { code: 'NETWORK' } }, { status: 0, statusText: 'Unknown Error' });
    tick();
    expect(component.peekClientRequestId()).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');

    component.executeRollup();
    const retry = httpMock.expectOne(`${bindingBase}/executions`);
    expect(retry.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    retry.flush({
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
      methodologyVersion: '2.0.0',
      productCount: 1,
      precursorContributionCount: 1,
      internalContributionCount: 1,
      totalDirectTco2e: '1.45000000',
      totalIndirectTco2e: '0.24500000',
      totalEmbeddedTco2e: '1.69500000',
      resultUnit: 'tCO2e',
      specificUnit: 'tCO2e/t',
      clientRequestId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    expect(component.executeButtonLabel()).toBe('Calculate again');
    component.executeRollup();
    const again = httpMock.expectOne(`${bindingBase}/executions`);
    expect(again.request.body.clientRequestId).toBe('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');
    again.flush({
      resultId: 'res-2',
      runId: 'res-2',
      status: 'COMPLETED',
      methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
      methodologyVersion: '2.0.0',
      productCount: 1,
      precursorContributionCount: 1,
      internalContributionCount: 1,
      totalDirectTco2e: '1.45000000',
      totalIndirectTco2e: '0.24500000',
      totalEmbeddedTco2e: '1.69500000',
      resultUnit: 'tCO2e',
      specificUnit: 'tCO2e/t',
      clientRequestId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      idempotentReplay: false,
      createdAt: '2024-06-02T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-2' },
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
    component.executeRollup();
    httpMock.expectOne(`${bindingBase}/executions`).flush({
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
      methodologyVersion: '2.0.0',
      productCount: 1,
      precursorContributionCount: 1,
      internalContributionCount: 1,
      totalDirectTco2e: '1.45000000',
      totalIndirectTco2e: '0.24500000',
      totalEmbeddedTco2e: '1.69500000',
      resultUnit: 'tCO2e',
      specificUnit: 'tCO2e/t',
      clientRequestId: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
      idempotentReplay: true,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
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
    component.executeRollup();
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

    component.executeRollup();
    httpMock.expectOne(`${bindingBase}/executions`).flush({
      resultId: 'res-1',
      runId: 'res-1',
      status: 'COMPLETED',
      methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2',
      methodologyVersion: '2.0.0',
      productCount: 1,
      precursorContributionCount: 1,
      internalContributionCount: 1,
      totalDirectTco2e: '1.45000000',
      totalIndirectTco2e: '0.24500000',
      totalEmbeddedTco2e: '1.69500000',
      resultUnit: 'tCO2e',
      specificUnit: 'tCO2e/t',
      clientRequestId: createClientRequestId(),
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('1.69500000');
    expect(text).toContain('0.01695000');
    expect(text).toContain('Ready');
    expect(text).toContain('Current');
    expect(text).toContain('V2 includes internal product flows.');
    expect(component.selectedDetail()?.products[0].productName).toBe('Screws');
  }));

  it('failure preserves the last successful result', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('1.69500000');

    component.executeRollup();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      {
        error: {
          code: 'DIRECT_EMISSIONS_ALLOCATION_STALE',
          details: [{ code: 'DIRECT_EMISSIONS_ALLOCATION_STALE' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('1.69500000');
    expect(component.summary()?.currentResultId).toBe('res-1');
    expect(component.selectedDetail()?.resultId).toBe('res-1');
  }));

  it('shows product totals from backend without client Number arithmetic', fakeAsync(() => {
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('1.45000000');
    expect(text).toContain('0.24500000');
    expect(text).toContain('1.69500000');
    expect(text).toContain('0.01450000');
    expect(text).toContain('0.00245000');
    expect(text).toContain('0.01695000');
    expect(text).toContain('tCO2e/t');

    const source = (component as unknown as { constructor: { toString: () => string } }).constructor
      .toString();
    expect(source).not.toMatch(/Number\([^)]*total/i);
    expect(formatDecimalDisplay(component.summary()?.totalEmbeddedTco2e)).toBe('1.69500000');
  }));

  it('shows own, precursor, internal and T72 breakdown from immutable detail', fakeAsync(() => {
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Allocated direct emissions');
    expect(text).toContain('1.10000000');
    expect(text).toContain('Measurable heat');
    expect(text).toContain('0.05000000');
    expect(text).toContain('Waste gas');
    expect(text).toContain('Exported-electricity adjustment (T72)');
    expect(text).toContain('-0.01000000');
    expect(text).toContain('Allocated indirect emissions');
    expect(text).toContain('0.20000000');
    expect(text).toContain('Wire rod');
    expect(text).toContain('Supplier data');
    expect(text).toContain('0.30000000');
    expect(text).toContain('0.04000000');
    expect(text).toContain('Internal products');
    expect(text).toContain('0.01000000');
    expect(text).toContain('0.00500000');
  }));

  it('labels V2 current and V1 historical results', fakeAsync(() => {
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [
        resultRow,
        {
          ...resultRow,
          resultId: 'res-v1',
          methodologyCode: 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1',
          methodologyVersion: '1.0.0',
          isCurrent: false,
          createdAt: '2024-05-01T10:00:00Z',
        },
      ],
    });
    tick();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('V2');
    expect(text).toContain('V1');
    expect(text).toContain('V2 includes internal product flows.');
    expect(text).not.toContain('methodology picker');
  }));

  it('shows Update product results CTA when current result is stale', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
    flushLoad({
      readiness: {
        ...ready,
        currentResultId: 'res-1',
        currentIsStale: true,
        staleReasonCodes: ['PROCESS_CHANGED'],
      },
      summary: {
        ...currentSummary,
        currentIsStale: true,
        staleReasonCodes: ['PROCESS_CHANGED'],
      },
      results: [{ ...resultRow, isStale: true }],
      detail: { ...detail, isStale: true, staleReasonCodes: ['PROCESS_CHANGED'] },
    });
    tick();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Update product results');
    expect(text).toContain(
      'Some source data changed after this calculation. Update the product results.',
    );
    expect(text).toContain('Out of date');
    expect(component.executeButtonLabel()).toBe('Update product results');
  }));

  it('historical detail does not call live process/precursor/CN APIs', fakeAsync(() => {
    fixture.detectChanges();
    flushLoad({
      readiness: { ...ready, currentResultId: 'res-1' },
      summary: currentSummary,
      results: [resultRow],
    });
    tick();
    fixture.detectChanges();

    component.viewDetails('res-1');
    httpMock.expectOne(`${bindingBase}/results/res-1`).flush(detail);
    fixture.detectChanges();

    const pending = httpMock.match(() => true);
    expect(pending.filter((r) => r.request.url.includes('/production-processes')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/purchased-precursors')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/cn-codes')).length).toBe(0);
    expect(pending.filter((r) => r.request.url.includes('/product-profiles')).length).toBe(0);
  }));

  it('emits blocking-section navigation outputs', fakeAsync(() => {
    const profiles = jasmine.createSpy('profiles');
    const production = jasmine.createSpy('production');
    const direct = jasmine.createSpy('direct');
    const indirect = jasmine.createSpy('indirect');
    const processes = jasmine.createSpy('processes');
    const purchased = jasmine.createSpy('purchased');
    const allocation = jasmine.createSpy('allocation');
    component.goToProductProfiles.subscribe(profiles);
    component.goToProduction.subscribe(production);
    component.goToDirectEmissions.subscribe(direct);
    component.goToIndirectEmissions.subscribe(indirect);
    component.goToProcesses.subscribe(processes);
    component.goToPurchasedInputs.subscribe(purchased);
    component.goToAllocation.subscribe(allocation);

    fixture.detectChanges();
    flushLoad();
    tick();
    fixture.detectChanges();

    const buttons = fixture.debugElement.queryAll(By.css('.nav-links button'));
    expect(buttons.length).toBe(7);
    buttons[0].nativeElement.click();
    buttons[1].nativeElement.click();
    buttons[2].nativeElement.click();
    buttons[3].nativeElement.click();
    buttons[4].nativeElement.click();
    buttons[5].nativeElement.click();
    buttons[6].nativeElement.click();
    expect(profiles).toHaveBeenCalled();
    expect(production).toHaveBeenCalled();
    expect(direct).toHaveBeenCalled();
    expect(indirect).toHaveBeenCalled();
    expect(processes).toHaveBeenCalled();
    expect(purchased).toHaveBeenCalled();
    expect(allocation).toHaveBeenCalled();
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
