import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { ApiErrorBody } from '../../../core/models/api.models';
import { ReportingPeriod } from '../../../core/models/reporting-period.models';
import { extractApiErrorMessage } from '../../../core/services/error.util';
import { ReportingPeriodService } from '../../../core/services/reporting-period.service';
import {
  CbamActivityRecord,
  CbamApiService,
  CbamStationaryCombustionActivityCoverageItem,
  CbamStationaryCombustionExecutionRequest,
  CbamStationaryCombustionFuel,
  CbamStationaryCombustionParameters,
  CbamStationaryCombustionPeriodSummary,
  CbamStationaryCombustionResultDetail,
  CbamStationaryCombustionResultSummary,
} from '../cbam-api.service';
import { createClientRequestId, formatDecimalDisplay } from '../cbam-shared.util';

export { createClientRequestId, formatDecimalDisplay };

const VOLUME_UNITS = new Set(['Sm3', 'm3']);
const MASS_UNITS = new Set(['kg', 't', 'Gg']);
const DENSITY_UNITS_BY_ACTIVITY: Record<string, string> = {
  Sm3: 'kg/Sm3',
  m3: 'kg/m3',
};

export type StationaryCombustionReadinessUi =
  | 'EMPTY'
  | 'INCOMPLETE'
  | 'STALE'
  | 'READY'
  | 'UNKNOWN';

export type SelectedActivityCalcState = 'missing' | 'valid' | 'stale' | 'unknown';

export function mapStationaryCombustionError(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 403 || error.status === 401) {
      return 'You do not have permission to do this.';
    }
    const body = error.error as ApiErrorBody | null;
    const details = body?.error?.details ?? [];
    const detailCode = details
      .map((d) => (d as { code?: string }).code)
      .find((c): c is string => typeof c === 'string' && c.length > 0);
    const code = detailCode ?? body?.error?.code;
    switch (code) {
      case 'DENSITY_REQUIRED':
        return 'Enter the fuel density.';
      case 'DENSITY_INVALID':
        return 'Enter a density greater than zero.';
      case 'UNRESOLVED_PARAMETER_SET':
        return 'No reference values are available for this fuel and date.';
      case 'AMBIGUOUS_PARAMETER_SET':
        return 'More than one reference value was found. The calculation cannot continue.';
      case 'REFERENCE_DATE_OUTSIDE_PERIOD':
        return 'Choose a date inside the reporting period.';
      case 'ACTIVITY_BINDING_MISMATCH':
        return 'This fuel use record does not belong to this period.';
      case 'IDEMPOTENCY_KEY_REUSED':
        return 'This calculation request changed. Start a new calculation.';
      case 'INCOMPATIBLE_UNIT':
        return 'The unit is not valid for this fuel.';
      default:
        break;
    }
    return extractApiErrorMessage(error, 'The calculation could not be completed. Try again.');
  }
  return 'The calculation could not be completed. Try again.';
}

export function isEligibleStationaryActivity(
  activity: CbamActivityRecord,
  fuels: CbamStationaryCombustionFuel[],
): boolean {
  if (activity.status !== 'active') {
    return false;
  }
  const fuel = fuels.find((f) => f.code === activity.activityType && f.status === 'ACTIVE');
  if (!fuel) {
    return false;
  }
  if (fuel.inputBasis === 'VOLUME') {
    return VOLUME_UNITS.has(activity.unit);
  }
  if (fuel.inputBasis === 'MASS') {
    return MASS_UNITS.has(activity.unit);
  }
  return false;
}

export function mapReadinessStatus(status: string | null | undefined): StationaryCombustionReadinessUi {
  switch (status) {
    case 'EMPTY':
    case 'INCOMPLETE':
    case 'STALE':
    case 'READY':
      return status;
    default:
      return 'UNKNOWN';
  }
}

export function readinessLabel(status: StationaryCombustionReadinessUi): string {
  switch (status) {
    case 'EMPTY':
      return 'No fuel use records';
    case 'INCOMPLETE':
      return 'Incomplete';
    case 'STALE':
      return 'Needs update';
    case 'READY':
      return 'Ready';
    default:
      return 'Not ready';
  }
}

export function readinessMessage(status: StationaryCombustionReadinessUi): string {
  switch (status) {
    case 'EMPTY':
      return 'Add fuel use in the Activities tab first.';
    case 'INCOMPLETE':
      return 'Calculate all fuel use records to complete this section.';
    case 'STALE':
      return 'One or more fuel use records changed. Update their calculations.';
    case 'READY':
      return 'All fuel use records have a current calculation.';
    default:
      return 'This section is not ready.';
  }
}

export function mapBlockingIssue(issue: string): string {
  const lower = issue.toLowerCase();
  if (lower.includes('no current calculation') || lower.includes('missing')) {
    return 'Some fuel use records still need a calculation.';
  }
  if (lower.includes('no longer match') || lower.includes('stale') || lower.includes('out of date')) {
    return 'Some calculations are out of date after fuel use changed.';
  }
  if (lower.includes('incompatible') || lower.includes('unit')) {
    return 'A fuel use unit is not valid for its fuel.';
  }
  if (lower.includes('mismatch') || lower.includes('ownership') || lower.includes('binding')) {
    return 'A fuel use record does not match this period or fuel.';
  }
  return 'Something needs attention in this section.';
}

export function resultStatusLabel(isCurrent: boolean, isStale: boolean): 'Current' | 'History' | 'Out of date' {
  if (isCurrent && isStale) {
    return 'Out of date';
  }
  if (isCurrent) {
    return 'Current';
  }
  return 'History';
}

export function coverageStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'MISSING':
      return 'Not calculated';
    case 'CURRENT':
      return 'Current';
    case 'STALE':
      return 'Out of date';
    default:
      return 'Unknown';
  }
}

export function mapCoverageToCalcState(status: string | null | undefined): SelectedActivityCalcState {
  switch (status) {
    case 'MISSING':
      return 'missing';
    case 'CURRENT':
      return 'valid';
    case 'STALE':
      return 'stale';
    default:
      return 'unknown';
  }
}

export function mapStaleReasonCode(code: string): string {
  switch (code) {
    case 'QUANTITY_CHANGED':
      return 'The amount changed after the last calculation.';
    case 'UNIT_CHANGED':
      return 'The unit changed after the last calculation.';
    case 'DATE_CHANGED':
      return 'The date changed after the last calculation.';
    case 'FUEL_TYPE_CHANGED':
      return 'The fuel type changed after the last calculation.';
    case 'OWNERSHIP_OR_BINDING_MISMATCH':
      return 'This record no longer belongs to this period.';
    default:
      return 'This fuel use record changed after its last calculation.';
  }
}

interface MaterialAttemptKey {
  activityRecordId: string;
  fuelCode: string;
  referenceDate: string;
  densityValue: string | null;
  densityUnit: string | null;
  datasetVersion: string | null;
}

@Component({
  selector: 'app-cbam-stationary-combustion',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './stationary-combustion.component.html',
  styleUrl: './stationary-combustion.component.scss',
})
export class CbamStationaryCombustionComponent implements OnInit {
  private readonly api = inject(CbamApiService);
  private readonly periodsApi = inject(ReportingPeriodService);
  private readonly fb = inject(FormBuilder);

  readonly bindingId = input.required<string>();
  readonly reportingPeriodId = input.required<string>();
  readonly canConfigure = input(false);
  readonly goToActivities = output<void>();

  readonly fuels = signal<CbamStationaryCombustionFuel[]>([]);
  readonly activities = signal<CbamActivityRecord[]>([]);
  readonly period = signal<ReportingPeriod | null>(null);
  readonly parameters = signal<CbamStationaryCombustionParameters | null>(null);

  readonly selectedActivityId = signal('');
  readonly referenceDateInput = signal('');
  readonly densityValueInput = signal('');
  readonly densityUnitInput = signal('kg/Sm3');

  readonly loadingBootstrap = signal(true);
  readonly loadingParameters = signal(false);
  readonly loadingResults = signal(false);
  readonly loadingDetail = signal(false);
  readonly loadingSummary = signal(false);
  readonly submitting = signal(false);

  readonly bootstrapError = signal<string | null>(null);
  readonly parameterError = signal<string | null>(null);
  readonly formError = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly resultsError = signal<string | null>(null);
  readonly summaryError = signal<string | null>(null);

  readonly periodSummary = signal<CbamStationaryCombustionPeriodSummary | null>(null);
  readonly coverageItems = signal<CbamStationaryCombustionActivityCoverageItem[]>([]);
  readonly coveragePage = signal(1);
  readonly coveragePageSize = signal(20);
  readonly coverageTotal = signal(0);
  readonly loadingCoverage = signal(false);
  readonly coverageError = signal<string | null>(null);
  readonly results = signal<CbamStationaryCombustionResultSummary[]>([]);
  readonly resultsPage = signal(1);
  readonly resultsPageSize = signal(20);
  readonly resultsTotal = signal(0);
  readonly resultDetail = signal<CbamStationaryCombustionResultDetail | null>(null);

  readonly resultColumns = [
    'status',
    'date',
    'fuel',
    'amount',
    'energy',
    'fossilCo2',
    'dataset',
    'actions',
  ];

  readonly fuelTotalColumns = ['fuel', 'activities', 'mass', 'energy', 'fossilCo2', 'final'];

  readonly form = this.fb.nonNullable.group({
    activityRecordId: ['', Validators.required],
    calculationReferenceDate: [''],
    densityValue: [''],
    densityUnit: ['kg/Sm3'],
  });

  private activeClientRequestId: string | null = null;
  private activeMaterialKey: string | null = null;
  private parameterRequestSeq = 0;
  private summaryRequestSeq = 0;
  private coverageRequestSeq = 0;

  /** Persisted activities remain available for join; selection list uses coverage. */
  readonly eligibleActivities = computed(() =>
    this.activities().filter((a) => isEligibleStationaryActivity(a, this.fuels())),
  );

  readonly selectedCoverage = computed(() => {
    const id = this.selectedActivityId();
    return this.coverageItems().find((item) => item.activityRecordId === id) ?? null;
  });

  readonly selectedActivity = computed(() => {
    const coverage = this.selectedCoverage();
    if (!coverage) {
      return null;
    }
    const persisted = this.activities().find((a) => a.id === coverage.activityRecordId);
    if (persisted) {
      return persisted;
    }
    // Coverage is authoritative for identity; synthesize a minimal activity view.
    return {
      id: coverage.activityRecordId,
      organizationId: '',
      reportingPeriodBindingId: this.bindingId(),
      installationProfileId: '',
      activityGroup: 'COMBUSTION',
      activityType: coverage.activityType,
      activityDate: coverage.activityDate,
      quantity: coverage.quantity,
      unit: coverage.unit,
      dataSourceType: 'PRIMARY',
      sourceReference: null,
      notes: null,
      status: 'active',
      rowVersion: 0,
    } satisfies CbamActivityRecord;
  });

  readonly selectedFuel = computed(() => {
    const activity = this.selectedActivity();
    if (!activity) {
      return null;
    }
    return this.fuels().find((f) => f.code === activity.activityType) ?? null;
  });

  readonly densityRequired = computed(() => this.selectedFuel()?.inputBasis === 'VOLUME');

  readonly effectiveReferenceDate = computed(() => {
    const activity = this.selectedActivity();
    if (!activity) {
      return null;
    }
    if (activity.activityDate) {
      return activity.activityDate;
    }
    const typed = this.referenceDateInput().trim();
    return typed || null;
  });

  readonly referenceDateOutsidePeriod = computed(() => {
    const ref = this.effectiveReferenceDate();
    const period = this.period();
    if (!ref || !period) {
      return false;
    }
    return ref < period.startDate || ref > period.endDate;
  });

  readonly densityInvalid = computed(() => {
    if (!this.densityRequired()) {
      return false;
    }
    const raw = this.densityValueInput().trim();
    if (!raw) {
      return true;
    }
    const value = Number(raw);
    return !Number.isFinite(value) || value <= 0;
  });

  readonly canSubmit = computed(() => {
    if (!this.canConfigure()) {
      return false;
    }
    if (this.submitting() || this.loadingParameters()) {
      return false;
    }
    if (this.selectedActivityCalcState() === 'unknown') {
      return false;
    }
    if (!this.selectedActivity() || !this.selectedFuel()) {
      return false;
    }
    if (!this.parameters() || this.parameterError()) {
      return false;
    }
    if (!this.effectiveReferenceDate()) {
      return false;
    }
    if (this.referenceDateOutsidePeriod()) {
      return false;
    }
    if (this.densityRequired() && this.densityInvalid()) {
      return false;
    }
    return true;
  });

  readonly readinessUi = computed(() => mapReadinessStatus(this.periodSummary()?.readinessStatus));

  readonly readinessStatusLabel = computed(() => readinessLabel(this.readinessUi()));

  readonly readinessStatusMessage = computed(() => readinessMessage(this.readinessUi()));

  readonly mappedBlockingIssues = computed(() =>
    (this.periodSummary()?.blockingIssues ?? []).map((issue) => mapBlockingIssue(issue)),
  );

  readonly showAuthoritativeTotals = computed(() => this.readinessUi() === 'READY');

  readonly showPartialTotals = computed(() => {
    const status = this.readinessUi();
    return status === 'INCOMPLETE' || status === 'STALE';
  });

  readonly showTotalsByFuel = computed(
    () => (this.periodSummary()?.totalsByFuel.length ?? 0) > 0 && this.readinessUi() !== 'EMPTY',
  );

  readonly selectedActivityCalcState = computed((): SelectedActivityCalcState => {
    const coverage = this.selectedCoverage();
    if (!coverage) {
      return 'unknown';
    }
    return mapCoverageToCalcState(coverage.coverageStatus);
  });

  readonly calculationActionLabel = computed(() => {
    switch (this.selectedActivityCalcState()) {
      case 'stale':
        return 'Update calculation';
      case 'valid':
        return 'Calculate again';
      case 'missing':
        return 'Calculate';
      default:
        return '';
    }
  });

  readonly selectedActivityIsStale = computed(() => this.selectedActivityCalcState() === 'stale');

  readonly selectedCoverageStatusLabel = computed(() =>
    coverageStatusLabel(this.selectedCoverage()?.coverageStatus),
  );

  readonly selectedStaleMessages = computed(() => {
    const codes = this.selectedCoverage()?.staleReasonCodes ?? [];
    if (codes.length === 0) {
      return this.selectedActivityIsStale()
        ? ['This fuel use record changed after its last calculation.']
        : [];
    }
    return codes.map((code) => mapStaleReasonCode(code));
  });

  readonly formatDecimal = formatDecimalDisplay;
  readonly resultBadge = resultStatusLabel;
  readonly coverageStatusLabel = coverageStatusLabel;

  ngOnInit(): void {
    this.reloadBootstrap();
    this.loadResults();
    this.loadSummary();
    this.loadCoverage();
    this.form.valueChanges.subscribe((value) => {
      this.successMessage.set(null);
      this.selectedActivityId.set(value.activityRecordId ?? '');
      this.referenceDateInput.set(value.calculationReferenceDate ?? '');
      this.densityValueInput.set(value.densityValue ?? '');
      this.densityUnitInput.set(value.densityUnit ?? 'kg/Sm3');
      this.invalidateAttemptIfMaterialChanged();
    });
    this.form.controls.calculationReferenceDate.valueChanges.subscribe(() => {
      this.refreshParameters();
    });
  }

  reloadBootstrap(): void {
    this.loadingBootstrap.set(true);
    this.bootstrapError.set(null);
    let pending = 3;
    const done = (): void => {
      pending -= 1;
      if (pending <= 0) {
        this.loadingBootstrap.set(false);
      }
    };

    this.api.listStationaryCombustionFuels().subscribe({
      next: (fuels) => {
        this.fuels.set(fuels.filter((f) => f.status === 'ACTIVE'));
        done();
      },
      error: (err: unknown) => {
        this.bootstrapError.set(extractApiErrorMessage(err));
        done();
      },
    });

    this.api.listActivityRecords(this.bindingId(), { page: 1, pageSize: 100 }).subscribe({
      next: (page) => {
        this.activities.set(page.items);
        done();
      },
      error: (err: unknown) => {
        this.bootstrapError.set(extractApiErrorMessage(err));
        done();
      },
    });

    this.periodsApi.get(this.reportingPeriodId()).subscribe({
      next: (period) => {
        this.period.set(period);
        done();
      },
      error: (err: unknown) => {
        this.bootstrapError.set(extractApiErrorMessage(err));
        done();
      },
    });
  }

  loadSummary(): void {
    const seq = ++this.summaryRequestSeq;
    this.loadingSummary.set(true);
    this.summaryError.set(null);
    this.api.getStationaryCombustionSummary(this.bindingId()).subscribe({
      next: (summary) => {
        if (seq !== this.summaryRequestSeq) {
          return;
        }
        this.periodSummary.set(summary);
        this.loadingSummary.set(false);
      },
      error: () => {
        if (seq !== this.summaryRequestSeq) {
          return;
        }
        this.loadingSummary.set(false);
        // Keep a stable user-facing message; do not surface opaque API payloads as the only text.
        this.summaryError.set('The period summary could not be loaded.');
      },
    });
  }

  retrySummary(): void {
    this.loadSummary();
  }

  loadCoverage(): void {
    const seq = ++this.coverageRequestSeq;
    this.loadingCoverage.set(true);
    this.coverageError.set(null);
    this.api
      .listStationaryCombustionActivityCoverage(this.bindingId(), {
        page: this.coveragePage(),
        pageSize: this.coveragePageSize(),
      })
      .subscribe({
        next: (page) => {
          if (seq !== this.coverageRequestSeq) {
            return;
          }
          this.coverageItems.set(page.items);
          this.coverageTotal.set(page.totalItems);
          this.loadingCoverage.set(false);
        },
        error: () => {
          if (seq !== this.coverageRequestSeq) {
            return;
          }
          this.loadingCoverage.set(false);
          this.coverageError.set('Fuel use coverage could not be loaded.');
        },
      });
  }

  retryCoverage(): void {
    this.loadCoverage();
  }

  onCoveragePage(event: PageEvent): void {
    this.clearSelectionForCoveragePageChange();
    this.coveragePage.set(event.pageIndex + 1);
    this.coveragePageSize.set(event.pageSize);
    this.loadCoverage();
  }

  private clearSelectionForCoveragePageChange(): void {
    this.form.controls.activityRecordId.setValue('', { emitEvent: false });
    this.selectedActivityId.set('');
    this.parameters.set(null);
    this.parameterError.set(null);
    this.clearAttemptState();
  }

  onActivityChange(): void {
    this.selectedActivityId.set(this.form.controls.activityRecordId.value);
    const activity = this.selectedActivity();
    const unit = activity?.unit;
    if (unit && DENSITY_UNITS_BY_ACTIVITY[unit]) {
      this.form.controls.densityUnit.setValue(DENSITY_UNITS_BY_ACTIVITY[unit], {
        emitEvent: false,
      });
      this.densityUnitInput.set(DENSITY_UNITS_BY_ACTIVITY[unit]);
    }
    if (activity?.activityDate) {
      this.form.controls.calculationReferenceDate.setValue('', { emitEvent: false });
      this.referenceDateInput.set('');
    }
    this.form.controls.densityValue.setValue('', { emitEvent: false });
    this.densityValueInput.set('');
    this.invalidateAttemptIfMaterialChanged();
    this.refreshParameters();
  }

  openActivitiesTab(): void {
    this.goToActivities.emit();
  }

  loadResults(): void {
    this.loadingResults.set(true);
    this.resultsError.set(null);
    this.api
      .listStationaryCombustionResults(this.bindingId(), {
        page: this.resultsPage(),
        pageSize: this.resultsPageSize(),
      })
      .subscribe({
        next: (page) => {
          this.results.set(page.items);
          this.resultsTotal.set(page.totalItems);
          this.loadingResults.set(false);
        },
        error: (err: unknown) => {
          this.loadingResults.set(false);
          this.resultsError.set(extractApiErrorMessage(err));
        },
      });
  }

  onResultsPage(event: PageEvent): void {
    this.resultsPage.set(event.pageIndex + 1);
    this.resultsPageSize.set(event.pageSize);
    this.loadResults();
  }

  viewDetails(resultId: string): void {
    this.loadingDetail.set(true);
    this.resultDetail.set(null);
    this.api.getStationaryCombustionResult(this.bindingId(), resultId).subscribe({
      next: (detail) => {
        this.resultDetail.set(detail);
        this.loadingDetail.set(false);
      },
      error: (err: unknown) => {
        this.loadingDetail.set(false);
        this.formError.set(extractApiErrorMessage(err));
      },
    });
  }

  closeDetails(): void {
    this.resultDetail.set(null);
  }

  runCalculationAction(): void {
    const state = this.selectedActivityCalcState();
    if (state === 'valid' || state === 'stale') {
      this.clearAttemptState();
    }
    this.calculate();
  }

  calculate(): void {
    if (!this.canSubmit() || this.submitting()) {
      return;
    }
    const activity = this.selectedActivity();
    const fuel = this.selectedFuel();
    const referenceDate = this.effectiveReferenceDate();
    if (!activity || !fuel || !referenceDate) {
      return;
    }

    const material = this.currentMaterialKey(activity, fuel, referenceDate);
    const materialSerialized = JSON.stringify(material);
    if (!this.activeClientRequestId || this.activeMaterialKey !== materialSerialized) {
      this.activeClientRequestId = createClientRequestId();
      this.activeMaterialKey = materialSerialized;
    }

    const payload: CbamStationaryCombustionExecutionRequest = {
      clientRequestId: this.activeClientRequestId,
      activityRecordId: activity.id,
      fuelCode: fuel.code,
    };
    if (!activity.activityDate) {
      payload.calculationReferenceDate = referenceDate;
    }
    if (fuel.inputBasis === 'VOLUME') {
      payload.densityValue = this.densityValueInput().trim();
      payload.densityUnit = this.densityUnitInput();
    }

    this.submitting.set(true);
    this.formError.set(null);
    this.successMessage.set(null);

    this.api.executeStationaryCombustion(this.bindingId(), payload).subscribe({
      next: (response) => {
        this.submitting.set(false);
        this.clearAttemptState();
        if (response.idempotentReplay) {
          this.successMessage.set(
            'This calculation was already completed. The saved result is shown.',
          );
        } else {
          this.successMessage.set('Calculation saved.');
        }
        this.resultsPage.set(1);
        this.loadResults();
        this.loadSummary();
        this.loadCoverage();
        this.viewDetails(response.resultId);
      },
      error: (err: unknown) => {
        this.submitting.set(false);
        this.formError.set(mapStationaryCombustionError(err));
        if (err instanceof HttpErrorResponse) {
          const body = err.error as ApiErrorBody | null;
          const details = body?.error?.details ?? [];
          const detailCode = details
            .map((d) => (d as { code?: string }).code)
            .find((c): c is string => typeof c === 'string');
          const code = detailCode ?? body?.error?.code;
          if (code === 'IDEMPOTENCY_KEY_REUSED') {
            this.clearAttemptState();
          }
        }
      },
    });
  }

  calculateAgain(): void {
    this.clearAttemptState();
    this.calculate();
  }

  activityLabel(activity: CbamActivityRecord): string {
    const fuel = this.fuels().find((f) => f.code === activity.activityType);
    const fuelName = fuel?.name ?? activity.activityType;
    const datePart = activity.activityDate ?? 'No date';
    return `${fuelName} · ${datePart} · ${activity.quantity} ${activity.unit}`;
  }

  coverageLabel(item: CbamStationaryCombustionActivityCoverageItem): string {
    const datePart = item.activityDate ?? 'No date';
    return `${item.fuelName} · ${datePart} · ${item.quantity} ${item.unit}`;
  }

  fuelDisplayName(code: string): string {
    return this.fuels().find((f) => f.code === code)?.name ?? code;
  }

  calculationAriaLabel(): string {
    const activity = this.selectedActivity();
    const label = this.calculationActionLabel();
    if (!activity) {
      return label;
    }
    return `${label} for ${this.activityLabel(activity)}`;
  }

  private refreshParameters(): void {
    const activity = this.selectedActivity();
    const fuel = this.selectedFuel();
    const ref = this.effectiveReferenceDate();
    if (!activity || !fuel || !ref || this.referenceDateOutsidePeriod()) {
      this.parameters.set(null);
      this.parameterError.set(null);
      this.loadingParameters.set(false);
      return;
    }
    this.loadParameters(fuel.code, ref);
  }

  private loadParameters(fuelCode: string, referenceDate: string): void {
    const seq = ++this.parameterRequestSeq;
    this.loadingParameters.set(true);
    this.parameterError.set(null);
    this.parameters.set(null);
    this.api
      .resolveStationaryCombustionParameters(fuelCode, { referenceDate })
      .subscribe({
        next: (params) => {
          if (seq !== this.parameterRequestSeq) {
            return;
          }
          this.parameters.set(params);
          this.loadingParameters.set(false);
        },
        error: (err: unknown) => {
          if (seq !== this.parameterRequestSeq) {
            return;
          }
          this.parameters.set(null);
          this.loadingParameters.set(false);
          this.parameterError.set(mapStationaryCombustionError(err));
        },
      });
  }

  private currentMaterialKey(
    activity: CbamActivityRecord,
    fuel: CbamStationaryCombustionFuel,
    referenceDate: string,
  ): MaterialAttemptKey {
    const volume = fuel.inputBasis === 'VOLUME';
    return {
      activityRecordId: activity.id,
      fuelCode: fuel.code,
      referenceDate,
      densityValue: volume ? this.densityValueInput().trim() || null : null,
      densityUnit: volume ? this.densityUnitInput() : null,
      datasetVersion: null,
    };
  }

  private invalidateAttemptIfMaterialChanged(): void {
    if (!this.activeClientRequestId || !this.activeMaterialKey) {
      return;
    }
    const activity = this.selectedActivity();
    const fuel = this.selectedFuel();
    const referenceDate = this.effectiveReferenceDate();
    if (!activity || !fuel || !referenceDate) {
      this.clearAttemptState();
      return;
    }
    const next = JSON.stringify(this.currentMaterialKey(activity, fuel, referenceDate));
    if (next !== this.activeMaterialKey) {
      this.clearAttemptState();
    }
  }

  private clearAttemptState(): void {
    this.activeClientRequestId = null;
    this.activeMaterialKey = null;
  }

  getActiveClientRequestIdForTests(): string | null {
    return this.activeClientRequestId;
  }

  seedActiveClientRequestIdForTests(id: string, materialKey: string): void {
    this.activeClientRequestId = id;
    this.activeMaterialKey = materialKey;
  }
}
