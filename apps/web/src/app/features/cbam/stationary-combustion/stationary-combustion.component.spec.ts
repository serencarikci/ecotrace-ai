import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamActivityRecord,
  CbamStationaryCombustionActivityCoverageItem,
  CbamStationaryCombustionFuel,
  CbamStationaryCombustionParameters,
  CbamStationaryCombustionPeriodSummary,
  CbamStationaryCombustionResultDetail,
  CbamStationaryCombustionResultSummary,
} from '../cbam-api.service';
import {
  CbamStationaryCombustionComponent,
  coverageStatusLabel,
  formatDecimalDisplay,
  isEligibleStationaryActivity,
  mapBlockingIssue,
  mapCoverageToCalcState,
  mapReadinessStatus,
  mapStaleReasonCode,
  mapStationaryCombustionError,
  readinessLabel,
  resultStatusLabel,
} from './stationary-combustion.component';

describe('CbamStationaryCombustionComponent', () => {
  let fixture: ComponentFixture<CbamStationaryCombustionComponent>;
  let component: CbamStationaryCombustionComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const periodBase = `${environment.apiUrl}${environment.apiV1Prefix}/organizations/org-1/reporting-periods`;

  const ngFuel: CbamStationaryCombustionFuel = {
    code: 'NATURAL_GAS',
    name: 'Natural gas',
    inputBasis: 'VOLUME',
    defaultActivityUnit: 'Sm3',
    densityRequired: true,
    status: 'ACTIVE',
  };

  const dieselMass: CbamStationaryCombustionFuel = {
    code: 'DIESEL',
    name: 'Diesel',
    inputBasis: 'MASS',
    defaultActivityUnit: 't',
    densityRequired: false,
    status: 'ACTIVE',
  };

  const eligibleActivity: CbamActivityRecord = {
    id: 'act-1',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    installationProfileId: 'inst-1',
    activityGroup: 'COMBUSTION',
    activityType: 'NATURAL_GAS',
    activityDate: '2024-01-15',
    quantity: '105437.03007519',
    unit: 'Sm3',
    dataSourceType: 'PRIMARY',
    sourceReference: null,
    notes: null,
    status: 'active',
    rowVersion: 1,
  };

  const ineligibleElectricity: CbamActivityRecord = {
    ...eligibleActivity,
    id: 'act-el',
    activityType: 'ELECTRICITY',
    unit: 'kWh',
  };

  const params: CbamStationaryCombustionParameters = {
    fuelCode: 'NATURAL_GAS',
    fuelName: 'Natural gas',
    inputBasis: 'VOLUME',
    defaultActivityUnit: 'Sm3',
    densityRequired: true,
    referenceDensity: null,
    referenceDensityUnit: null,
    netCalorificValue: '48',
    netCalorificValueUnit: 'TJ/Gg',
    fossilCo2EmissionFactor: '56100',
    fossilCo2EmissionFactorUnit: 'kgCO2/TJ',
    oxidationFactor: '1',
    datasetCode: 'IPCC_2006',
    datasetVersion: '2006_V1',
    validFrom: '2006-01-01',
    validUntil: null,
    ncvSource: {
      referenceSourceId: 'src-1',
      sourceDocument: 'IPCC 2006',
      sourceTable: 'Table 1.2',
    },
    co2Source: {
      referenceSourceId: 'src-1',
      sourceDocument: 'IPCC 2006',
      sourceTable: 'Table 2.2',
    },
    oxidationSource: {
      referenceSourceId: 'src-1',
      sourceDocument: 'IPCC 2006',
      sourceTable: 'Table 1.4',
    },
    resolutionStatus: 'RESOLVED',
    parameterSetId: 'ps-1',
  };

  const summary: CbamStationaryCombustionResultSummary = {
    resultId: 'res-1',
    runId: 'run-1',
    activityRecordId: 'act-1',
    fuelCode: 'NATURAL_GAS',
    activityQuantity: '105437.03007519',
    activityUnit: 'Sm3',
    energyContentTj: '3.390',
    fossilCo2Tonnes: '190.22695917',
    resultValue: '190.22695917',
    resultUnit: 'tCO2',
    datasetVersion: '2006_V1',
    clientRequestId: '11111111-1111-4111-8111-111111111111',
    createdAt: '2024-06-01T10:00:00Z',
    isCurrent: true,
    isStale: false,
  };

  const missingCoverage: CbamStationaryCombustionActivityCoverageItem = {
    activityRecordId: 'act-1',
    activityDate: '2024-01-15',
    effectiveReferenceDate: '2024-01-15',
    activityType: 'NATURAL_GAS',
    fuelCode: 'NATURAL_GAS',
    fuelName: 'Natural gas',
    quantity: '105437.03007519',
    unit: 'Sm3',
    coverageStatus: 'MISSING',
    currentResultId: null,
    currentRunId: null,
    currentResultCreatedAt: null,
    currentResultValue: null,
    currentResultUnit: null,
    staleReasonCodes: [],
    blockingIssueCodes: ['MISSING_CALCULATION'],
  };

  const currentCoverage: CbamStationaryCombustionActivityCoverageItem = {
    ...missingCoverage,
    coverageStatus: 'CURRENT',
    currentResultId: 'res-1',
    currentRunId: 'run-1',
    currentResultCreatedAt: '2024-06-01T10:00:00Z',
    currentResultValue: '190.22695917',
    currentResultUnit: 'tCO2',
    staleReasonCodes: [],
    blockingIssueCodes: [],
  };

  const staleCoverage: CbamStationaryCombustionActivityCoverageItem = {
    ...currentCoverage,
    coverageStatus: 'STALE',
    staleReasonCodes: ['QUANTITY_CHANGED'],
    blockingIssueCodes: ['QUANTITY_CHANGED'],
  };

  const incompletePeriodSummary: CbamStationaryCombustionPeriodSummary = {
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    periodStart: '2024-01-01',
    periodEnd: '2024-03-31',
    periodType: 'custom',
    eligibleActivityCount: 1,
    currentResultCount: 0,
    validCurrentResultCount: 0,
    missingResultCount: 1,
    staleResultCount: 0,
    excludedResultCount: 0,
    isComplete: false,
    readinessStatus: 'INCOMPLETE',
    blockingIssues: ['1 eligible fuel-use record(s) have no current calculation.'],
    totalFuelMassKg: '0',
    totalFuelMassGg: '0',
    totalEnergyContentTj: '0',
    totalFossilCo2Kg: '0',
    totalFossilCo2Tonnes: '0',
    finalResultValue: '0.00000000',
    finalResultUnit: 'tCO2',
    totalsByFuel: [],
  };

  const readyPeriodSummary: CbamStationaryCombustionPeriodSummary = {
    ...incompletePeriodSummary,
    currentResultCount: 1,
    validCurrentResultCount: 1,
    missingResultCount: 0,
    isComplete: true,
    readinessStatus: 'READY',
    blockingIssues: [],
    totalFuelMassKg: '70642.810150377300000000',
    totalFuelMassGg: '0.070642810150377300',
    totalEnergyContentTj: '3.390854887218110400',
    totalFossilCo2Kg: '190226.959172935993440000',
    totalFossilCo2Tonnes: '190.226959172935993440',
    finalResultValue: '190.22695917',
    totalsByFuel: [
      {
        fuelCode: 'NATURAL_GAS',
        fuelName: 'Natural gas',
        activityCount: 1,
        totalFuelMassKg: '70642.810150377300000000',
        totalEnergyContentTj: '3.390854887218110400',
        totalFossilCo2Tonnes: '190.226959172935993440',
        finalResultValue: '190.22695917',
        resultUnit: 'tCO2',
      },
    ],
  };

  const emptyPeriodSummary: CbamStationaryCombustionPeriodSummary = {
    ...incompletePeriodSummary,
    eligibleActivityCount: 0,
    missingResultCount: 0,
    readinessStatus: 'EMPTY',
    blockingIssues: [],
  };

  const detail: CbamStationaryCombustionResultDetail = {
    id: 'res-1',
    organizationId: 'org-1',
    calculationRunId: 'run-1',
    calculationDefinitionId: 'def-1',
    reportingPeriodBindingId: 'binding-1',
    activityRecordId: 'act-1',
    fuelId: 'fuel-1',
    parameterSetId: 'ps-1',
    calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
    formulaVersion: 'STATIONARY_COMBUSTION_CO2_V1',
    fuelCode: 'NATURAL_GAS',
    fuelName: 'Natural gas',
    inputBasis: 'VOLUME',
    activityQuantity: '105437.03007519',
    activityUnit: 'Sm3',
    densityValue: '0.67',
    densityUnit: 'kg/Sm3',
    clientRequestId: '11111111-1111-4111-8111-111111111111',
    requestFingerprint: 'abc',
    calculationReferenceDate: '2024-01-15',
    netCalorificValue: '48',
    netCalorificValueUnit: 'TJ/Gg',
    fossilCo2EmissionFactor: '56100',
    fossilCo2EmissionFactorUnit: 'kgCO2/TJ',
    oxidationFactor: '1',
    datasetCode: 'IPCC_2006',
    datasetVersion: '2006_V1',
    validFrom: '2006-01-01',
    validUntil: null,
    ncvReferenceSourceId: 'src-1',
    ncvSourceDocument: 'IPCC 2006',
    ncvSourceTable: 'Table 1.2',
    co2ReferenceSourceId: 'src-1',
    co2SourceDocument: 'IPCC 2006',
    co2SourceTable: 'Table 2.2',
    oxidationReferenceSourceId: 'src-1',
    oxidationSourceDocument: 'IPCC 2006',
    oxidationSourceTable: 'Table 1.4',
    fuelMassKg: '70642.81',
    fuelMassGg: '0.07064281',
    energyContentTj: '3.39085488',
    fossilCo2Kg: '190226.95917',
    fossilCo2Tonnes: '190.22695917',
    resultValue: '190.22695917',
    resultUnit: 'tCO2',
    createdByUserId: 'user-1',
    createdAt: '2024-06-01T10:00:00Z',
    isCurrent: true,
    isStale: false,
  };

  function flushPeriodSummary(body: CbamStationaryCombustionPeriodSummary = incompletePeriodSummary): void {
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/summary`,
      )
      .flush(body);
  }

  function coverageUrl(page = 1, pageSize = 20): string {
    return `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/activity-coverage?page=${page}&pageSize=${pageSize}`;
  }

  function flushCoverage(
    items: CbamStationaryCombustionActivityCoverageItem[] = [missingCoverage],
    page = 1,
    pageSize = 20,
  ): void {
    httpMock.expectOne(coverageUrl(page, pageSize)).flush({
      items,
      page,
      pageSize,
      totalItems: items.length,
      totalPages: items.length === 0 ? 0 : 1,
    });
  }

  function defaultCoverageForBootstrap(options?: {
    activities?: CbamActivityRecord[];
    results?: CbamStationaryCombustionResultSummary[];
    periodSummary?: CbamStationaryCombustionPeriodSummary;
    coverage?: CbamStationaryCombustionActivityCoverageItem[];
  }): CbamStationaryCombustionActivityCoverageItem[] {
    if (options?.coverage) {
      return options.coverage;
    }
    const activities = options?.activities ?? [eligibleActivity, ineligibleElectricity];
    const eligible = activities.filter((a) =>
      isEligibleStationaryActivity(a, [ngFuel, dieselMass]),
    );
    if (eligible.length === 0) {
      return [];
    }
    const summaryStatus = options?.periodSummary?.readinessStatus;
    const results = options?.results ?? [];
    return eligible.map((activity) => {
      const current = results.find((r) => r.activityRecordId === activity.id && r.isCurrent);
      if (current?.isStale || summaryStatus === 'STALE') {
        return {
          ...staleCoverage,
          activityRecordId: activity.id,
          activityDate: activity.activityDate,
          effectiveReferenceDate: activity.activityDate,
          activityType: activity.activityType,
          fuelCode: activity.activityType,
          quantity: activity.quantity,
          unit: activity.unit,
          currentResultId: current?.resultId ?? 'res-1',
          currentRunId: current?.runId ?? 'run-1',
          currentResultValue: current?.resultValue ?? staleCoverage.currentResultValue,
        };
      }
      if (current && !current.isStale) {
        return {
          ...currentCoverage,
          activityRecordId: activity.id,
          activityDate: activity.activityDate,
          effectiveReferenceDate: activity.activityDate,
          activityType: activity.activityType,
          fuelCode: activity.activityType,
          quantity: activity.quantity,
          unit: activity.unit,
          currentResultId: current.resultId,
          currentRunId: current.runId,
          currentResultValue: current.resultValue,
        };
      }
      return {
        ...missingCoverage,
        activityRecordId: activity.id,
        activityDate: activity.activityDate,
        effectiveReferenceDate: activity.activityDate,
        activityType: activity.activityType,
        fuelCode: activity.activityType,
        quantity: activity.quantity,
        unit: activity.unit,
      };
    });
  }

  function flushBootstrap(options?: {
    activities?: CbamActivityRecord[];
    fuels?: CbamStationaryCombustionFuel[];
    results?: CbamStationaryCombustionResultSummary[];
    periodSummary?: CbamStationaryCombustionPeriodSummary;
    coverage?: CbamStationaryCombustionActivityCoverageItem[];
  }): void {
    httpMock
      .expectOne(`${orgBase}/stationary-combustion/fuels`)
      .flush(options?.fuels ?? [ngFuel, dieselMass]);
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/activity-records?page=1&pageSize=100`,
      )
      .flush({
        items: options?.activities ?? [eligibleActivity, ineligibleElectricity],
        page: 1,
        pageSize: 100,
        totalItems: (options?.activities ?? [eligibleActivity, ineligibleElectricity]).length,
        totalPages: 1,
      });
    httpMock.expectOne(`${periodBase}/rp-1`).flush({
      id: 'rp-1',
      organizationId: 'org-1',
      code: 'P1',
      name: 'Period',
      periodType: 'custom',
      startDate: '2024-01-01',
      endDate: '2024-03-31',
      status: 'open',
      lockedAt: null,
      lockedByUserId: null,
    });
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results?page=1&pageSize=20`,
      )
      .flush({
        items: options?.results ?? [],
        page: 1,
        pageSize: 20,
        totalItems: (options?.results ?? []).length,
        totalPages: 1,
      });
    flushPeriodSummary(options?.periodSummary ?? incompletePeriodSummary);
    flushCoverage(defaultCoverageForBootstrap(options));
  }

  function flushAfterSuccessfulExecution(options?: {
    results?: CbamStationaryCombustionResultSummary[];
    detail?: CbamStationaryCombustionResultDetail;
    periodSummary?: CbamStationaryCombustionPeriodSummary;
    coverage?: CbamStationaryCombustionActivityCoverageItem[];
    resultId?: string;
  }): void {
    const resultId = options?.resultId ?? 'res-1';
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results?page=1&pageSize=20`,
      )
      .flush({
        items: options?.results ?? [summary],
        page: 1,
        pageSize: 20,
        totalItems: (options?.results ?? [summary]).length,
        totalPages: 1,
      });
    flushPeriodSummary(options?.periodSummary ?? readyPeriodSummary);
    flushCoverage(
      options?.coverage ?? [
        {
          ...currentCoverage,
          currentResultId: resultId,
          currentResultValue:
            options?.detail?.resultValue ?? currentCoverage.currentResultValue,
        },
      ],
    );
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results/${resultId}`,
      )
      .flush(options?.detail ?? { ...detail, id: resultId });
  }

  function flushParameterRequests(referenceDate = '2024-01-15'): void {
    const reqs = httpMock.match(
      (r) =>
        r.url.includes('/stationary-combustion/fuels/') &&
        r.url.includes('/parameters') &&
        r.params.get('referenceDate') === referenceDate,
    );
    expect(reqs.length).toBeGreaterThan(0);
    for (const req of reqs) {
      req.flush(params);
    }
  }

  function selectEligibleAndLoadParams(): void {
    component.form.controls.activityRecordId.setValue('act-1');
    component.onActivityChange();
    fixture.detectChanges();
    flushParameterRequests();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamStationaryCombustionComponent],
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
    fixture = TestBed.createComponent(CbamStationaryCombustionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('bindingId', 'binding-1');
    fixture.componentRef.setInput('reportingPeriodId', 'rp-1');
    fixture.componentRef.setInput('canConfigure', true);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock?.verify();
  });

  it('renders for view users and loads fuels and eligible activities', () => {
    fixture.componentRef.setInput('canConfigure', false);
    flushBootstrap();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Direct Emissions');
    expect(component.fuels().some((f) => f.code === 'NATURAL_GAS')).toBeTrue();
    expect(component.eligibleActivities().map((a) => a.id)).toEqual(['act-1']);
    expect(component.eligibleActivities().some((a) => a.id === 'act-el')).toBeFalse();
  });

  it('shows empty eligible-activity state', () => {
    flushBootstrap({
      activities: [ineligibleElectricity],
      periodSummary: emptyPeriodSummary,
      coverage: [],
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No fuel use records');
  });

  it('keeps activity quantity and unit read-only', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    expect(fixture.nativeElement.textContent).toContain('105437.03007519');
    expect(fixture.nativeElement.textContent).toContain('Sm3');
    expect(fixture.nativeElement.querySelector('input[formcontrolname="quantity"]')).toBeNull();
  });

  it('uses activity date when present and does not require calculation date', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    expect(component.effectiveReferenceDate()).toBe('2024-01-15');
    expect(fixture.nativeElement.textContent).not.toContain('Calculation date');
  });

  it('requires reference date when activity date is absent', () => {
    flushBootstrap({
      activities: [{ ...eligibleActivity, activityDate: null }],
    });
    fixture.detectChanges();
    component.form.controls.activityRecordId.setValue('act-1');
    component.onActivityChange();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Calculation date');
    expect(component.canSubmit()).toBeFalse();
  });

  it('blocks submit when reference date is outside the period', () => {
    flushBootstrap({
      activities: [{ ...eligibleActivity, activityDate: null }],
    });
    fixture.detectChanges();
    component.form.patchValue({
      activityRecordId: 'act-1',
      calculationReferenceDate: '2025-01-01',
      densityValue: '0.67',
    });
    component.onActivityChange();
    component.form.controls.calculationReferenceDate.setValue('2025-01-01');
    fixture.detectChanges();
    expect(component.referenceDateOutsidePeriod()).toBeTrue();
    expect(component.canSubmit()).toBeFalse();
  });

  it('loads parameters and disables Calculate while loading', fakeAsync(() => {
    flushBootstrap();
    component.form.controls.activityRecordId.setValue('act-1');
    component.onActivityChange();
    fixture.detectChanges();
    expect(component.loadingParameters()).toBeTrue();
    expect(component.canSubmit()).toBeFalse();
    flushParameterRequests();
    tick();
    fixture.detectChanges();
    expect(component.loadingParameters()).toBeFalse();
    expect(component.parameters()?.netCalorificValue).toBe('48');
  }));

  it('disables Calculate on parameter error', () => {
    flushBootstrap();
    component.form.controls.activityRecordId.setValue('act-1');
    component.onActivityChange();
    fixture.detectChanges();
    const reqs = httpMock.match((r) => r.url.includes('/parameters'));
    expect(reqs.length).toBeGreaterThan(0);
    for (const req of reqs) {
      req.flush(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Unresolved',
            details: [{ code: 'UNRESOLVED_PARAMETER_SET', message: 'x' }],
            requestId: null,
          },
        },
        { status: 422, statusText: 'Unprocessable' },
      );
    }
    fixture.detectChanges();
    expect(component.parameterError()).toContain('No reference values are available');
    expect(component.canSubmit()).toBeFalse();
  });

  it('shows VOLUME density empty without 0.67/0.68 defaults', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    expect(fixture.nativeElement.textContent).toContain('Density');
    expect(component.form.controls.densityValue.value).toBe('');
    expect(fixture.nativeElement.textContent).not.toContain('0.67');
    expect(fixture.nativeElement.textContent).not.toContain('0.68');
  });

  it('rejects missing zero and negative density', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    expect(component.canSubmit()).toBeFalse();
    component.form.controls.densityValue.setValue('0');
    fixture.detectChanges();
    expect(component.densityInvalid()).toBeTrue();
    expect(component.canSubmit()).toBeFalse();
    component.form.controls.densityValue.setValue('-1');
    fixture.detectChanges();
    expect(component.densityInvalid()).toBeTrue();
  });

  it('hides density for MASS fuel and omits density on submit', () => {
    const massActivity: CbamActivityRecord = {
      ...eligibleActivity,
      id: 'act-mass',
      activityType: 'DIESEL',
      unit: 't',
      quantity: '10',
    };
    flushBootstrap({ activities: [massActivity], fuels: [dieselMass] });
    fixture.detectChanges();
    component.form.controls.activityRecordId.setValue('act-mass');
    component.onActivityChange();
    fixture.detectChanges();
    const dieselParams = httpMock.match((r) => r.url.includes('/fuels/DIESEL/parameters'));
    expect(dieselParams.length).toBeGreaterThan(0);
    for (const req of dieselParams) {
      req.flush({
        ...params,
        fuelCode: 'DIESEL',
        fuelName: 'Diesel',
        inputBasis: 'MASS',
        densityRequired: false,
      });
    }
    fixture.detectChanges();
    expect(component.densityRequired()).toBeFalse();
    expect(fixture.nativeElement.textContent).not.toContain('Enter the fuel density');
    component.calculate();
    const exec = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    expect(exec.request.body.densityValue).toBeUndefined();
    expect(exec.request.body.densityUnit).toBeUndefined();
    expect(exec.request.body.clientRequestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    exec.flush({
      runId: 'run-1',
      resultId: 'res-1',
      status: 'COMPLETED',
      calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
      calculationVersion: 'v1',
      activityRecordId: 'act-mass',
      fuelCode: 'DIESEL',
      referenceDate: '2024-01-15',
      resultValue: '1',
      resultUnit: 'tCO2',
      clientRequestId: exec.request.body.clientRequestId,
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushAfterSuccessfulExecution({
      results: [],
      detail: {
        ...detail,
        id: 'res-1',
        fuelCode: 'DIESEL',
        fuelName: 'Diesel',
        densityValue: null,
        isCurrent: true,
        isStale: false,
      },
    });
  });

  it('blocks calculate without configure permission', () => {
    fixture.componentRef.setInput('canConfigure', false);
    flushBootstrap();
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    expect(component.canSubmit()).toBeFalse();
    expect(fixture.nativeElement.textContent).toContain('cannot run a calculation');
  });

  it('sends one request on double click and keeps clientRequestId on transport retry', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.calculate();
    component.calculate();
    const execs = httpMock.match(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    expect(execs.length).toBe(1);
    const firstId = execs[0].request.body.clientRequestId as string;
    execs[0].flush(
      { error: { code: 'INTERNAL_ERROR', message: 'down', details: [], requestId: null } },
      { status: 503, statusText: 'Unavailable' },
    );
    fixture.detectChanges();
    expect(component.getActiveClientRequestIdForTests()).toBe(firstId);
    component.calculate();
    const retry = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    expect(retry.request.body.clientRequestId).toBe(firstId);
    retry.flush({
      runId: 'run-1',
      resultId: 'res-1',
      status: 'COMPLETED',
      calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
      calculationVersion: 'v1',
      activityRecordId: 'act-1',
      fuelCode: 'NATURAL_GAS',
      referenceDate: '2024-01-15',
      resultValue: '190.22695917',
      resultUnit: 'tCO2',
      clientRequestId: firstId,
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushAfterSuccessfulExecution();
  });

  it('invalidates clientRequestId when material input changes and Calculate again uses a new id', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.calculate();
    const first = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    const firstId = first.request.body.clientRequestId as string;
    first.flush(
      { error: { code: 'INTERNAL_ERROR', message: 'x', details: [], requestId: null } },
      { status: 500, statusText: 'Error' },
    );
    component.form.controls.densityValue.setValue('0.68');
    fixture.detectChanges();
    expect(component.getActiveClientRequestIdForTests()).toBeNull();
    component.calculate();
    const second = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    expect(second.request.body.clientRequestId).not.toBe(firstId);
    second.flush({
      runId: 'run-2',
      resultId: 'res-2',
      status: 'COMPLETED',
      calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
      calculationVersion: 'v1',
      activityRecordId: 'act-1',
      fuelCode: 'NATURAL_GAS',
      referenceDate: '2024-01-15',
      resultValue: '190.22695917',
      resultUnit: 'tCO2',
      clientRequestId: second.request.body.clientRequestId,
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushAfterSuccessfulExecution({
      results: [],
      resultId: 'res-2',
      detail: { ...detail, id: 'res-2' },
    });
    const afterSuccess = component.getActiveClientRequestIdForTests();
    expect(afterSuccess).toBeNull();
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.calculateAgain();
    const again = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    expect(again.request.body.clientRequestId).not.toBe(second.request.body.clientRequestId);
    again.flush({
      runId: 'run-3',
      resultId: 'res-3',
      status: 'COMPLETED',
      calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
      calculationVersion: 'v1',
      activityRecordId: 'act-1',
      fuelCode: 'NATURAL_GAS',
      referenceDate: '2024-01-15',
      resultValue: '190.22695917',
      resultUnit: 'tCO2',
      clientRequestId: again.request.body.clientRequestId,
      idempotentReplay: false,
      createdAt: '2024-06-01T10:00:00Z',
    });
    flushAfterSuccessfulExecution({
      results: [],
      resultId: 'res-3',
      detail: { ...detail, id: 'res-3' },
    });
  });

  it('handles 201 create and 200 replay without list duplication semantics', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.calculate();
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
      )
      .flush({
        runId: 'run-1',
        resultId: 'res-1',
        status: 'COMPLETED',
        calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
        calculationVersion: 'v1',
        activityRecordId: 'act-1',
        fuelCode: 'NATURAL_GAS',
        referenceDate: '2024-01-15',
        resultValue: '190.22695917',
        resultUnit: 'tCO2',
        clientRequestId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        idempotentReplay: false,
        createdAt: '2024-06-01T10:00:00Z',
      });
    flushAfterSuccessfulExecution();
    fixture.detectChanges();
    expect(component.successMessage()).toBe('Calculation saved.');
    expect(component.results().length).toBe(1);

    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.calculate();
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
      )
      .flush({
        runId: 'run-1',
        resultId: 'res-1',
        status: 'COMPLETED',
        calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
        calculationVersion: 'v1',
        activityRecordId: 'act-1',
        fuelCode: 'NATURAL_GAS',
        referenceDate: '2024-01-15',
        resultValue: '190.22695917',
        resultUnit: 'tCO2',
        clientRequestId: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        idempotentReplay: true,
        createdAt: '2024-06-01T10:00:00Z',
      });
    flushAfterSuccessfulExecution();
    fixture.detectChanges();
    expect(component.successMessage()).toContain('already completed');
    expect(component.results().length).toBe(1);
  });

  it('clears stale request state on IDEMPOTENCY_KEY_REUSED', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.seedActiveClientRequestIdForTests('old-id', '{"x":1}');
    component.calculate();
    // material mismatch regenerates id — force reuse path via response
    const exec = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    exec.flush(
      {
        error: {
          code: 'IDEMPOTENCY_KEY_REUSED',
          message: 'reused',
          details: [{ code: 'IDEMPOTENCY_KEY_REUSED' }],
          requestId: null,
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();
    expect(component.formError()).toContain('Start a new calculation');
    expect(component.getActiveClientRequestIdForTests()).toBeNull();
  });

  it('lists results with pagination params and shows loading empty error states', () => {
    flushBootstrap({ results: [] });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No calculations saved');

    component.onResultsPage({ pageIndex: 1, pageSize: 10, length: 30 } as never);
    const pageReq = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results?page=2&pageSize=10`,
    );
    pageReq.flush({ items: [summary], page: 2, pageSize: 10, totalItems: 21, totalPages: 3 });
    fixture.detectChanges();
    expect(component.results().length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('190.22695917');
  });

  it('loads snapshot detail with provenance and intermediates', () => {
    flushBootstrap({ results: [summary] });
    fixture.detectChanges();
    component.viewDetails('res-1');
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results/res-1`,
      )
      .flush(detail);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Table 1.2');
    expect(text).toContain('Fuel mass');
    expect(text).toContain('190.22695917');
    expect(text).toContain('Client request ID');
  });

  it('maps backend error codes to simple messages', () => {
    flushBootstrap();
    expect(
      mapStationaryCombustionError(
        new HttpErrorResponse({
          status: 422,
          error: {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'x',
              details: [{ code: 'DENSITY_REQUIRED' }],
              requestId: null,
            },
          },
        }),
      ),
    ).toBe('Enter the fuel density.');
    expect(
      mapStationaryCombustionError(
        new HttpErrorResponse({
          status: 422,
          error: {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'x',
              details: [{ code: 'INCOMPATIBLE_UNIT' }],
              requestId: null,
            },
          },
        }),
      ),
    ).toBe('The unit is not valid for this fuel.');
  });

  it('marks ineligible activities as not submittable', () => {
    flushBootstrap();
    expect(isEligibleStationaryActivity(ineligibleElectricity, [ngFuel])).toBeFalse();
    expect(isEligibleStationaryActivity(eligibleActivity, [ngFuel])).toBeTrue();
  });

  it('shows reference values as read-only text', () => {
    flushBootstrap();
    selectEligibleAndLoadParams();
    expect(fixture.nativeElement.textContent).toContain('48');
    expect(fixture.nativeElement.textContent).toContain('56100');
    expect(fixture.debugElement.query(By.css('input[formcontrolname="netCalorificValue"]'))).toBeNull();
  });
  it('loads period summary for the current organization and binding', () => {
    flushBootstrap({ periodSummary: readyPeriodSummary });
    fixture.detectChanges();
    expect(component.periodSummary()?.reportingPeriodBindingId).toBe('binding-1');
    expect(fixture.nativeElement.textContent).toContain('Period Summary');
    expect(fixture.nativeElement.textContent).toContain('Ready');
  });

  it('maps EMPTY readiness to No fuel use records and Go to Activities', () => {
    flushBootstrap({
      activities: [ineligibleElectricity],
      periodSummary: emptyPeriodSummary,
      coverage: [],
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No fuel use records');
    expect(fixture.nativeElement.textContent).toContain('Go to Activities');
    expect(fixture.nativeElement.textContent).toContain('No totals yet.');
    expect(fixture.nativeElement.textContent).not.toContain('Current calculated total');
  });

  it('shows Incomplete with missing count and blocking issues', () => {
    flushBootstrap();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Incomplete');
    expect(fixture.nativeElement.textContent).toContain('Missing calculations: 1');
    expect(fixture.nativeElement.textContent).toContain(
      'Some fuel use records still need a calculation.',
    );
    expect(fixture.nativeElement.textContent).toContain('Current calculated total');
  });

  it('shows Needs update for STALE and keeps Current calculated total label', () => {
    flushBootstrap({
      periodSummary: {
        ...incompletePeriodSummary,
        readinessStatus: 'STALE',
        missingResultCount: 0,
        staleResultCount: 1,
        currentResultCount: 1,
        validCurrentResultCount: 0,
        blockingIssues: ['1 current calculation(s) no longer match their fuel-use record.'],
        finalResultValue: '0.00000000',
      },
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Needs update');
    expect(fixture.nativeElement.textContent).toContain('Out-of-date calculations: 1');
    expect(fixture.nativeElement.textContent).toContain('Current calculated total');
  });

  it('exposes both missing and stale issues when incomplete with stale records', () => {
    flushBootstrap({
      periodSummary: {
        ...incompletePeriodSummary,
        missingResultCount: 1,
        staleResultCount: 1,
        blockingIssues: [
          '1 eligible fuel-use record(s) have no current calculation.',
          '1 current calculation(s) no longer match their fuel-use record.',
        ],
      },
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain(
      'Some fuel use records still need a calculation.',
    );
    expect(fixture.nativeElement.textContent).toContain(
      'Some calculations are out of date after fuel use changed.',
    );
  });

  it('does not treat unknown readiness as Ready', () => {
    flushBootstrap({
      periodSummary: { ...incompletePeriodSummary, readinessStatus: 'SOMETHING_ELSE' },
    });
    fixture.detectChanges();
    expect(mapReadinessStatus('SOMETHING_ELSE')).toBe('UNKNOWN');
    expect(fixture.nativeElement.textContent).toContain('Not ready');
    expect(fixture.nativeElement.textContent).toContain('This section is not ready.');
    expect(readinessLabel('UNKNOWN')).not.toBe('Ready');
  });

  it('shows READY totals from backend Decimal strings as tCO2 without recalculating', () => {
    flushBootstrap({ periodSummary: readyPeriodSummary, results: [summary] });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Ready');
    expect(text).toContain('190.22695917');
    expect(text).toContain('tCO2');
    expect(text).not.toContain('CO2e');
    expect(text).toContain('Totals by fuel');
    expect(text).toContain('Natural gas');
    expect(formatDecimalDisplay('190.22695917')).toBe('190.22695917');
    expect(formatDecimalDisplay('0.1')).toBe('0.1');
  });

  it('hides totals-by-fuel table when empty', () => {
    flushBootstrap({ periodSummary: incompletePeriodSummary });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Totals by fuel');
  });

  it('shows Current History and Out of date badges from isCurrent/isStale', () => {
    const history = { ...summary, resultId: 'res-old', isCurrent: false, isStale: false };
    const stale = { ...summary, resultId: 'res-stale', isCurrent: true, isStale: true };
    flushBootstrap({ results: [stale, history] });
    fixture.detectChanges();
    expect(resultStatusLabel(true, false)).toBe('Current');
    expect(resultStatusLabel(false, false)).toBe('History');
    expect(resultStatusLabel(true, true)).toBe('Out of date');
    expect(fixture.nativeElement.textContent).toContain('Out of date');
    expect(fixture.nativeElement.textContent).toContain('History');
  });

  it('keeps stale result detail accessible', () => {
    const staleSummary = { ...summary, isCurrent: true, isStale: true };
    flushBootstrap({ results: [staleSummary] });
    fixture.detectChanges();
    component.viewDetails('res-1');
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results/res-1`,
      )
      .flush({ ...detail, isCurrent: true, isStale: true });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Out of date');
    expect(fixture.nativeElement.textContent).toContain('Result details');
  });

  it('shows Calculate Calculate again and Update calculation by activity state', () => {
    flushBootstrap({ coverage: [missingCoverage], results: [] });
    selectEligibleAndLoadParams();
    expect(component.calculationActionLabel()).toBe('Calculate');

    component.coverageItems.set([currentCoverage]);
    fixture.detectChanges();
    expect(component.calculationActionLabel()).toBe('Calculate again');

    component.coverageItems.set([staleCoverage]);
    fixture.detectChanges();
    expect(component.calculationActionLabel()).toBe('Update calculation');
    expect(fixture.nativeElement.textContent).toContain(
      'The amount changed after the last calculation.',
    );
  });

  it('lets view-only users see summary without calculate action', () => {
    fixture.componentRef.setInput('canConfigure', false);
    flushBootstrap({ periodSummary: readyPeriodSummary, results: [summary] });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Period Summary');
    expect(fixture.nativeElement.textContent).toContain('cannot run a calculation');
    expect(component.canSubmit()).toBeFalse();
  });

  it('refreshes results and summary after successful recalculation', () => {
    flushBootstrap({
      results: [{ ...summary, isCurrent: true, isStale: false }],
      periodSummary: readyPeriodSummary,
      coverage: [currentCoverage],
    });
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.68');
    fixture.detectChanges();
    component.runCalculationAction();
    const exec = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    exec.flush({
      runId: 'run-2',
      resultId: 'res-2',
      status: 'COMPLETED',
      calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
      calculationVersion: 'v1',
      activityRecordId: 'act-1',
      fuelCode: 'NATURAL_GAS',
      referenceDate: '2024-01-15',
      resultValue: '193.00000000',
      resultUnit: 'tCO2',
      clientRequestId: exec.request.body.clientRequestId,
      idempotentReplay: false,
      createdAt: '2024-06-02T10:00:00Z',
    });
    const oldHistory = { ...summary, isCurrent: false, isStale: false };
    const newCurrent = {
      ...summary,
      resultId: 'res-2',
      resultValue: '193.00000000',
      isCurrent: true,
      isStale: false,
    };
    flushAfterSuccessfulExecution({
      results: [newCurrent, oldHistory],
      resultId: 'res-2',
      detail: { ...detail, id: 'res-2', resultValue: '193.00000000', isCurrent: true, isStale: false },
      periodSummary: {
        ...readyPeriodSummary,
        finalResultValue: '193.00000000',
      },
      coverage: [
        {
          ...currentCoverage,
          currentResultId: 'res-2',
          currentResultValue: '193.00000000',
        },
      ],
    });
    fixture.detectChanges();
    expect(component.results().find((r) => r.resultId === 'res-2')?.isCurrent).toBeTrue();
    expect(component.results().find((r) => r.resultId === 'res-1')?.isCurrent).toBeFalse();
    expect(component.periodSummary()?.finalResultValue).toBe('193.00000000');
    expect(component.selectedActivityCalcState()).toBe('valid');
    expect(component.calculationActionLabel()).toBe('Calculate again');
  });

  it('does not optimistically change summary on failed calculation', () => {
    flushBootstrap({ periodSummary: readyPeriodSummary, results: [summary] });
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    const before = component.periodSummary();
    fixture.detectChanges();
    component.calculate();
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
      )
      .flush(
        { error: { code: 'INTERNAL_ERROR', message: 'x', details: [], requestId: null } },
        { status: 500, statusText: 'Error' },
      );
    fixture.detectChanges();
    expect(component.periodSummary()).toEqual(before);
    expect(component.formError()).toBeTruthy();
  });

  it('keeps result history when summary fails and retries', () => {
    httpMock.expectOne(`${orgBase}/stationary-combustion/fuels`).flush([ngFuel]);
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/activity-records?page=1&pageSize=100`,
      )
      .flush({
        items: [eligibleActivity],
        page: 1,
        pageSize: 100,
        totalItems: 1,
        totalPages: 1,
      });
    httpMock.expectOne(`${periodBase}/rp-1`).flush({
      id: 'rp-1',
      organizationId: 'org-1',
      code: 'P1',
      name: 'Period',
      periodType: 'custom',
      startDate: '2024-01-01',
      endDate: '2024-03-31',
      status: 'open',
      lockedAt: null,
      lockedByUserId: null,
    });
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results?page=1&pageSize=20`,
      )
      .flush({ items: [summary], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/summary`,
      )
      .flush(
        { error: { code: 'INTERNAL_ERROR', message: 'down', details: [], requestId: null } },
        { status: 500, statusText: 'Error' },
      );
    flushCoverage([currentCoverage]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('The period summary could not be loaded.');
    expect(fixture.nativeElement.textContent).toContain('Saved results');
    expect(component.results().length).toBe(1);
    component.retrySummary();
    flushPeriodSummary(readyPeriodSummary);
    fixture.detectChanges();
    expect(component.periodSummary()?.readinessStatus).toBe('READY');
  });

  it('shows accessible summary loading state', () => {
    httpMock.expectOne(`${orgBase}/stationary-combustion/fuels`).flush([ngFuel]);
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/activity-records?page=1&pageSize=100`,
      )
      .flush({
        items: [eligibleActivity],
        page: 1,
        pageSize: 100,
        totalItems: 1,
        totalPages: 1,
      });
    httpMock.expectOne(`${periodBase}/rp-1`).flush({
      id: 'rp-1',
      organizationId: 'org-1',
      code: 'P1',
      name: 'Period',
      periodType: 'custom',
      startDate: '2024-01-01',
      endDate: '2024-03-31',
      status: 'open',
      lockedAt: null,
      lockedByUserId: null,
    });
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results?page=1&pageSize=20`,
      )
      .flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    fixture.detectChanges();
    expect(component.loadingSummary()).toBeTrue();
    expect(fixture.nativeElement.querySelector('[aria-label="Loading period summary"]')).toBeTruthy();
    flushPeriodSummary();
    flushCoverage();
    fixture.detectChanges();
    expect(component.loadingSummary()).toBeFalse();
  });

  it('ignores stale parameter responses after rapid selection changes', fakeAsync(() => {
    flushBootstrap({
      activities: [
        eligibleActivity,
        { ...eligibleActivity, id: 'act-2', activityDate: '2024-02-01' },
      ],
    });
    component.form.controls.activityRecordId.setValue('act-1');
    component.onActivityChange();
    fixture.detectChanges();
    const firstReqs = httpMock.match((r) => r.url.includes('/fuels/NATURAL_GAS/parameters'));
    expect(firstReqs.length).toBeGreaterThan(0);
    component.form.controls.activityRecordId.setValue('act-2');
    component.onActivityChange();
    fixture.detectChanges();
    const secondReqs = httpMock.match(
      (r) =>
        r.url.includes('/fuels/NATURAL_GAS/parameters') &&
        r.params.get('referenceDate') === '2024-02-01',
    );
    expect(secondReqs.length).toBeGreaterThan(0);
    // Resolve older request last — must be ignored
    for (const req of firstReqs) {
      if (!req.cancelled) {
        req.flush({ ...params, datasetVersion: 'OLD' });
      }
    }
    for (const req of secondReqs) {
      req.flush({ ...params, datasetVersion: 'NEW' });
    }
    tick();
    fixture.detectChanges();
    expect(component.parameters()?.datasetVersion).toBe('NEW');
  }));


  it('loads activity coverage independently from result history', () => {
    flushBootstrap({
      results: [],
      coverage: [currentCoverage],
      periodSummary: readyPeriodSummary,
    });
    fixture.detectChanges();
    expect(component.coverageItems()[0].coverageStatus).toBe('CURRENT');
    expect(component.results().length).toBe(0);
    selectEligibleAndLoadParams();
    expect(component.calculationActionLabel()).toBe('Calculate again');
  });

  it('does not treat CURRENT as missing when result is absent from history page', () => {
    flushBootstrap({
      results: [],
      coverage: [currentCoverage],
      periodSummary: readyPeriodSummary,
    });
    selectEligibleAndLoadParams();
    expect(component.selectedActivityCalcState()).toBe('valid');
    expect(component.calculationActionLabel()).toBe('Calculate again');
  });

  it('history pagination does not change activity coverage status', () => {
    flushBootstrap({
      results: [summary],
      coverage: [currentCoverage],
      periodSummary: readyPeriodSummary,
    });
    selectEligibleAndLoadParams();
    const before = component.selectedActivityCalcState();
    component.onResultsPage({ pageIndex: 1, pageSize: 10, length: 21 } as never);
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/results?page=2&pageSize=10`,
      )
      .flush({ items: [], page: 2, pageSize: 10, totalItems: 21, totalPages: 3 });
    fixture.detectChanges();
    expect(component.selectedActivityCalcState()).toBe(before);
    expect(component.calculationActionLabel()).toBe('Calculate again');
  });

  it('coverage pagination sends page and pageSize and clears previous-page status', () => {
    flushBootstrap({ coverage: [missingCoverage] });
    selectEligibleAndLoadParams();
    expect(component.selectedActivityCalcState()).toBe('missing');
    component.onCoveragePage({ pageIndex: 1, pageSize: 10, length: 12 } as never);
    expect(component.selectedActivityId()).toBe('');
    expect(component.selectedActivityCalcState()).toBe('unknown');
    httpMock.expectOne(coverageUrl(2, 10)).flush({
      items: [{ ...currentCoverage, activityRecordId: 'act-2' }],
      page: 2,
      pageSize: 10,
      totalItems: 12,
      totalPages: 2,
    });
    fixture.detectChanges();
    expect(component.coveragePage()).toBe(2);
    expect(component.coveragePageSize()).toBe(10);
    expect(component.coverageItems()[0].activityRecordId).toBe('act-2');
    expect(component.selectedActivityCalcState()).toBe('unknown');
  });

  it('successful stale recalculation changes CTA to Calculate again after refresh', () => {
    flushBootstrap({
      coverage: [staleCoverage],
      results: [{ ...summary, isCurrent: true, isStale: true }],
      periodSummary: {
        ...incompletePeriodSummary,
        readinessStatus: 'STALE',
        missingResultCount: 0,
        staleResultCount: 1,
        currentResultCount: 1,
        validCurrentResultCount: 0,
      },
    });
    selectEligibleAndLoadParams();
    expect(component.calculationActionLabel()).toBe('Update calculation');
    component.form.controls.densityValue.setValue('0.67');
    fixture.detectChanges();
    component.runCalculationAction();
    const exec = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
    );
    exec.flush({
      runId: 'run-2',
      resultId: 'res-2',
      status: 'COMPLETED',
      calculationType: 'STATIONARY_COMBUSTION_CO2_V1',
      calculationVersion: 'v1',
      activityRecordId: 'act-1',
      fuelCode: 'NATURAL_GAS',
      referenceDate: '2024-01-15',
      resultValue: '190.22695917',
      resultUnit: 'tCO2',
      clientRequestId: exec.request.body.clientRequestId,
      idempotentReplay: false,
      createdAt: '2024-06-02T10:00:00Z',
    });
    flushAfterSuccessfulExecution({
      resultId: 'res-2',
      coverage: [{ ...currentCoverage, currentResultId: 'res-2' }],
      periodSummary: readyPeriodSummary,
      detail: { ...detail, id: 'res-2', isCurrent: true, isStale: false },
    });
    fixture.detectChanges();
    expect(component.calculationActionLabel()).toBe('Calculate again');
    expect(component.selectedActivityCalcState()).toBe('valid');
  });

  it('failed calculation leaves coverage unchanged', () => {
    flushBootstrap({ coverage: [missingCoverage] });
    selectEligibleAndLoadParams();
    component.form.controls.densityValue.setValue('0.67');
    const before = component.coverageItems();
    fixture.detectChanges();
    component.calculate();
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/stationary-combustion/executions`,
      )
      .flush(
        { error: { code: 'INTERNAL_ERROR', message: 'x', details: [], requestId: null } },
        { status: 500, statusText: 'Error' },
      );
    fixture.detectChanges();
    expect(component.coverageItems()).toEqual(before);
    expect(component.selectedActivityCalcState()).toBe('missing');
  });

  it('maps stale reason messages and fails safe on unknown coverage status', () => {
    expect(mapStaleReasonCode('QUANTITY_CHANGED')).toContain('amount changed');
    expect(mapStaleReasonCode('UNIT_CHANGED')).toContain('unit changed');
    expect(mapStaleReasonCode('DATE_CHANGED')).toContain('date changed');
    expect(mapStaleReasonCode('FUEL_TYPE_CHANGED')).toContain('fuel type changed');
    expect(mapStaleReasonCode('OWNERSHIP_OR_BINDING_MISMATCH')).toContain('no longer belongs');
    expect(mapStaleReasonCode('SOMETHING_ELSE')).toContain('changed after its last calculation');
    expect(coverageStatusLabel('MISSING')).toBe('Not calculated');
    expect(coverageStatusLabel('CURRENT')).toBe('Current');
    expect(coverageStatusLabel('STALE')).toBe('Out of date');
    expect(mapCoverageToCalcState('WEIRD')).toBe('unknown');
    flushBootstrap({
      coverage: [{ ...missingCoverage, coverageStatus: 'WEIRD' }],
    });
    selectEligibleAndLoadParams();
    expect(component.selectedActivityCalcState()).toBe('unknown');
    expect(component.canSubmit()).toBeFalse();
  });

  it('view-only user sees coverage status without calculation action', () => {
    fixture.componentRef.setInput('canConfigure', false);
    flushBootstrap({ coverage: [currentCoverage], periodSummary: readyPeriodSummary });
    selectEligibleAndLoadParams();
    expect(fixture.nativeElement.textContent).toContain('Current');
    expect(fixture.nativeElement.textContent).toContain('cannot run a calculation');
    expect(component.canSubmit()).toBeFalse();
  });

  it('maps blocking issue helpers', () => {
    flushBootstrap();
    expect(mapBlockingIssue('1 eligible fuel-use record(s) have no current calculation.')).toContain(
      'still need a calculation',
    );
    expect(mapBlockingIssue('unit incompatible')).toContain('unit');
    expect(mapBlockingIssue('totally unknown xyz')).toContain('attention');
  });

});
