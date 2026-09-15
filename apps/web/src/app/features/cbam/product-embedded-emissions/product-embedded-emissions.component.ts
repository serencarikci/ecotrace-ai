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
  CbamProductEmbeddedEmissionsInternalContribution,
  CbamProductEmbeddedEmissionsPeriodSummary,
  CbamProductEmbeddedEmissionsPrecursorContribution,
  CbamProductEmbeddedEmissionsProductRow,
  CbamProductEmbeddedEmissionsReadiness,
  CbamProductEmbeddedEmissionsResultDetail,
  CbamProductEmbeddedEmissionsResultSummary,
} from '../cbam-api.service';
import {
  createClientRequestId,
  deriveDirectAllocationStatus,
  deriveIndirectAllocationStatus,
  deriveInternalFlowStatus,
  derivePrecursorStatus,
  deriveProcessStatus,
  extractErrorCode,
  formatDecimalDisplay,
  mapDataSourceLabel,
  mapExecutionStatusLabel,
  mapMethodologyLabel,
  mapPeeError,
  mapPeeIssueCode,
  mapPeeStaleReason,
  mapResultLifecycleLabel,
  methodologyNote,
} from './product-embedded-emissions.util';

@Component({
  selector: 'app-cbam-product-embedded-emissions',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatTableModule,
  ],
  templateUrl: './product-embedded-emissions.component.html',
  styleUrl: './product-embedded-emissions.component.scss',
})
export class CbamProductEmbeddedEmissionsComponent {
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
  readonly goToProductProfiles = output<void>();
  readonly goToProduction = output<void>();
  readonly goToDirectEmissions = output<void>();
  readonly goToIndirectEmissions = output<void>();
  readonly goToProcesses = output<void>();
  readonly goToPurchasedInputs = output<void>();
  readonly goToAllocation = output<void>();

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly readiness = signal<CbamProductEmbeddedEmissionsReadiness | null>(null);
  readonly summary = signal<CbamProductEmbeddedEmissionsPeriodSummary | null>(null);
  readonly results = signal<CbamProductEmbeddedEmissionsResultSummary[]>([]);
  readonly resultsTotal = signal(0);
  readonly resultsPage = signal(1);
  readonly resultsPageSize = signal(10);
  readonly selectedDetail = signal<CbamProductEmbeddedEmissionsResultDetail | null>(null);
  readonly selectedProductProfileVersionId = signal<string | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal<string | null>(null);
  readonly submitting = signal(false);
  readonly actionError = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly liveMessage = signal('');
  readonly openSections = signal<Record<string, boolean>>({
    own: true,
    precursors: true,
    internal: true,
    totals: true,
  });

  readonly productColumns = [
    'product',
    'cn',
    'profile',
    'output',
    'direct',
    'indirect',
    'total',
    'specificDirect',
    'specificIndirect',
    'specificTotal',
    'status',
  ] as const;

  readonly historyColumns = [
    'created',
    'method',
    'products',
    'total',
    'status',
    'actions',
  ] as const;

  readonly formatDecimal = formatDecimalDisplay;
  readonly issueMessage = mapPeeIssueCode;
  readonly staleReasonMessage = mapPeeStaleReason;
  readonly lifecycleLabel = mapResultLifecycleLabel;
  readonly executionLabel = mapExecutionStatusLabel;
  readonly methodologyLabel = mapMethodologyLabel;
  readonly methodologyNote = methodologyNote;
  readonly dataSourceLabel = mapDataSourceLabel;

  constructor() {
    this.load$
      .pipe(
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          this.loading.set(true);
          this.loadError.set(null);
          this.liveMessage.set('Loading product results.');
          const page = this.resultsPage();
          const pageSize = this.resultsPageSize();
          return forkJoin({
            readiness: this.api.getProductEmbeddedEmissionsReadiness(bindingId),
            summary: this.api.getProductEmbeddedEmissionsSummary(bindingId).pipe(
              catchError(() => of(null)),
            ),
            results: this.api.listProductEmbeddedEmissionsResults(bindingId, {
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
              this.liveMessage.set('Product results loaded.');
              const currentId =
                readiness.currentResultId ??
                results.items.find((r) => r.isCurrent)?.resultId ??
                null;
              if (currentId) {
                untracked(() => this.loadDetail(currentId));
              }
            }),
            catchError((err: unknown) => {
              if (seq === this.loadSeq) {
                this.loadError.set(
                  mapPeeError(err) || 'Product results could not be loaded. Try again.',
                );
                this.liveMessage.set('Product results could not be loaded.');
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
      !!this.readiness()?.rollupReady &&
      !this.submitting()
    );
  }

  executeButtonLabel(): string {
    const readiness = this.readiness();
    const summary = this.summary();
    if (!summary?.currentResultId && !readiness?.currentResultId) {
      return 'Calculate product results';
    }
    if (readiness?.currentIsStale || summary?.currentIsStale) {
      return 'Update product results';
    }
    return 'Calculate again';
  }

  executeRollup(): void {
    if (!this.canExecute() || this.executingGuard) {
      return;
    }
    this.executingGuard = true;
    this.actionError.set(null);
    this.successMessage.set(null);

    const label = this.executeButtonLabel();
    const forcesNewId = label === 'Calculate again' || label === 'Update product results';
    if (forcesNewId || !this.activeClientRequestId) {
      this.activeClientRequestId = createClientRequestId();
    }

    const clientRequestId = this.activeClientRequestId;
    this.submitting.set(true);
    this.liveMessage.set('Calculating product results.');

    this.api
      .executeProductEmbeddedEmissions(this.bindingId(), { clientRequestId })
      .subscribe({
        next: (response) => {
          this.submitting.set(false);
          this.executingGuard = false;
          this.activeClientRequestId = null;
          if (response.idempotentReplay) {
            this.successMessage.set(
              'This calculation was already completed. The saved result is shown.',
            );
            this.liveMessage.set('Product results replayed from saved result.');
          } else {
            this.successMessage.set('Product results saved.');
            this.liveMessage.set('Product results calculated.');
          }
          this.resultsPage.set(1);
          this.reload();
        },
        error: (err: unknown) => {
          this.submitting.set(false);
          this.executingGuard = false;
          this.actionError.set(mapPeeError(err));
          this.liveMessage.set('Product results calculation failed.');
          const code = extractErrorCode(err);
          if (code === 'IDEMPOTENCY_KEY_REUSED') {
            this.activeClientRequestId = null;
          }
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
    this.selectedProductProfileVersionId.set(null);
    this.loadDetail(resultId);
  }

  selectProduct(productProfileVersionId: string): void {
    this.selectedProductProfileVersionId.set(productProfileVersionId);
    this.openSections.set({ own: true, precursors: true, internal: true, totals: true });
  }

  selectedProduct(): CbamProductEmbeddedEmissionsProductRow | null {
    const detail = this.selectedDetail();
    const id = this.selectedProductProfileVersionId();
    if (!detail || !id) {
      return null;
    }
    return detail.products.find((p) => p.productProfileVersionId === id) ?? null;
  }

  precursorRowsForSelected(): CbamProductEmbeddedEmissionsPrecursorContribution[] {
    const detail = this.selectedDetail();
    const id = this.selectedProductProfileVersionId();
    if (!detail || !id) {
      return [];
    }
    return detail.precursorContributions.filter((c) => c.productProfileVersionId === id);
  }

  internalRowsForSelected(): CbamProductEmbeddedEmissionsInternalContribution[] {
    const detail = this.selectedDetail();
    const id = this.selectedProductProfileVersionId();
    if (!detail || !id) {
      return [];
    }
    return detail.internalContributions.filter(
      (c) => c.consumerProductProfileVersionId === id,
    );
  }

  supplierProductName(supplierProfileVersionId: string): string {
    const detail = this.selectedDetail();
    if (!detail) {
      return supplierProfileVersionId;
    }
    const match = detail.products.find(
      (p) => p.productProfileVersionId === supplierProfileVersionId,
    );
    return match?.productName?.trim() || match?.cnDisplayCode || supplierProfileVersionId;
  }

  productStatusLabel(): string {
    const summary = this.summary();
    if (!summary?.currentResultId) {
      return '—';
    }
    if (summary.currentIsStale) {
      return 'Out of date';
    }
    return 'Current';
  }

  directAllocationStatus(): string {
    const ready = this.readiness();
    if (!ready) {
      return '—';
    }
    return deriveDirectAllocationStatus({
      resultId: ready.directEmissionsAllocationResultId,
      stale: ready.directEmissionsAllocationStale,
      blockingIssueCodes: ready.blockingIssueCodes,
    });
  }

  indirectAllocationStatus(): string {
    const ready = this.readiness();
    if (!ready) {
      return '—';
    }
    return deriveIndirectAllocationStatus({
      resultId: ready.indirectEmissionsAllocationResultId,
      stale: ready.indirectEmissionsAllocationStale,
      blockingIssueCodes: ready.blockingIssueCodes,
    });
  }

  processStatus(): string {
    const ready = this.readiness();
    return ready ? deriveProcessStatus(ready.blockingIssueCodes) : '—';
  }

  precursorStatus(): string {
    const ready = this.readiness();
    return ready ? derivePrecursorStatus(ready.blockingIssueCodes) : '—';
  }

  internalFlowStatus(): string {
    const ready = this.readiness();
    return ready ? deriveInternalFlowStatus(ready.blockingIssueCodes) : '—';
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
    this.api.getProductEmbeddedEmissionsResult(this.bindingId(), resultId).subscribe({
      next: (detail) => {
        this.selectedDetail.set(detail);
        this.detailLoading.set(false);
        const currentSelected = this.selectedProductProfileVersionId();
        const stillPresent =
          currentSelected &&
          detail.products.some((p) => p.productProfileVersionId === currentSelected);
        if (!stillPresent) {
          this.selectedProductProfileVersionId.set(
            detail.products[0]?.productProfileVersionId ?? null,
          );
        }
      },
      error: (err: unknown) => {
        this.detailLoading.set(false);
        this.detailError.set(mapPeeError(err));
        if (err instanceof HttpErrorResponse && err.status === 404) {
          this.selectedDetail.set(null);
        }
      },
    });
  }
}
