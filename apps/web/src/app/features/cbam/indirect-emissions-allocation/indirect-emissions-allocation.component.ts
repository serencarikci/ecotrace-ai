import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { Subject, forkJoin, of } from 'rxjs';
import { catchError, finalize, switchMap, tap } from 'rxjs/operators';
import {
  CbamApiService,
  CbamIndirectEmissionsAllocationPeriodSummary,
  CbamIndirectEmissionsAllocationReadiness,
  CbamIndirectEmissionsAllocationResultDetail,
  CbamIndirectEmissionsAllocationResultSummary,
} from '../cbam-api.service';
import {
  createClientRequestId,
  extractErrorCode,
  formatDecimalDisplay,
  formatMonthLabel,
  mapAllocationError,
  mapAllocationIssueCode,
  mapAllocationStaleReason,
  mapBalanceStatusLabel,
  mapExecutionStatusLabel,
  mapResultLifecycleLabel,
  mapSubsystemStatusLabel,
  monthTotalField,
} from './indirect-emissions-allocation.util';

@Component({
  selector: 'app-cbam-indirect-emissions-allocation',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatTableModule,
  ],
  templateUrl: './indirect-emissions-allocation.component.html',
  styleUrl: './indirect-emissions-allocation.component.scss',
})
export class CbamIndirectEmissionsAllocationComponent {
  private readonly api = inject(CbamApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly load$ = new Subject<string>();
  private loadSeq = 0;

  /** In-memory only; never persisted to localStorage. */
  private activeClientRequestId: string | null = null;
  private executingGuard = false;

  readonly bindingId = input.required<string>();
  readonly canConfigure = input(false);
  readonly canMutate = input(false);
  readonly goToIndirectEmissions = output<void>();
  readonly goToProduction = output<void>();
  readonly goToMonthlyAllocationData = output<void>();

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly readiness = signal<CbamIndirectEmissionsAllocationReadiness | null>(null);
  readonly summary = signal<CbamIndirectEmissionsAllocationPeriodSummary | null>(null);
  readonly results = signal<CbamIndirectEmissionsAllocationResultSummary[]>([]);
  readonly resultsTotal = signal(0);
  readonly resultsPage = signal(1);
  readonly resultsPageSize = signal(10);
  readonly selectedDetail = signal<CbamIndirectEmissionsAllocationResultDetail | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal<string | null>(null);
  readonly submitting = signal(false);
  readonly actionError = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly liveMessage = signal('');
  readonly openSections = signal<Record<string, boolean>>({
    overview: true,
    monthly: false,
    sources: false,
    products: false,
    exported: false,
    balance: false,
    method: false,
  });

  readonly historyColumns = [
    'created',
    'status',
    'cbam',
    'allocated',
    'balance',
    'actions',
  ] as const;

  readonly formatDecimal = formatDecimalDisplay;
  readonly formatMonth = formatMonthLabel;
  readonly issueMessage = mapAllocationIssueCode;
  readonly staleReasonMessage = mapAllocationStaleReason;
  readonly lifecycleLabel = mapResultLifecycleLabel;
  readonly balanceLabel = mapBalanceStatusLabel;
  readonly executionLabel = mapExecutionStatusLabel;
  readonly subsystemLabel = mapSubsystemStatusLabel;
  readonly monthField = monthTotalField;

  constructor() {
    this.load$
      .pipe(
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          this.loading.set(true);
          this.loadError.set(null);
          this.liveMessage.set('Loading allocation data.');
          const page = this.resultsPage();
          const pageSize = this.resultsPageSize();
          return forkJoin({
            readiness: this.api.getIndirectEmissionsAllocationReadiness(bindingId),
            summary: this.api.getIndirectEmissionsAllocationSummary(bindingId).pipe(
              catchError(() => of(null)),
            ),
            results: this.api.listIndirectEmissionsAllocationResults(bindingId, {
              page,
              pageSize,
            }),
          }).pipe(
            tap(({ readiness, summary, results }) => {
              if (seq !== this.loadSeq) {
                return;
              }
              this.readiness.set(readiness);
              if (summary) {
                this.summary.set(summary);
              }
              this.results.set(results.items);
              this.resultsTotal.set(results.totalItems);
              this.liveMessage.set('Allocation data loaded.');
              const currentId =
                readiness.currentAllocationId ??
                results.items.find((r) => r.isCurrent)?.resultId ??
                null;
              if (currentId) {
                untracked(() => this.loadDetail(currentId));
              }
            }),
            catchError((err: unknown) => {
              if (seq === this.loadSeq) {
                this.loadError.set(
                  mapAllocationError(err) ||
                    'Allocation data could not be loaded. Try again.',
                );
                this.liveMessage.set('Allocation data could not be loaded.');
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
  }

  reload(): void {
    this.load$.next(this.bindingId());
  }

  canExecute(): boolean {
    return (
      this.canConfigure() &&
      this.canMutate() &&
      !!this.readiness()?.allocationReady &&
      !this.submitting()
    );
  }

  executeButtonLabel(): string {
    const readiness = this.readiness();
    const summary = this.summary();
    if (!summary?.currentResultId && !readiness?.currentAllocationId) {
      return 'Calculate allocation';
    }
    if (readiness?.currentAllocationStale || summary?.currentIsStale) {
      return 'Update allocation';
    }
    return 'Calculate again';
  }

  executeAllocation(): void {
    if (!this.canExecute() || this.executingGuard) {
      return;
    }
    this.executingGuard = true;
    this.actionError.set(null);
    this.successMessage.set(null);

    const label = this.executeButtonLabel();
    const forcesNewId = label === 'Calculate again' || label === 'Update allocation';
    if (forcesNewId || !this.activeClientRequestId) {
      this.activeClientRequestId = createClientRequestId();
    }

    const clientRequestId = this.activeClientRequestId;
    this.submitting.set(true);
    this.liveMessage.set('Running allocation.');

    this.api
      .executeIndirectEmissionsAllocation(this.bindingId(), { clientRequestId })
      .subscribe({
        next: (response) => {
          this.submitting.set(false);
          this.executingGuard = false;
          this.activeClientRequestId = null;
          if (response.idempotentReplay) {
            this.successMessage.set(
              'This allocation was already completed. The saved result is shown.',
            );
            this.liveMessage.set('Allocation replayed from saved result.');
          } else {
            this.successMessage.set('Allocation saved.');
            this.liveMessage.set('Allocation completed.');
          }
          this.resultsPage.set(1);
          this.reload();
        },
        error: (err: unknown) => {
          this.submitting.set(false);
          this.executingGuard = false;
          this.actionError.set(mapAllocationError(err));
          this.liveMessage.set('Allocation failed.');
          const code = extractErrorCode(err);
          if (code === 'IDEMPOTENCY_KEY_REUSED') {
            this.activeClientRequestId = null;
          }
          // Keep last successful summary/results/detail visible.
        },
      });
  }

  /** Public for tests: inspect active idempotency key. */
  peekClientRequestId(): string | null {
    return this.activeClientRequestId;
  }

  /** Public for tests: seed an in-flight retry ID. */
  seedClientRequestIdForRetry(id: string): void {
    this.activeClientRequestId = id;
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

  private loadDetail(resultId: string): void {
    this.detailLoading.set(true);
    this.detailError.set(null);
    this.api.getIndirectEmissionsAllocationResult(this.bindingId(), resultId).subscribe({
      next: (detail) => {
        this.selectedDetail.set(detail);
        this.detailLoading.set(false);
      },
      error: (err: unknown) => {
        this.detailLoading.set(false);
        this.detailError.set(mapAllocationError(err));
        if (err instanceof HttpErrorResponse && err.status === 404) {
          this.selectedDetail.set(null);
        }
      },
    });
  }
}
