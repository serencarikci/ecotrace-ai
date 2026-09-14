import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { Component, signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamMonthlyProductionBasis,
  CbamMonthlyProductionBasisSummary,
} from '../cbam-api.service';
import { CbamMonthlyAllocationDataComponent } from './monthly-allocation-data.component';
import {
  formatCbamShareDisplay,
  formatMonthLabel,
  mapCoverageLabel,
  mapIssueCodeMessage,
  mapReconciliationLabel,
  quantityPayloadValue,
} from './monthly-allocation-data.util';

@Component({
  standalone: true,
  imports: [CbamMonthlyAllocationDataComponent],
  template: `
    <app-cbam-monthly-allocation-data
      [bindingId]="bindingId()"
      [canConfigure]="canConfigure()"
      [canMutate]="canMutate()"
      (goToDirectEmissions)="wentToDirect.set(true)"
    />
  `,
})
class HostComponent {
  readonly bindingId = signal('binding-1');
  readonly canConfigure = signal(true);
  readonly canMutate = signal(true);
  readonly wentToDirect = signal(false);
}

describe('CbamMonthlyAllocationDataComponent', () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;
  let httpMock: HttpTestingController;
  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;

  const emptySummary = (
    overrides: Partial<CbamMonthlyProductionBasisSummary> = {},
  ): CbamMonthlyProductionBasisSummary => ({
    reportingPeriodBindingId: 'binding-1',
    expectedMonthCount: 3,
    completedMonthCount: 0,
    incompleteMonthCount: 0,
    invalidMonthCount: 0,
    missingMonthCount: 3,
    status: 'INCOMPLETE',
    allocationBasisReady: false,
    blockingIssueCodes: ['MONTHLY_PRODUCTION_BASIS_MISSING'],
    monthCoverage: [
      { monthStart: '2026-01-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
      { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
      { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
    ],
    informationalTotalProductionTonnes: null,
    informationalTotalCbamQuantityTonnes: null,
    combustionCompatibilityStatus: 'READY',
    combustionCompatibilityIssueCodes: [],
    combustionItems: [],
    productionReconciliation: [],
    ...overrides,
  });

  const readyRow = (
    overrides: Partial<CbamMonthlyProductionBasis> = {},
  ): CbamMonthlyProductionBasis => ({
    id: 'mpb-1',
    organizationId: 'org-1',
    reportingPeriodBindingId: 'binding-1',
    monthStart: '2026-01-01',
    totalProductionQuantity: '100.5',
    cbamQuantity: '25.125',
    quantityUnit: 't',
    normalizedTotalProductionTonnes: '100.5',
    normalizedCbamQuantityTonnes: '25.125',
    cbamShare: '0.25',
    status: 'READY',
    issueCodes: [],
    sourceType: 'MANUAL',
    notes: null,
    rowVersion: 1,
    ...overrides,
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
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
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
  });

  afterEach(() => {
    httpMock.verify();
  });

  function child(): CbamMonthlyAllocationDataComponent {
    return fixture.debugElement.query(By.directive(CbamMonthlyAllocationDataComponent))
      .componentInstance as CbamMonthlyAllocationDataComponent;
  }

  function flushLoad(
    summary: CbamMonthlyProductionBasisSummary = emptySummary(),
    items: CbamMonthlyProductionBasis[] = [],
  ): void {
    httpMock
      .expectOne(`${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis-summary`)
      .flush(summary);
    httpMock
      .expectOne(
        `${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis?page=1&pageSize=100`,
      )
      .flush({
        items,
        page: 1,
        pageSize: 100,
        totalItems: items.length,
        totalPages: 1,
      });
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent as string;
  }

  function januaryRow() {
    return child().monthRows().find((r) => r.monthStart === '2026-01-01')!;
  }

  it('displays expected months from the backend summary', () => {
    fixture.detectChanges();
    flushLoad();
    expect(text()).toContain('January 2026');
    expect(text()).toContain('February 2026');
    expect(text()).toContain('March 2026');
  });

  it('shows Not entered for missing months', () => {
    fixture.detectChanges();
    flushLoad();
    expect(text()).toContain('Not entered');
  });

  it('hides mutation actions for view-only users', () => {
    host.canMutate.set(false);
    host.canConfigure.set(false);
    fixture.detectChanges();
    flushLoad();
    expect(fixture.nativeElement.querySelector('[aria-label^="Enter "]')).toBeNull();
    expect(fixture.nativeElement.querySelector('[aria-label^="Edit "]')).toBeNull();
    expect(fixture.nativeElement.querySelector('[aria-label^="Delete "]')).toBeNull();
    expect(text()).toContain('January 2026');
  });

  it('creates a missing month with POST', () => {
    fixture.detectChanges();
    flushLoad();
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.setValue({
      totalProductionQuantity: '100',
      cbamQuantity: '40',
      quantityUnit: 't',
    });
    fixture.detectChanges();
    c.saveMonth(januaryRow());

    const post = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis`,
    );
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual({
      monthStart: '2026-01-01',
      totalProductionQuantity: '100',
      cbamQuantity: '40',
      quantityUnit: 't',
    });
    post.flush(readyRow());
    flushLoad(
      emptySummary({
        completedMonthCount: 1,
        missingMonthCount: 2,
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow()],
    );
  });

  it('updates an existing row with PATCH and rowVersion', () => {
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        completedMonthCount: 1,
        missingMonthCount: 2,
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow()],
    );
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.patchValue({ totalProductionQuantity: '200.75' });
    c.saveMonth(januaryRow());

    const patch = httpMock.expectOne(`${orgBase}/monthly-production-basis/mpb-1`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body.rowVersion).toBe(1);
    expect(patch.request.body.totalProductionQuantity).toBe('200.75');
    patch.flush(readyRow({ totalProductionQuantity: '200.75', rowVersion: 2 }));
    flushLoad(
      emptySummary({
        completedMonthCount: 1,
        missingMonthCount: 2,
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow({ totalProductionQuantity: '200.75', rowVersion: 2 })],
    );
  });

  it('sends blank quantity as null and preserves explicit zero', () => {
    expect(quantityPayloadValue('')).toBeNull();
    expect(quantityPayloadValue('0')).toBe('0');

    fixture.detectChanges();
    flushLoad();
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.setValue({
      totalProductionQuantity: '',
      cbamQuantity: '0',
      quantityUnit: 't',
    });
    c.saveMonth(januaryRow());

    const post = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis`,
    );
    expect(post.request.body.totalProductionQuantity).toBeNull();
    expect(post.request.body.cbamQuantity).toBe('0');
    post.flush(
      readyRow({
        totalProductionQuantity: null,
        cbamQuantity: '0',
        status: 'INCOMPLETE',
        cbamShare: null,
      }),
    );
    flushLoad();
  });

  it('does not convert decimal input through Number', () => {
    const precise = '1.234567890123456789';
    fixture.detectChanges();
    flushLoad();
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.setValue({
      totalProductionQuantity: precise,
      cbamQuantity: '0.1',
      quantityUnit: 't',
    });
    c.saveMonth(januaryRow());

    const post = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis`,
    );
    expect(post.request.body.totalProductionQuantity).toBe(precise);
    expect(typeof post.request.body.totalProductionQuantity).toBe('string');
    post.flush(readyRow({ totalProductionQuantity: precise }));
    flushLoad();
  });

  it('offers only mass units kg, t, Gg', () => {
    fixture.detectChanges();
    flushLoad();
    expect([...child().massUnits]).toEqual(['kg', 't', 'Gg']);
    expect(child().massUnits as readonly string[]).not.toContain('m3');
    expect(child().massUnits as readonly string[]).not.toContain('kWh');
  });

  it('displays backend cbamShare and does not calculate a period-wide ratio', () => {
    expect(formatCbamShareDisplay('0')).toBe('0%');
    expect(formatCbamShareDisplay('0.25')).toBe('25%');
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        informationalTotalProductionTonnes: '300',
        informationalTotalCbamQuantityTonnes: '75',
        completedMonthCount: 1,
        missingMonthCount: 2,
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow({ cbamShare: '0.25' })],
    );
    expect(text()).toContain('25%');
    expect(text()).not.toContain('Period share');
    expect(text()).not.toMatch(/sum\(E\)/i);
  });

  it('uses backend-authoritative summary readiness text', () => {
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        allocationBasisReady: true,
        completedMonthCount: 3,
        missingMonthCount: 0,
        blockingIssueCodes: [],
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          {
            monthStart: '2026-02-01',
            coverage: 'READY',
            recordId: 'mpb-2',
            issueCodes: [],
          },
          {
            monthStart: '2026-03-01',
            coverage: 'READY',
            recordId: 'mpb-3',
            issueCodes: [],
          },
        ],
      }),
    );
    expect(text()).toContain('Monthly data is ready.');
    expect(text()).toContain('Ready months: 3 / 3');
  });

  it('maps coverage statuses and unknown fallbacks', () => {
    expect(mapCoverageLabel('MISSING')).toBe('Not entered');
    expect(mapCoverageLabel('INCOMPLETE')).toBe('Incomplete');
    expect(mapCoverageLabel('INVALID')).toBe('Check values');
    expect(mapCoverageLabel('READY')).toBe('Ready');
    expect(mapCoverageLabel('WEIRD')).toBe('Not ready');
    expect(mapIssueCodeMessage('UNKNOWN_CODE_X')).toBe('More information is needed.');
    expect(formatMonthLabel('2026-01-01')).toBe('January 2026');

    fixture.detectChanges();
    flushLoad(
      emptySummary({
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'INCOMPLETE',
            recordId: 'mpb-1',
            issueCodes: ['TOTAL_PRODUCTION_REQUIRED'],
          },
          {
            monthStart: '2026-02-01',
            coverage: 'INVALID',
            recordId: 'mpb-2',
            issueCodes: [],
          },
          {
            monthStart: '2026-03-01',
            coverage: 'READY',
            recordId: 'mpb-3',
            issueCodes: [],
          },
        ],
        blockingIssueCodes: ['TOTAL_PRODUCTION_REQUIRED', 'MYSTERY_CODE'],
      }),
      [
        readyRow({ id: 'mpb-1', status: 'INCOMPLETE', totalProductionQuantity: null }),
        readyRow({ id: 'mpb-2', monthStart: '2026-02-01', status: 'INVALID' }),
        readyRow({ id: 'mpb-3', monthStart: '2026-03-01' }),
      ],
    );
    expect(text()).toContain('Incomplete');
    expect(text()).toContain('Check values');
    expect(text()).toContain('Ready');
    expect(text()).toContain('Enter total production.');
    expect(text()).toContain('More information is needed.');
    expect(text()).toContain('MYSTERY_CODE');
  });

  it('maps E>D backend validation to simple text', () => {
    fixture.detectChanges();
    flushLoad();
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.setValue({
      totalProductionQuantity: '10',
      cbamQuantity: '20',
      quantityUnit: 't',
    });
    c.saveMonth(januaryRow());

    httpMock
      .expectOne(`${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis`)
      .flush(
        {
          error: {
            message: 'CBAM quantity cannot exceed total production',
            details: [{ code: 'CBAM_QUANTITY_EXCEEDS_TOTAL' }],
          },
        },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
    fixture.detectChanges();
    expect(text()).toContain(
      'The amount sent to the importer cannot be higher than total production.',
    );
    expect(c.editForm.getRawValue().totalProductionQuantity).toBe('10');
    expect(c.editForm.getRawValue().cbamQuantity).toBe('20');
  });

  it('shows reconciliation EXACT_MATCH, MISMATCH without overwriting E, and UNAVAILABLE', () => {
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          {
            monthStart: '2026-02-01',
            coverage: 'READY',
            recordId: 'mpb-2',
            issueCodes: [],
          },
          {
            monthStart: '2026-03-01',
            coverage: 'INCOMPLETE',
            recordId: 'mpb-3',
            issueCodes: [],
          },
        ],
        productionReconciliation: [
          {
            monthStart: '2026-01-01',
            explicitCbamQuantityTonnes: '25.125',
            recordedCbamProductionTonnes: '25.125',
            differenceTonnes: '0',
            reconciliationStatus: 'EXACT_MATCH',
          },
          {
            monthStart: '2026-02-01',
            explicitCbamQuantityTonnes: '10',
            recordedCbamProductionTonnes: '12',
            differenceTonnes: '-2',
            reconciliationStatus: 'MISMATCH',
          },
          {
            monthStart: '2026-03-01',
            explicitCbamQuantityTonnes: null,
            recordedCbamProductionTonnes: null,
            differenceTonnes: null,
            reconciliationStatus: 'UNAVAILABLE',
          },
        ],
      }),
      [
        readyRow({ cbamQuantity: '25.125' }),
        readyRow({
          id: 'mpb-2',
          monthStart: '2026-02-01',
          cbamQuantity: '10',
          cbamShare: '0.1',
        }),
        readyRow({
          id: 'mpb-3',
          monthStart: '2026-03-01',
          cbamQuantity: null,
          status: 'INCOMPLETE',
          cbamShare: null,
        }),
      ],
    );
    expect(mapReconciliationLabel('EXACT_MATCH')).toBe('Matches product records');
    expect(text()).toContain('Matches product records');
    expect(text()).toContain('Does not match product records');
    expect(text()).toContain('The importer amount does not match the product records.');
    expect(text()).toContain('Cannot compare yet');
    const febCard = fixture.nativeElement.querySelector('[data-month="2026-02-01"]') as HTMLElement;
    expect(febCard.textContent).toContain('10');
    expect(febCard.textContent).toContain('12');
  });

  it('displays stationary-combustion compatibility issues from the summary', () => {
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        combustionCompatibilityStatus: 'BLOCKED',
        combustionCompatibilityIssueCodes: ['COMBUSTION_ACTIVITY_DATE_REQUIRED'],
        combustionItems: [
          {
            activityRecordId: 'act-1',
            currentResultId: 'res-1',
            activityDate: null,
            monthStart: null,
            status: 'BLOCKED',
            issueCodes: [
              'COMBUSTION_ACTIVITY_DATE_REQUIRED',
              'COMBUSTION_MONTH_NOT_COVERED',
            ],
          },
        ],
      }),
    );
    expect(text()).toContain('A fuel record does not have a date.');
    expect(text()).toContain('A fuel record is outside the entered months.');
    expect(text()).toContain('Open Direct Emissions');
  });

  it('reloads list and summary after successful save', () => {
    fixture.detectChanges();
    flushLoad();
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.setValue({
      totalProductionQuantity: '50',
      cbamQuantity: '10',
      quantityUnit: 't',
    });
    c.saveMonth(januaryRow());
    httpMock
      .expectOne(`${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis`)
      .flush(readyRow());
    flushLoad(
      emptySummary({
        allocationBasisReady: false,
        completedMonthCount: 1,
        missingMonthCount: 2,
        blockingIssueCodes: ['MONTHLY_PRODUCTION_BASIS_MISSING'],
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow()],
    );
    expect(text()).toContain('Ready months: 1 / 3');
  });

  it('keeps entered values and old summary after a failed save', () => {
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        allocationBasisReady: false,
        completedMonthCount: 0,
        blockingIssueCodes: ['MONTHLY_PRODUCTION_BASIS_MISSING'],
      }),
    );
    expect(text()).toContain('Complete the monthly data before allocation.');
    const c = child();
    c.startEdit(januaryRow());
    c.editForm.setValue({
      totalProductionQuantity: '99.9',
      cbamQuantity: '1',
      quantityUnit: 't',
    });
    c.saveMonth(januaryRow());
    httpMock
      .expectOne(`${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis`)
      .flush(
        { error: { message: 'Server error', details: [] } },
        { status: 500, statusText: 'Server Error' },
      );
    fixture.detectChanges();
    expect(c.editForm.getRawValue().totalProductionQuantity).toBe('99.9');
    expect(c.editForm.getRawValue().cbamQuantity).toBe('1');
    expect(text()).toContain('Complete the monthly data before allocation.');
    expect(text()).toContain('Ready months: 0 / 3');
  });

  it('confirms delete and refreshes to Not entered', () => {
    spyOn(window, 'confirm').and.returnValue(true);
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        completedMonthCount: 1,
        missingMonthCount: 2,
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow()],
    );
    child().deleteMonth(januaryRow());
    expect(window.confirm).toHaveBeenCalled();
    const del = httpMock.expectOne(`${orgBase}/monthly-production-basis/mpb-1`);
    expect(del.request.method).toBe('DELETE');
    del.flush(null);
    flushLoad();
    expect(text()).toContain('Not entered');
  });

  it('maps concurrency conflict to Reload without silent retry', () => {
    fixture.detectChanges();
    flushLoad(
      emptySummary({
        completedMonthCount: 1,
        missingMonthCount: 2,
        monthCoverage: [
          {
            monthStart: '2026-01-01',
            coverage: 'READY',
            recordId: 'mpb-1',
            issueCodes: [],
          },
          { monthStart: '2026-02-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          { monthStart: '2026-03-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
      }),
      [readyRow()],
    );
    const c = child();
    c.startEdit(januaryRow());
    c.saveMonth(januaryRow());
    httpMock.expectOne(`${orgBase}/monthly-production-basis/mpb-1`).flush(
      { error: { message: 'Conflict', details: [] } },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();
    expect(text()).toContain('This record changed. Reload it and try again.');
    expect(fixture.nativeElement.textContent).toContain('Reload');
    httpMock.expectNone(`${orgBase}/monthly-production-basis/mpb-1`);
  });

  it('ignores stale load responses after binding change', fakeAsync(() => {
    fixture.detectChanges();
    const firstSummary = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis-summary`,
    );
    const firstList = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-1/monthly-production-basis?page=1&pageSize=100`,
    );

    host.bindingId.set('binding-2');
    fixture.detectChanges();
    tick();

    const secondSummary = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-2/monthly-production-basis-summary`,
    );
    const secondList = httpMock.expectOne(
      `${orgBase}/reporting-period-bindings/binding-2/monthly-production-basis?page=1&pageSize=100`,
    );

    if (!firstSummary.cancelled) {
      firstSummary.flush(
        emptySummary({
          reportingPeriodBindingId: 'binding-1',
          blockingIssueCodes: ['STALE_BINDING'],
          monthCoverage: [
            { monthStart: '2025-01-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
          ],
          expectedMonthCount: 1,
          missingMonthCount: 1,
        }),
      );
    }
    if (!firstList.cancelled) {
      firstList.flush({ items: [], page: 1, pageSize: 100, totalItems: 0, totalPages: 0 });
    }

    secondSummary.flush(
      emptySummary({
        reportingPeriodBindingId: 'binding-2',
        monthCoverage: [
          { monthStart: '2026-04-01', coverage: 'MISSING', recordId: null, issueCodes: [] },
        ],
        expectedMonthCount: 1,
        missingMonthCount: 1,
        blockingIssueCodes: [],
      }),
    );
    secondList.flush({ items: [], page: 1, pageSize: 100, totalItems: 0, totalPages: 0 });
    fixture.detectChanges();

    expect(text()).toContain('April 2026');
    expect(text()).not.toContain('January 2025');
    expect(text()).not.toContain('STALE_BINDING');
  }));
});

describe('monthly-allocation-data.util', () => {
  it('formats month labels and share without Number loss for simple ratios', () => {
    expect(formatMonthLabel('2026-02-01')).toBe('February 2026');
    expect(formatCbamShareDisplay('0')).toBe('0%');
    expect(formatCbamShareDisplay('1')).toBe('100%');
  });
});
