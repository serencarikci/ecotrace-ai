import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { Subject, forkJoin, of } from 'rxjs';
import { catchError, finalize, switchMap, tap } from 'rxjs/operators';
import {
  CbamActivityRecord,
  CbamApiService,
  CbamPurchasedElectricityExecuteRequest,
  CbamPurchasedElectricityFactorResolution,
  CbamPurchasedElectricityFactorSourceMode,
  CbamPurchasedElectricityPeriodSummary,
  CbamPurchasedElectricityResultDetail,
  CbamPurchasedElectricityResultSummary,
} from '../cbam-api.service';
import {
  ELECTRICITY_FACTOR_UNITS,
  createClientRequestId,
  extractErrorCode,
  formatDecimalDisplay,
  isBlankDecimalInput,
  isEligibleElectricityActivity,
  isNegativeDecimalString,
  mapElectricityInfoCode,
  mapElectricityIssueCode,
  mapElectricityStaleReason,
  mapFactorSourceLabel,
  mapPurchasedElectricityError,
  mapReadinessStatusLabel,
  mapResultLifecycleLabel,
  mapSelectedCalcState,
  optionalDecimalOrNull,
  optionalTextOrNull,
} from './purchased-electricity.util';

@Component({
  selector: 'app-cbam-purchased-electricity',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatRadioModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './purchased-electricity.component.html',
  styleUrl: './purchased-electricity.component.scss',
})
export class CbamPurchasedElectricityComponent {
  private readonly api = inject(CbamApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  private readonly load$ = new Subject<string>();
  private loadSeq = 0;

  /** In-memory only; never persisted to localStorage. */
  private activeClientRequestId: string | null = null;
  private activeMaterialKey: string | null = null;
  private executingGuard = false;

  readonly bindingId = input.required<string>();
  readonly canConfigure = input(false);
  readonly canMutate = input(false);
  readonly goToActivities = output<void>();

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly activities = signal<CbamActivityRecord[]>([]);
  readonly readiness = signal<CbamPurchasedElectricityPeriodSummary | null>(null);
  readonly summary = signal<CbamPurchasedElectricityPeriodSummary | null>(null);
  readonly results = signal<CbamPurchasedElectricityResultSummary[]>([]);
  readonly resultsTotal = signal(0);
  readonly resultsPage = signal(1);
  readonly resultsPageSize = signal(10);
  readonly selectedDetail = signal<CbamPurchasedElectricityResultDetail | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal<string | null>(null);
  readonly platformDefault = signal<CbamPurchasedElectricityFactorResolution | null>(null);
  readonly platformDefaultLoading = signal(false);
  readonly platformDefaultError = signal<string | null>(null);
  readonly submitting = signal(false);
  readonly actionError = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly liveMessage = signal('');
  /** Bumps when reactive form values change so computeds re-evaluate. */
  readonly formEpoch = signal(0);
  readonly openSections = signal<Record<string, boolean>>({
    input: true,
    calculation: true,
    factor: true,
    exported: true,
    sources: false,
    audit: false,
  });

  readonly factorUnits = ELECTRICITY_FACTOR_UNITS;

  readonly form = this.fb.nonNullable.group({
    activityRecordId: ['', Validators.required],
    factorSourceMode: this.fb.nonNullable.control<CbamPurchasedElectricityFactorSourceMode>(
      'MANUAL',
    ),
    manualValue: [''],
    manualUnit: ['tCO2e/MWh'],
    sourceName: [''],
    sourceDocument: [''],
    datasetVersion: [''],
    referenceDescription: [''],
    effectiveDate: [''],
    exportedQuantity: [''],
    exportedUnit: ['MWh'],
    evidenceNotes: [''],
  });

  readonly historyColumns = [
    'created',
    'electricity',
    'factorSource',
    'factor',
    'emissions',
    'status',
    'actions',
  ] as const;

  readonly formatDecimal = formatDecimalDisplay;
  readonly issueMessage = mapElectricityIssueCode;
  readonly infoMessage = mapElectricityInfoCode;
  readonly staleReasonMessage = mapElectricityStaleReason;
  readonly lifecycleLabel = mapResultLifecycleLabel;
  readonly factorSourceLabel = mapFactorSourceLabel;
  readonly readinessLabel = mapReadinessStatusLabel;

  readonly eligibleActivities = computed(() =>
    this.activities().filter((a) => isEligibleElectricityActivity(a)),
  );

  readonly selectedActivity = computed(() => {
    this.formEpoch();
    const id = this.form.controls.activityRecordId.value;
    return this.eligibleActivities().find((a) => a.id === id) ?? null;
  });

  readonly currentResultForSelected = computed(() => {
    const activity = this.selectedActivity();
    if (!activity) {
      return null;
    }
    return (
      this.results().find((r) => r.activityRecordId === activity.id && r.isCurrent) ?? null
    );
  });

  readonly selectedCalcState = computed(() =>
    mapSelectedCalcState(this.currentResultForSelected()),
  );

  readonly calculationActionLabel = computed(() => {
    switch (this.selectedCalcState()) {
      case 'stale':
        return 'Update calculation';
      case 'valid':
        return 'Calculate again';
      case 'missing':
        return 'Calculate';
      default:
        return 'Calculate';
    }
  });

  readonly platformDefaultAvailable = computed(() => {
    const resolved = this.platformDefault();
    return !!resolved?.resolved && resolved.factorValue != null;
  });

  readonly factorMode = computed(() => {
    this.formEpoch();
    return this.form.controls.factorSourceMode.value as CbamPurchasedElectricityFactorSourceMode;
  });

  readonly canExecute = computed(() => {
    this.formEpoch();
    if (!this.canConfigure() || !this.canMutate() || this.submitting()) {
      return false;
    }
    if (!this.selectedActivity()) {
      return false;
    }
    const mode = this.factorMode();
    if (mode === 'PLATFORM_DEFAULT') {
      return this.platformDefaultAvailable();
    }
    return this.manualFactorClientValid();
  });

  constructor() {
    this.load$
      .pipe(
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          this.loading.set(true);
          this.loadError.set(null);
          this.liveMessage.set('Loading electricity data.');
          const page = this.resultsPage();
          const pageSize = this.resultsPageSize();
          return forkJoin({
            activities: this.api.listActivityRecords(bindingId, { page: 1, pageSize: 100 }),
            readiness: this.api.getPurchasedElectricityReadiness(bindingId),
            summary: this.api.getPurchasedElectricitySummary(bindingId).pipe(
              catchError(() => of(null)),
            ),
            results: this.api.listPurchasedElectricityResults(bindingId, { page, pageSize }),
          }).pipe(
            tap(({ activities, readiness, summary, results }) => {
              if (seq !== this.loadSeq) {
                return;
              }
              this.activities.set(activities.items);
              this.readiness.set(readiness);
              if (summary) {
                this.summary.set(summary);
              }
              this.results.set(results.items);
              this.resultsTotal.set(results.totalItems);
              this.liveMessage.set('Electricity data loaded.');
              const currentId =
                results.items.find((r) => r.isCurrent)?.resultId ?? null;
              if (currentId) {
                untracked(() => this.loadDetail(currentId));
              }
            }),
            catchError((err: unknown) => {
              if (seq === this.loadSeq) {
                this.loadError.set(
                  mapPurchasedElectricityError(err) ||
                    'Electricity data could not be loaded. Try again.',
                );
                this.liveMessage.set('Electricity data could not be loaded.');
              }
              return of(null);
            }),
            finalize(() => {
              if (seq === this.loadSeq) {
                this.loading.set(false);
              }
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe();

    effect(() => {
      const id = this.bindingId();
      if (id) {
        untracked(() => this.reload());
      }
    });

    this.form.controls.factorSourceMode.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((mode) => {
        this.formEpoch.update((n) => n + 1);
        this.actionError.set(null);
        this.clearAttemptState();
        if (mode === 'PLATFORM_DEFAULT') {
          this.refreshPlatformDefault();
        }
      });

    this.form.controls.activityRecordId.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.formEpoch.update((n) => n + 1);
        this.actionError.set(null);
        this.clearAttemptState();
        if (this.form.controls.factorSourceMode.value === 'PLATFORM_DEFAULT') {
          this.refreshPlatformDefault();
        }
      });

    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.formEpoch.update((n) => n + 1);
      this.invalidateAttemptIfMaterialChanged();
    });
  }

  reload(): void {
    this.load$.next(this.bindingId());
  }

  openActivitiesTab(): void {
    this.goToActivities.emit();
  }

  activityLabel(activity: CbamActivityRecord): string {
    const datePart = activity.activityDate ?? 'No date';
    return `Electricity · ${datePart} · ${activity.quantity} ${activity.unit}`;
  }

  refreshPlatformDefault(): void {
    const activity = this.selectedActivity();
    this.platformDefaultLoading.set(true);
    this.platformDefaultError.set(null);
    this.api
      .getPurchasedElectricityDefaultFactor(this.bindingId(), {
        referenceDate: activity?.activityDate ?? null,
      })
      .subscribe({
        next: (resolved) => {
          this.platformDefault.set(resolved);
          this.platformDefaultLoading.set(false);
          if (!resolved.resolved) {
            this.platformDefaultError.set(
              'A verified default factor is not available. Enter a manual factor and its source.',
            );
          }
        },
        error: (err: unknown) => {
          this.platformDefault.set(null);
          this.platformDefaultLoading.set(false);
          this.platformDefaultError.set(mapPurchasedElectricityError(err));
        },
      });
  }

  onHistoryPage(event: PageEvent): void {
    this.resultsPage.set(event.pageIndex + 1);
    this.resultsPageSize.set(event.pageSize);
    this.reload();
  }

  viewDetails(resultId: string): void {
    this.loadDetail(resultId);
  }

  toggleSection(key: string): void {
    this.openSections.update((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }

  isSectionOpen(key: string): boolean {
    return !!this.openSections()[key];
  }

  calculationAriaLabel(): string {
    const activity = this.selectedActivity();
    const label = this.calculationActionLabel();
    if (!activity) {
      return label;
    }
    return `${label} for ${this.activityLabel(activity)}`;
  }

  runCalculationAction(): void {
    if (!this.canExecute() || this.executingGuard) {
      return;
    }
    const state = this.selectedCalcState();
    const forcesNewId = state === 'valid' || state === 'stale';
    if (forcesNewId) {
      this.clearAttemptState();
    }
    this.execute();
  }

  /** Public for tests: inspect active idempotency key. */
  peekClientRequestId(): string | null {
    return this.activeClientRequestId;
  }

  /** Public for tests: seed an in-flight retry ID. */
  seedClientRequestIdForRetry(id: string): void {
    this.activeClientRequestId = id;
    this.activeMaterialKey = this.currentMaterialKey();
  }

  private execute(): void {
    const activity = this.selectedActivity();
    if (!activity || this.executingGuard) {
      return;
    }
    if (!this.canExecute()) {
      return;
    }

    this.executingGuard = true;
    this.actionError.set(null);
    this.successMessage.set(null);

    const material = this.currentMaterialKey();
    if (!this.activeClientRequestId || this.activeMaterialKey !== material) {
      this.activeClientRequestId = createClientRequestId();
      this.activeMaterialKey = material;
    }

    const mode = this.form.controls.factorSourceMode.value;
    const payload: CbamPurchasedElectricityExecuteRequest = {
      clientRequestId: this.activeClientRequestId,
      activityRecordId: activity.id,
      factorSourceMode: mode,
    };

    if (mode === 'MANUAL') {
      const value = this.form.controls.manualValue.value.trim();
      payload.manualFactor = {
        value,
        unit: this.form.controls.manualUnit.value,
        sourceName: this.form.controls.sourceName.value.trim(),
        sourceDocument: this.form.controls.sourceDocument.value.trim(),
        datasetVersion: this.form.controls.datasetVersion.value.trim(),
        referenceDescription: this.form.controls.referenceDescription.value.trim(),
        effectiveDate: optionalTextOrNull(this.form.controls.effectiveDate.value),
      };
    }

    const exportedQty = optionalDecimalOrNull(this.form.controls.exportedQuantity.value);
    const exportedUnit = this.form.controls.exportedUnit.value;
    if (exportedQty != null) {
      payload.exportedElectricityQuantity = exportedQty;
      payload.exportedElectricityUnit = exportedUnit;
    }

    const notes = optionalTextOrNull(this.form.controls.evidenceNotes.value);
    if (notes != null) {
      payload.evidenceNotes = notes;
    }

    this.submitting.set(true);
    this.liveMessage.set('Running electricity calculation.');

    this.api.executePurchasedElectricity(this.bindingId(), payload).subscribe({
      next: (response) => {
        this.submitting.set(false);
        this.executingGuard = false;
        this.clearAttemptState();
        if (response.idempotentReplay) {
          this.successMessage.set(
            'This calculation was already completed. The saved result is shown.',
          );
          this.liveMessage.set('Electricity calculation replayed from saved result.');
        } else {
          this.successMessage.set('Calculation saved.');
          this.liveMessage.set('Electricity calculation completed.');
        }
        this.resultsPage.set(1);
        this.reload();
        untracked(() => this.loadDetail(response.resultId));
      },
      error: (err: unknown) => {
        this.submitting.set(false);
        this.executingGuard = false;
        this.actionError.set(mapPurchasedElectricityError(err));
        this.liveMessage.set('Electricity calculation failed.');
        if (extractErrorCode(err) === 'IDEMPOTENCY_KEY_REUSED') {
          this.clearAttemptState();
        }
        // Preserve last successful summary/results/detail.
      },
    });
  }

  private manualFactorClientValid(): boolean {
    const value = this.form.controls.manualValue.value;
    if (isBlankDecimalInput(value)) {
      return false;
    }
    if (isNegativeDecimalString(value)) {
      return false;
    }
    if (!this.form.controls.manualUnit.value.trim()) {
      return false;
    }
    if (!this.form.controls.sourceName.value.trim()) {
      return false;
    }
    if (!this.form.controls.sourceDocument.value.trim()) {
      return false;
    }
    if (!this.form.controls.datasetVersion.value.trim()) {
      return false;
    }
    if (!this.form.controls.referenceDescription.value.trim()) {
      return false;
    }
    return true;
  }

  private currentMaterialKey(): string {
    const v = this.form.getRawValue();
    return JSON.stringify({
      activityRecordId: v.activityRecordId,
      factorSourceMode: v.factorSourceMode,
      manualValue: v.manualValue.trim(),
      manualUnit: v.manualUnit,
      sourceName: v.sourceName.trim(),
      sourceDocument: v.sourceDocument.trim(),
      datasetVersion: v.datasetVersion.trim(),
      referenceDescription: v.referenceDescription.trim(),
      effectiveDate: v.effectiveDate.trim(),
      exportedQuantity: v.exportedQuantity.trim(),
      exportedUnit: v.exportedUnit,
      evidenceNotes: v.evidenceNotes.trim(),
    });
  }

  private invalidateAttemptIfMaterialChanged(): void {
    if (!this.activeClientRequestId || !this.activeMaterialKey) {
      return;
    }
    if (this.activeMaterialKey !== this.currentMaterialKey()) {
      this.clearAttemptState();
    }
  }

  private clearAttemptState(): void {
    this.activeClientRequestId = null;
    this.activeMaterialKey = null;
  }

  private loadDetail(resultId: string): void {
    this.detailLoading.set(true);
    this.detailError.set(null);
    this.api.getPurchasedElectricityResult(this.bindingId(), resultId).subscribe({
      next: (detail) => {
        this.selectedDetail.set(detail);
        this.detailLoading.set(false);
      },
      error: (err: unknown) => {
        this.detailLoading.set(false);
        this.detailError.set(mapPurchasedElectricityError(err));
        if (err instanceof HttpErrorResponse && err.status === 404) {
          this.selectedDetail.set(null);
        }
      },
    });
  }
}
