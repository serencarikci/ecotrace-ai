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
    httpMock.verify();
  });

  function flushBootstrap(options?: {
    roles?: string[];
    production?: unknown[];
    rules?: unknown[];
    results?: unknown[];
    runs?: Array<{ id: string; status: string; calculatedCount: number; blockedCount: number; invalidCount: number; primaryFactorCount: number; defaultFactorCount: number }>;
    calcResults?: unknown[];
  }): void {
    const base = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
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
      .expectOne(`${base}/reporting-period-bindings/binding-1/production-records?page=1&pageSize=20`)
      .flush({
        items: options?.production ?? [],
        page: 1,
        pageSize: 20,
        totalItems: (options?.production ?? []).length,
        totalPages: 1,
      });
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
      warnings: ['Official CBAM workbook mapping is BLOCKED'],
      officialMappingBlocked: true,
      suggestedTemplateId: 'tpl-1',
      calculationRunId: null,
    });
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
  }

  it('renders period tabs including Allocation and Report / Excel for configure roles', () => {
    flushBootstrap();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Production');
    expect(text).toContain('Activities');
    expect(text).toContain('Purchased Inputs');
    expect(text).toContain('Allocation');
    expect(text).toContain('Factors');
    expect(text).toContain('Calculation');
    expect(text).toContain('Report / Excel');
    expect(text).toContain('No production data has been added for this period.');
    expect(text.toLowerCase()).not.toContain('emission factor');
    expect(text.toLowerCase()).not.toContain('certificate amount');

    openAllocationTab();
    const allocText = fixture.nativeElement.textContent as string;
    expect(allocText).toContain('how much of a shared amount belongs to this product');
    expect(allocText).toContain('New allocation rule');
    expect(allocText).toContain('No allocation rules have been added for this period.');
    expect(allocText.toLowerCase()).not.toContain('emission factor');

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
    expect(reportText).not.toContain('Official CBAM Submit');
    expect(reportText).toContain('Generate Excel');
    expect(fixture.nativeElement.querySelector('button[data-export-excel]')).toBeTruthy();
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
});
