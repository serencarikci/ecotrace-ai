import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { signal } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { environment } from '../../../environments/environment';
import { CbamPeriodDetailComponent } from './period-detail.component';

describe('CbamPeriodDetailComponent Phase 3–4A', () => {
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<CbamPeriodDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamPeriodDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'binding-1' } } },
        },
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
    fixture = TestBed.createComponent(CbamPeriodDetailComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    // The purchased-precursors panel lives in the Purchased Inputs tab and loads its own
    // catalogs once change detection reaches it, independently of the period bootstrap.
    flushPrecursorPanel();
    httpMock.verify();
  });

  function flushPrecursorPanel(): void {
    for (const req of httpMock.match(
      (r) => r.method === 'GET' && r.url.includes('/purchased-precursors/metadata'),
    )) {
      req.flush({
        methodologyCode: 'PURCHASED_PRECURSOR_V1',
        methodologyVersion: '1.0.0',
        workbookFilename: 'CBAM SEE V2.1.xlsx',
        workbookSha256: 'sha',
        workbookPrimarySheet: 'E_PurchPrec',
        workbookFormulaRefs: 'L52=L50*L51',
        supportedDataSourceModes: ['EU_DEFAULT', 'SUPPLIER_DATA'],
        units: {},
        fieldMap: {},
        extraction: {},
        controlledLists: [],
        defaultValueDataset: {
          id: 'ds-1',
          datasetCode: 'CBAM_EU_DEFAULT_VALUES',
          datasetVersion: 'IR_2025_2621_v20260204',
          contentChecksum: 'checksum',
          sourceWorkbookName: 'DVs_as_adopted_v20260204.xlsx',
          sourceWorkbookSha256: 'sha',
          sourceTemplateVersion: 'v20260204',
          regulationReference: null,
          validFrom: '2026-01-01',
          validUntil: null,
          status: 'ACTIVE',
          valueCount: 12532,
        },
        otherCountriesNote: 'Other countries note.',
        rollupNote: 'Precursor emissions are not rolled up into product totals.',
      });
    }
    const emptyPage = { items: [], page: 1, pageSize: 100, totalItems: 0, totalPages: 0 };
    for (const req of httpMock.match(
      (r) => r.method === 'GET' && r.url.endsWith('/purchased-precursors'),
    )) {
      req.flush(emptyPage);
    }
    for (const req of httpMock.match(
      (r) =>
        r.method === 'GET' &&
        r.url.endsWith('/installations') &&
        r.params.get('status') === 'ACTIVE',
    )) {
      req.flush(emptyPage);
    }
    for (const req of httpMock.match(
      (r) =>
        r.method === 'GET' &&
        r.url.endsWith('/product-profiles') &&
        r.params.get('pageSize') === '100',
    )) {
      req.flush(emptyPage);
    }
    for (const req of httpMock.match(
      (r) =>
        r.method === 'GET' &&
        r.url.endsWith('/purchased-inputs') &&
        r.params.get('pageSize') === '100',
    )) {
      req.flush(emptyPage);
    }
    for (const req of httpMock.match((r) => r.method === 'GET' && r.url.endsWith('/suppliers'))) {
      req.flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    }
  }

  function flushBootstrap(options?: {
    roles?: string[];
    production?: unknown[];
    linkSummary?: {
      eligibleRecordCount: number;
      missingProfileCount: number;
      outdatedProfileCount: number;
      invalidProfileCount: number;
      activeRecordCount: number;
      allocationProfileReady: boolean;
      blockingIssueCodes: string[];
    };
    rules?: unknown[];
    results?: unknown[];
    runs?: Array<{ id: string; status: string; calculatedCount: number; blockedCount: number; invalidCount: number; primaryFactorCount: number; defaultFactorCount: number }>;
    calcResults?: unknown[];
  }): void {
    const base = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
    const periodsBase = `${environment.apiUrl}${environment.apiV1Prefix}/organizations/org-1/reporting-periods`;
    httpMock.expectOne((r) => r.url.startsWith(periodsBase)).flush({
      items: [
        {
          id: 'rp-1',
          organizationId: 'org-1',
          code: 'RP-1',
          name: 'Review Period',
          periodType: 'custom',
          startDate: '2024-07-01',
          endDate: '2024-08-31',
          status: 'open',
        },
      ],
      page: 1,
      pageSize: 200,
      totalItems: 1,
      totalPages: 1,
    });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1`)
      .flush({
        id: 'binding-1',
        organizationId: 'org-1',
        reportingPeriodId: 'rp-1',
        status: 'data_collection',
        lockedAt: null,
        lockedByUserId: null,
        approvedAt: null,
        approvedCalculationRunId: null,
        revisionNumber: 0,
        rowVersion: 2,
      });
    httpMock.expectOne((r) => r.url.includes('/installations')).flush({
      items: [
        {
          id: 'inst-1',
          organizationId: 'org-1',
          facilityId: 'f1',
          code: 'I1',
          name: 'Inst',
          status: 'active',
          timezone: 'UTC',
          operatorIdentityRef: null,
          metadataJson: null,
          rowVersion: 1,
        },
      ],
      page: 1,
      pageSize: 100,
      totalItems: 1,
      totalPages: 1,
    });
    httpMock.expectOne(`${base}/activity-types`).flush([
      {
        code: 'ELECTRICITY',
        displayName: 'Electricity',
        activityGroup: 'PURCHASED_ENERGY',
        allowedUnitFamily: 'energy',
      },
    ]);
    httpMock.expectOne(`${base}/units`).flush([
      { code: 'kWh', displayName: 'Kilowatt-hour', family: 'energy' },
      { code: 'MWh', displayName: 'Megawatt-hour', family: 'energy' },
      { code: 't', displayName: 'Tonne', family: 'mass' },
    ]);
    httpMock
      .expectOne(
        (r) =>
          r.url.includes('/organizations/org-1/products') &&
          !r.url.includes('/cbam/'),
      )
      .flush({
        items: [
          {
            id: 'prod-1',
            organizationId: 'org-1',
            code: 'P1',
            name: 'Screws',
            productType: 'finished_good',
            defaultUnitCode: 't',
            isActive: true,
          },
        ],
        page: 1,
        pageSize: 100,
        totalItems: 1,
        totalPages: 1,
      });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/production-records?page=1&pageSize=20`)
      .flush({
        items: options?.production ?? [],
        page: 1,
        pageSize: 20,
        totalItems: (options?.production ?? []).length,
        totalPages: 1,
      });
    httpMock
      .expectOne(
        `${base}/reporting-period-bindings/binding-1/production-profile-link-summary`,
      )
      .flush(
        options?.linkSummary ?? {
          eligibleRecordCount: 0,
          missingProfileCount: 0,
          outdatedProfileCount: 0,
          invalidProfileCount: 0,
          activeRecordCount: (options?.production ?? []).length,
          allocationProfileReady: false,
          blockingIssueCodes: ['PRODUCTION_RECORDS_REQUIRED'],
        },
      );
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/activity-records?page=1&pageSize=20`)
      .flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/purchased-inputs?page=1&pageSize=20`)
      .flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/allocation-rules?page=1&pageSize=20`)
      .flush({
        items: options?.rules ?? [],
        page: 1,
        pageSize: 20,
        totalItems: (options?.rules ?? []).length,
        totalPages: 1,
      });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/allocation-results?page=1&pageSize=20`)
      .flush({
        items: options?.results ?? [],
        page: 1,
        pageSize: 20,
        totalItems: (options?.results ?? []).length,
        totalPages: 1,
      });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/factor-resolutions?page=1&pageSize=50`)
      .flush({ items: [], page: 1, pageSize: 50, totalItems: 0, totalPages: 0 });
    const defsReq = httpMock.expectOne(`${base}/factor-definitions?page=1&pageSize=50`);
    defsReq.flush({
      items: [
        {
          id: 'def-ncv',
          code: 'NET_CALORIFIC_VALUE',
          name: 'Net calorific value',
          factorCategory: 'ACTIVITY_PROPERTY',
          activityType: null,
          propertyCode: 'NET_CALORIFIC_VALUE',
          inputUnitFamily: null,
          outputUnit: null,
          description: null,
          status: 'ACTIVE',
        },
      ],
      page: 1,
      pageSize: 50,
      totalItems: 1,
      totalPages: 1,
    });
    httpMock
      .expectOne(`${base}/factor-definitions/def-ncv/values?page=1&pageSize=50`)
      .flush({ items: [], page: 1, pageSize: 50, totalItems: 0, totalPages: 0 });
    httpMock
      .expectOne(`${base}/reference-sources?page=1&pageSize=50`)
      .flush({ items: [], page: 1, pageSize: 50, totalItems: 0, totalPages: 0 });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/calculation-runs?page=1&pageSize=20`)
      .flush({
        items: options?.runs ?? [],
        page: 1,
        pageSize: 20,
        totalItems: (options?.runs ?? []).length,
        totalPages: 1,
      });
    if ((options?.runs ?? []).length > 0) {
      const runId = options!.runs![0].id;
      httpMock
        .expectOne(`${base}/calculation-runs/${runId}/results?page=1&pageSize=50`)
        .flush({
          items: options?.calcResults ?? [],
          page: 1,
          pageSize: 50,
          totalItems: (options?.calcResults ?? []).length,
          totalPages: 1,
        });
    }
    httpMock.expectOne(`${base}/export-templates?page=1&pageSize=20`).flush({
      items: [
        {
          id: 'tpl-1',
          organizationId: null,
          code: 'ECOTRACE_SKDM_INTERNAL',
          name: 'EcoTrace SKDM Internal',
          templateType: 'INTERNAL_SKDM',
          version: '1.0.0',
          mappingVersion: '1.0.0',
          storageUri: 'cbam/templates/ECOTRACE_SKDM_INTERNAL/1.0.0/template.xlsx',
          checksum: 'abc123checksum456',
          status: 'ACTIVE',
          description: 'Internal',
          activatedAt: '2032-01-01T00:00:00Z',
          archivedAt: null,
          officialMappingBlocked: true,
        },
      ],
      page: 1,
      pageSize: 20,
      totalItems: 1,
      totalPages: 1,
    });
    httpMock.expectOne(`${base}/reporting-period-bindings/binding-1/summary`).flush({
      title: 'SKDM Period Summary',
      organizationId: 'org-1',
      organizationName: 'Demo',
      reportingPeriodBindingId: 'binding-1',
      reportingPeriodCode: 'P1',
      readinessStatus: 'NOT_READY',
      metrics: { activity_record_count: 0, blocked_calculation_count: 0 },
      warnings: [],
      officialMappingBlocked: true,
      calculationRunId: null,
      installations: [],
      disclaimer: 'SKDM Period Summary is an internal EcoTrace summary.',
    });
    httpMock
      .expectOne(`${base}/reporting-period-bindings/binding-1/exports?page=1&pageSize=20`)
      .flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    fixture.detectChanges();
    const readinessReq = httpMock.expectOne(
      (r) =>
        r.url.includes('/reporting-period-bindings/binding-1/export-readiness') &&
        r.method === 'GET',
    );
    readinessReq.flush({
      status: 'NOT_READY',
      checks: [
        { code: 'production', label: 'Production Data', status: 'WARNING', message: 'No production' },
        { code: 'activity', label: 'Activity Data', status: 'MISSING', message: 'Missing' },
        {
          code: 'purchased',
          label: 'Purchased Inputs',
          status: 'WARNING',
          message: 'No purchased',
        },
        { code: 'allocation', label: 'Allocation', status: 'WARNING', message: 'No allocation' },
        { code: 'factors', label: 'Factor Resolution', status: 'WARNING', message: 'No factors' },
        { code: 'calculation', label: 'Calculation', status: 'MISSING', message: 'No calc' },
        { code: 'mappings', label: 'Excel Mapping', status: 'OK', message: 'ok' },
      ],
      blockingIssues: ['Missing'],
      warnings: ['Internal Excel readiness warnings only'],
      officialMappingBlocked: true,
      suggestedTemplateId: 'tpl-1',
      calculationRunId: null,
    });
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/official-see-export/readiness') && r.method === 'GET',
    )) {
      req.flush({
        ready: false,
        blockingIssueCodes: ['PEE_V2_MISSING_OR_STALE'],
        warnings: [],
        mappingVersion: 'official-see-mapping-v1',
        templateVersion: 'CBAM_SEE_V2.1',
        templateSha256: '83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64',
        capacity: {
          installations: 1,
          goods: 0,
          processes: 0,
          precursors: 0,
          fuelActivities: 0,
        },
        sofficeAvailable: true,
        snapshotIds: {},
      });
    }
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/official-see-export/runs') &&
        r.method === 'GET' &&
        !r.url.includes('/artifacts'),
    )) {
      req.flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/monthly-production-basis-summary'),
    )) {
      req.flush({
        reportingPeriodBindingId: 'binding-1',
        expectedMonthCount: 0,
        completedMonthCount: 0,
        incompleteMonthCount: 0,
        invalidMonthCount: 0,
        missingMonthCount: 0,
        status: 'INCOMPLETE',
        allocationBasisReady: false,
        blockingIssueCodes: [],
        monthCoverage: [],
        informationalTotalProductionTonnes: null,
        informationalTotalCbamQuantityTonnes: null,
        combustionCompatibilityStatus: 'READY',
        combustionCompatibilityIssueCodes: [],
        combustionItems: [],
        productionReconciliation: [],
      });
    }
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/monthly-production-basis') &&
        !r.url.includes('summary') &&
        r.method === 'GET',
    )) {
      req.flush({ items: [], page: 1, pageSize: 100, totalItems: 0, totalPages: 0 });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/direct-emissions-allocation/readiness'),
    )) {
      req.flush({
        status: 'NOT_READY',
        allocationReady: false,
        blockingIssueCodes: ['DIRECT_EMISSIONS_NOT_READY'],
        stationaryCombustionStatus: 'EMPTY',
        monthlyProductionBasisStatus: 'INCOMPLETE',
        productionProfileStatus: 'NOT_READY',
        productionReconciliationStatus: 'UNAVAILABLE',
        sourceResultCount: 0,
        monthCount: 0,
        fuelCount: 0,
        participatingProductionRecordCount: 0,
        productProfileGroupCount: 0,
        currentAllocationId: null,
        currentAllocationStale: false,
        staleReasonCodes: [],
      });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/direct-emissions-allocation/summary'),
    )) {
      req.flush({
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
      });
    }
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/direct-emissions-allocation/results') &&
        !r.url.match(/results\/[^/?]+$/) &&
        r.method === 'GET',
    )) {
      req.flush({ items: [], page: 1, pageSize: 10, totalItems: 0, totalPages: 0 });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/indirect-emissions-allocation/readiness'),
    )) {
      req.flush({
        status: 'NOT_READY',
        allocationReady: false,
        blockingIssueCodes: ['INDIRECT_EMISSIONS_NOT_READY'],
        purchasedElectricityStatus: 'EMPTY',
        monthlyProductionBasisStatus: 'INCOMPLETE',
        productionProfileStatus: 'NOT_READY',
        productionReconciliationStatus: 'UNAVAILABLE',
        sourceResultCount: 0,
        monthCount: 0,
        participatingProductionRecordCount: 0,
        productProfileGroupCount: 0,
        currentAllocationId: null,
        currentAllocationStale: false,
        staleReasonCodes: [],
      });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/indirect-emissions-allocation/summary'),
    )) {
      req.flush({
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
      });
    }
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/indirect-emissions-allocation/results') &&
        !r.url.match(/results\/[^/?]+$/) &&
        r.method === 'GET',
    )) {
      req.flush({ items: [], page: 1, pageSize: 10, totalItems: 0, totalPages: 0 });
    }
    fixture.detectChanges();
  }

  function openAllocationTab(): void {
    const labels = Array.from(
      fixture.nativeElement.querySelectorAll('.mdc-tab__text-label'),
    ) as HTMLElement[];
    const alloc = labels.find((el) => el.textContent?.includes('Allocation'));
    expect(alloc).toBeTruthy();
    alloc?.click();
    fixture.detectChanges();
    // Child allocation panels load when the tab becomes active.
    for (const req of httpMock.match((r) =>
      r.url.includes('/direct-emissions-allocation/readiness'),
    )) {
      req.flush({
        status: 'NOT_READY',
        allocationReady: false,
        blockingIssueCodes: ['DIRECT_EMISSIONS_NOT_READY'],
        stationaryCombustionStatus: 'EMPTY',
        monthlyProductionBasisStatus: 'INCOMPLETE',
        productionProfileStatus: 'NOT_READY',
        productionReconciliationStatus: 'UNAVAILABLE',
        sourceResultCount: 0,
        monthCount: 0,
        fuelCount: 0,
        participatingProductionRecordCount: 0,
        productProfileGroupCount: 0,
        currentAllocationId: null,
        currentAllocationStale: false,
        staleReasonCodes: [],
      });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/direct-emissions-allocation/summary'),
    )) {
      req.flush({
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
      });
    }
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/direct-emissions-allocation/results') &&
        !r.url.match(/results\/[^/?]+$/) &&
        r.method === 'GET',
    )) {
      req.flush({ items: [], page: 1, pageSize: 10, totalItems: 0, totalPages: 0 });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/indirect-emissions-allocation/readiness'),
    )) {
      req.flush({
        status: 'NOT_READY',
        allocationReady: false,
        blockingIssueCodes: ['INDIRECT_EMISSIONS_NOT_READY'],
        purchasedElectricityStatus: 'EMPTY',
        monthlyProductionBasisStatus: 'INCOMPLETE',
        productionProfileStatus: 'NOT_READY',
        productionReconciliationStatus: 'UNAVAILABLE',
        sourceResultCount: 0,
        monthCount: 0,
        participatingProductionRecordCount: 0,
        productProfileGroupCount: 0,
        currentAllocationId: null,
        currentAllocationStale: false,
        staleReasonCodes: [],
      });
    }
    for (const req of httpMock.match((r) =>
      r.url.includes('/indirect-emissions-allocation/summary'),
    )) {
      req.flush({
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
      });
    }
    for (const req of httpMock.match(
      (r) =>
        r.url.includes('/indirect-emissions-allocation/results') &&
        !r.url.match(/results\/[^/?]+$/) &&
        r.method === 'GET',
    )) {
      req.flush({ items: [], page: 1, pageSize: 10, totalItems: 0, totalPages: 0 });
    }
    fixture.detectChanges();
  }

  function openPurchasedInputsTab(): void {
    const labels = Array.from(
      fixture.nativeElement.querySelectorAll('.mdc-tab__text-label'),
    ) as HTMLElement[];
    const purchased = labels.find((el) => el.textContent?.includes('Purchased Inputs'));
    expect(purchased).toBeTruthy();
    purchased?.click();
    fixture.detectChanges();
    flushPrecursorPanel();
    fixture.detectChanges();
  }

  it('renders period tabs including Allocation and Report / Excel for configure roles', () => {
    flushBootstrap();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Production');
    expect(text).toContain('Product Profiles');
    expect(text).toContain('Activities');
    expect(text).toContain('Direct Emissions');
    expect(text).toContain('Indirect Emissions');
    expect(text).toContain('Processes');
    expect(text).toContain('Purchased Inputs');
    expect(text).toContain('Product Results');
    expect(text).toContain('Allocation');
    expect(text).toContain('Factors');
    expect(text).toContain('Calculation');
    expect(text).toContain('Report / Excel');
    expect(text).toContain('No production data has been added for this period.');
    expect(text.toLowerCase()).not.toContain('emission factor');
    expect(text.toLowerCase()).not.toContain('certificate amount');

    const tabLabels = Array.from(
      fixture.nativeElement.querySelectorAll('.mdc-tab__text-label'),
    ).map((el) => ((el as HTMLElement).textContent || '').trim());
    const indirectIdx = tabLabels.findIndex((l) => l.includes('Indirect Emissions'));
    const processesIdx = tabLabels.findIndex((l) => l === 'Processes');
    const purchasedIdx = tabLabels.findIndex((l) => l.includes('Purchased Inputs'));
    const productResultsIdx = tabLabels.findIndex((l) => l.includes('Product Results'));
    const allocationIdx = tabLabels.findIndex((l) => l === 'Allocation');
    expect(indirectIdx).toBeGreaterThanOrEqual(0);
    expect(processesIdx).toBe(indirectIdx + 1);
    expect(purchasedIdx).toBe(processesIdx + 1);
    expect(productResultsIdx).toBe(purchasedIdx + 1);
    expect(allocationIdx).toBe(productResultsIdx + 1);

    openAllocationTab();
    const allocText = fixture.nativeElement.textContent as string;
    expect(allocText).toContain('Direct emissions allocation');
    expect(allocText).toContain('Indirect emissions allocation');
    expect(allocText).toContain('Generic allocation rules');
    expect(allocText).toContain('how much of a shared amount belongs to this product');
    expect(allocText).toContain('New allocation rule');
    expect(allocText).toContain('No allocation rules have been added for this period.');
    expect(allocText.toLowerCase()).not.toContain('emission factor');
    const dea = fixture.nativeElement.querySelector(
      '[data-testid="direct-emissions-allocation"]',
    ) as HTMLElement | null;
    const iea = fixture.nativeElement.querySelector(
      '[data-testid="indirect-emissions-allocation"]',
    ) as HTMLElement | null;
    const genericHeading = Array.from(
      fixture.nativeElement.querySelectorAll('h2'),
    ).find((el) => (el as HTMLElement).textContent?.includes('Generic allocation rules')) as
      | HTMLElement
      | undefined;
    expect(dea).toBeTruthy();
    expect(iea).toBeTruthy();
    expect(genericHeading).toBeTruthy();
    const deaPos = dea!.compareDocumentPosition(iea!);
    expect(deaPos & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const ieaPos = iea!.compareDocumentPosition(genericHeading!);
    expect(ieaPos & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const labels = Array.from(
      fixture.nativeElement.querySelectorAll('.mdc-tab__text-label'),
    ) as HTMLElement[];
    const factors = labels.find((el) => el.textContent?.includes('Factors'));
    factors?.click();
    fixture.detectChanges();
    const factorText = fixture.nativeElement.textContent as string;
    expect(factorText).toContain('Factor resolution');
    expect(factorText).toContain('Add primary property');
    expect(factorText.toLowerCase()).not.toContain('hesaplanan emisyon');

    const calc = labels.find((el) => el.textContent?.includes('Calculation'));
    calc?.click();
    fixture.detectChanges();
    const calcText = fixture.nativeElement.textContent as string;
    expect(calcText).toContain('Basic calculation');
    expect(calcText).toContain('Calculate');
    expect(calcText).toContain('No calculation run has been started for this period.');
    expect(calcText.toLowerCase()).not.toContain('certificate amount');
    expect(calcText.toLowerCase()).not.toContain('financial obligation');

    const report = labels.find((el) => el.textContent?.includes('Report / Excel'));
    report?.click();
    fixture.detectChanges();
    const reportText = fixture.nativeElement.textContent as string;
    expect(reportText).toContain('SKDM Period Summary');
    expect(reportText).toContain('Not Ready');
    expect(reportText).toContain('Production Data');
    expect(reportText).toContain('Excel Mapping');
    expect(reportText).toContain('Generate Excel');
    expect(reportText).toContain('INTERNAL DEVELOPMENT TEMPLATE');
    expect(reportText).toContain('Official Excel');
    expect(reportText).toContain('Generate official Excel');
    expect(reportText).not.toContain('Official CBAM Submit');
    expect(fixture.nativeElement.querySelector('button[data-export-excel]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-testid="official-see-export"]')).toBeTruthy();
  });

  it('Phase 10B: shows Purchased precursors above the generic purchased inputs UI', () => {
    flushBootstrap();
    openPurchasedInputsTab();
    const precursors = fixture.nativeElement.querySelector(
      '[data-testid="purchased-precursors"]',
    ) as HTMLElement | null;
    expect(precursors).toBeTruthy();
    expect(precursors!.textContent).toContain('Purchased precursors');
    expect(precursors!.textContent).toContain(
      'No purchased precursors have been added for this period.',
    );

    const otherHeading = Array.from(fixture.nativeElement.querySelectorAll('h2')).find((el) =>
      (el as HTMLElement).textContent?.includes('Other purchased inputs'),
    ) as HTMLElement | undefined;
    expect(otherHeading).toBeTruthy();
    const order = precursors!.compareDocumentPosition(otherHeading!);
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const tabText = fixture.nativeElement.textContent as string;
    expect(tabText).toContain('No purchased inputs have been added for this period.');
    expect(tabText).toContain('Add purchased input');
    expect(tabText.toUpperCase()).not.toContain('HYBRID');
  });

  it('shows method-dependent fields and production ratio preview', () => {
    flushBootstrap({
      production: [
        {
          id: 'prod-base',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          installationProfileId: 'inst-1',
          productProfileVersionId: null,
          productionDate: null,
          periodStart: null,
          periodEnd: null,
          quantity: '500',
          unit: 't',
          notes: null,
          sourceType: 'MANUAL',
          status: 'active',
          rowVersion: 1,
          profileLinkStatus: 'MISSING',
          profileLinkIssueCodes: ['PRODUCT_PROFILE_REQUIRED'],
        },
        {
          id: 'prod-target',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          installationProfileId: 'inst-1',
          productProfileVersionId: null,
          productionDate: null,
          periodStart: null,
          periodEnd: null,
          quantity: '100',
          unit: 't',
          notes: null,
          sourceType: 'MANUAL',
          status: 'active',
          rowVersion: 1,
          profileLinkStatus: 'MISSING',
          profileLinkIssueCodes: ['PRODUCT_PROFILE_REQUIRED'],
        },
      ],
    });
    openAllocationTab();
    const component = fixture.componentInstance;
    component.allocationForm.patchValue({
      installationProfileId: 'inst-1',
      allocationMethod: 'PRODUCTION_QUANTITY_RATIO',
      numeratorProductionRecordId: 'prod-target',
      denominatorProductionRecordId: 'prod-base',
    });
    fixture.detectChanges();
    const preview = component.productionRatioPreview();
    expect(preview).toEqual({
      target: '100 t',
      base: '500 t',
      ratioPct: '20.00%',
    });
    expect(fixture.nativeElement.textContent).toContain('Target Production');
    expect(fixture.nativeElement.textContent).toContain('20.00%');

    component.allocationForm.patchValue({ allocationMethod: 'MANUAL_RATIO' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Reason');
    expect(fixture.nativeElement.textContent).toContain('explain why you use it');
  });

  it('lists allocation rules/results and hides mutations for viewer', async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [CbamPeriodDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'binding-1' } } },
        },
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
            currentRoles: signal(['viewer']),
          },
        },
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(CbamPeriodDetailComponent);
    fixture.detectChanges();

    flushBootstrap({
      rules: [
        {
          id: 'rule-1',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          installationProfileId: 'inst-1',
          productProfileVersionId: null,
          allocationMethod: 'PRODUCTION_QUANTITY_RATIO',
          name: 'Ratio rule',
          description: null,
          allocationRatio: '0.2',
          numeratorProductionRecordId: null,
          denominatorProductionRecordId: null,
          numeratorQuantity: '100',
          denominatorQuantity: '500',
          quantityUnit: 't',
          rationale: null,
          sourceReference: null,
          status: 'ACTIVE',
          rowVersion: 2,
          archivedAt: null,
        },
      ],
      results: [
        {
          id: 'res-1',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          allocationRuleId: 'rule-1',
          sourceType: 'ACTIVITY_RECORD',
          sourceId: 'act-1',
          sourceQuantity: '100',
          sourceUnit: 'MWh',
          allocationRatio: '0.2',
          allocatedQuantity: '20',
          allocatedUnit: 'MWh',
          allocationMethod: 'PRODUCTION_QUANTITY_RATIO',
          calculationVersion: 'allocation-quantity-v1',
          isCurrent: true,
          supersededAt: null,
          createdAt: '2026-01-01T00:00:00Z',
        },
      ],
    });
    openAllocationTab();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Ratio rule');
    expect(text).toContain('20');
    expect(text).toContain('MWh');
    expect(text).toContain('20.00%');
    expect(text).not.toContain('New allocation rule');
    expect(text).not.toContain('Activate');
    expect(text.toLowerCase()).not.toContain('kg co2e');
  });

  it('surfaces 409 conflict messages from allocation activate', () => {
    flushBootstrap({
      rules: [
        {
          id: 'rule-1',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          installationProfileId: 'inst-1',
          productProfileVersionId: null,
          allocationMethod: 'DIRECT_ASSIGNMENT',
          name: 'Draft',
          description: null,
          allocationRatio: '1',
          numeratorProductionRecordId: null,
          denominatorProductionRecordId: null,
          numeratorQuantity: null,
          denominatorQuantity: null,
          quantityUnit: null,
          rationale: null,
          sourceReference: null,
          status: 'DRAFT',
          rowVersion: 1,
          archivedAt: null,
        },
      ],
    });
    openAllocationTab();
    const component = fixture.componentInstance;
    const rule = component.allocationRules()[0];
    component.activateAllocationRule(rule);
    const base = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
    const req = httpMock.expectOne(`${base}/allocation-rules/rule-1/activate`);
    req.flush(
      { error: { message: 'Stale row version.', code: 'CONFLICT' } },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();
    const msg = component.errorMessage() ?? '';
    expect(msg).toBe(
      'This record was changed by another user. Please refresh the page and try again.',
    );
  });

  it('Phase 6C: product selection loads active ready profiles without auto-select', () => {
    flushBootstrap();
    const component = fixture.componentInstance;
    expect(component.productionForm.controls.productProfileVersionId.value).toBe('');
    component.productionForm.controls.productId.setValue('prod-1');
    fixture.detectChanges();
    const base = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
    const req = httpMock.expectOne(
      (r) =>
        r.url === `${base}/product-profile-versions` &&
        r.params.get('productId') === 'prod-1' &&
        r.params.get('status') === 'active',
    );
    req.flush({
      items: [
        {
          id: 'pp-ready',
          organizationId: 'org-1',
          productId: 'prod-1',
          version: 2,
          status: 'active',
          classificationReady: true,
          productName: 'Screws',
          cnNormalizedCode: '73181595',
          cnDisplayCode: '7318 15 95',
          fieldApplicability: {},
          missingRequirements: [],
          validationIssues: [],
          rowVersion: 1,
        },
        {
          id: 'pp-not-ready',
          organizationId: 'org-1',
          productId: 'prod-1',
          version: 1,
          status: 'active',
          classificationReady: false,
          productName: 'Screws',
          cnNormalizedCode: '73181595',
          cnDisplayCode: '7318 15 95',
          fieldApplicability: {},
          missingRequirements: [],
          validationIssues: [],
          rowVersion: 1,
        },
      ],
      page: 1,
      pageSize: 100,
      totalItems: 2,
      totalPages: 1,
    });
    fixture.detectChanges();
    expect(component.selectableProfiles().map((p) => p.id)).toEqual(['pp-ready']);
    expect(component.productionForm.controls.productProfileVersionId.value).toBe('');
  });

  it('Phase 6C: product change clears selected profile', () => {
    flushBootstrap();
    const component = fixture.componentInstance;
    component.selectableProfiles.set([
      {
        id: 'pp-1',
        organizationId: 'org-1',
        productId: 'prod-1',
        version: 1,
        status: 'active',
        validFrom: null,
        validTo: null,
        classificationReady: true,
        productName: 'Screws',
        cnCodeId: null,
        cnNormalizedCode: '73181595',
        cnDisplayCode: '7318 15 95',
        cnDescription: null,
        cnSector: null,
        cnDatasetCode: null,
        cnDatasetVersion: null,
        fieldApplicability: {
          reducingAgent: true,
          steelMillIdentificationNumber: true,
          percentMn: true,
          percentCr: true,
          percentNi: true,
          percentOtherAlloys: true,
          percentOtherMaterials: true,
        },
        reducingAgent: null,
        steelMillIdentificationNumber: null,
        percentMn: null,
        percentCr: null,
        percentNi: null,
        percentOtherAlloys: null,
        percentOtherMaterials: null,
        missingRequirements: [],
        validationIssues: [],
        rowVersion: 1,
      },
    ]);
    component.productionForm.controls.productId.setValue('prod-1', { emitEvent: false });
    component.productionForm.controls.productProfileVersionId.setValue('pp-1');
    component.productionForm.controls.productId.setValue('prod-2');
    const base = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
    httpMock
      .expectOne(
        (r) =>
          r.url === `${base}/product-profile-versions` &&
          r.params.get('productId') === 'prod-2',
      )
      .flush({ items: [], page: 1, pageSize: 100, totalItems: 0, totalPages: 0 });
    expect(component.productionForm.controls.productProfileVersionId.value).toBe('');
  });

  it('Phase 6C: shows backend profileLinkStatus and summary, not page-derived readiness', () => {
    flushBootstrap({
      production: [
        {
          id: 'prod-legacy',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          installationProfileId: 'inst-1',
          productProfileVersionId: null,
          productName: null,
          profileVersion: null,
          productionDate: null,
          periodStart: null,
          periodEnd: null,
          quantity: '10',
          unit: 't',
          notes: null,
          sourceType: 'MANUAL',
          status: 'active',
          rowVersion: 1,
          profileLinkStatus: 'MISSING',
          profileLinkIssueCodes: ['PRODUCT_PROFILE_REQUIRED'],
        },
      ],
      linkSummary: {
        eligibleRecordCount: 0,
        missingProfileCount: 1,
        outdatedProfileCount: 0,
        invalidProfileCount: 0,
        activeRecordCount: 1,
        allocationProfileReady: false,
        blockingIssueCodes: ['PRODUCTION_PROFILE_LINK_MISSING'],
      },
    });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Profile missing');
    expect(text).toContain('1 missing');
    expect(text).toContain('not ready for allocation yet');
    expect(text).toContain('Link profile');
    expect(fixture.componentInstance.profileLinkLabel('UNKNOWN' as never)).toContain('unknown');
  });

  it('Phase 6C: viewer cannot mutate production', async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [CbamPeriodDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'binding-1' } } },
        },
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
            currentRoles: signal(['viewer']),
          },
        },
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(CbamPeriodDetailComponent);
    fixture.detectChanges();
    flushBootstrap({
      production: [
        {
          id: 'prod-legacy',
          organizationId: 'org-1',
          reportingPeriodBindingId: 'binding-1',
          installationProfileId: 'inst-1',
          productProfileVersionId: null,
          productionDate: null,
          periodStart: null,
          periodEnd: null,
          quantity: '10',
          unit: 't',
          notes: null,
          sourceType: 'MANUAL',
          status: 'active',
          rowVersion: 1,
          profileLinkStatus: 'MISSING',
          profileLinkIssueCodes: ['PRODUCT_PROFILE_REQUIRED'],
        },
      ],
    });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Profile missing');
    expect(text).not.toContain('Add production');
    expect(text).not.toContain('Link profile');
    expect(text).not.toContain('Archive');
  });
});
