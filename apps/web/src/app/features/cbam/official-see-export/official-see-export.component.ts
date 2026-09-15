import { DatePipe } from '@angular/common';
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
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import {
  Subscription,
  Subject,
  forkJoin,
  of,
  timer,
} from 'rxjs';
import {
  catchError,
  finalize,
  switchMap,
  takeWhile,
  tap,
} from 'rxjs/operators';
import {
  CbamApiService,
  CbamOfficialSeeExportArtifact,
  CbamOfficialSeeExportReadiness,
  CbamOfficialSeeExportRun,
} from '../cbam-api.service';
import {
  OFFICIAL_SEE_CAPACITY_LIMITS,
  OfficialSeeBlockingIssue,
  OfficialSeeNavTarget,
  canDownloadOfficialSeeRun,
  capacityStatusLabel,
  createClientRequestId,
  extractErrorCode,
  formatFileSizeBytes,
  isActiveGenerationStatus,
  mapBlockingIssue,
  mapGenerationUiStatus,
  mapOfficialSeeError,
  mapParityLabel,
  mapValidationLabel,
  sanitizeDownloadFileName,
} from './official-see-export.util';

@Component({
  selector: 'app-cbam-official-see-export',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatProgressSpinnerModule, MatTableModule],
  templateUrl: './official-see-export.component.html',
  styleUrl: './official-see-export.component.scss',
})
export class CbamOfficialSeeExportComponent {
  private readonly api = inject(CbamApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly load$ = new Subject<string>();
  private loadSeq = 0;

  /** In-memory only; never persisted to localStorage. */
  private activeClientRequestId: string | null = null;
  private executingGuard = false;
  private pollSub: Subscription | null = null;
  private pollGeneration = 0;

  readonly bindingId = input.required<string>();
  readonly canConfigure = input(false);
  readonly canMutate = input(false);

  readonly goToProductProfiles = output<void>();
  readonly goToProduction = output<void>();
  readonly goToDirectEmissions = output<void>();
  readonly goToIndirectEmissions = output<void>();
  readonly goToProcesses = output<void>();
  readonly goToPurchasedInputs = output<void>();
  readonly goToProductResults = output<void>();
  readonly goToAllocation = output<void>();

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly readiness = signal<CbamOfficialSeeExportReadiness | null>(null);
  readonly runs = signal<CbamOfficialSeeExportRun[]>([]);
  readonly activeRun = signal<CbamOfficialSeeExportRun | null>(null);
  /** Last successful downloadable artifact; kept after a later failed generation. */
  readonly currentArtifact = signal<CbamOfficialSeeExportArtifact | null>(null);
  readonly currentDownloadableRun = signal<CbamOfficialSeeExportRun | null>(null);
  readonly submitting = signal(false);
  readonly actionError = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly liveMessage = signal('');
  readonly downloadingRunId = signal<string | null>(null);

  readonly historyColumns = [
    'status',
    'created',
    'template',
    'mapping',
    'validation',
    'parity',
    'size',
    'fileName',
    'actions',
  ] as const;

  readonly capacityLimits = OFFICIAL_SEE_CAPACITY_LIMITS;

  constructor() {
    this.load$
      .pipe(
        tap(() => {
          this.stopPolling();
          this.loading.set(true);
          this.loadError.set(null);
        }),
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          return forkJoin({
            readiness: this.api.getOfficialSeeExportReadiness(bindingId).pipe(
              catchError((err: unknown) => {
                if (seq === this.loadSeq) {
                  this.loadError.set(mapOfficialSeeError(err));
                }
                return of(null);
              }),
            ),
            runs: this.api.listOfficialSeeExportRuns(bindingId, { page: 1, pageSize: 20 }).pipe(
              catchError((err: unknown) => {
                if (seq === this.loadSeq) {
                  this.loadError.set(mapOfficialSeeError(err));
                }
                return of({ items: [] as CbamOfficialSeeExportRun[], total: 0, page: 1, pageSize: 20 });
              }),
            ),
          }).pipe(
            tap((result) => {
              if (seq !== this.loadSeq) {
                return;
              }
              this.readiness.set(result.readiness);
              this.runs.set(result.runs.items);
              this.hydrateCurrentFromHistory(result.runs.items);
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
      untracked(() => {
        this.activeClientRequestId = null;
        this.executingGuard = false;
        this.stopPolling();
        this.activeRun.set(null);
        this.actionError.set(null);
        this.successMessage.set(null);
        this.liveMessage.set('');
        this.currentArtifact.set(null);
        this.currentDownloadableRun.set(null);
        if (id) {
          this.load$.next(id);
        }
      });
    });

    this.destroyRef.onDestroy(() => this.stopPolling());
  }

  blockingIssues(): OfficialSeeBlockingIssue[] {
    return (this.readiness()?.blockingIssueCodes ?? []).map(mapBlockingIssue);
  }

  capacityRows(): Array<{ key: string; label: string; status: string; ok: boolean }> {
    const cap = this.readiness()?.capacity;
    if (!cap) {
      return [];
    }
    type CapKey = 'installations' | 'goods' | 'processes' | 'precursors';
    const rows: Array<{ key: CapKey; label: string }> = [
      { key: 'installations', label: 'Installations' },
      { key: 'goods', label: 'Products' },
      { key: 'processes', label: 'Processes' },
      { key: 'precursors', label: 'Precursors' },
    ];
    return rows.map((row) => {
      const used = cap[row.key];
      const info = capacityStatusLabel(used, this.capacityLimits[row.key]);
      return { key: row.key, label: row.label, status: info.label, ok: info.ok };
    });
  }

  canGenerate(): boolean {
    const ready = this.readiness()?.ready === true;
    return (
      this.canConfigure() &&
      this.canMutate() &&
      ready &&
      !this.submitting() &&
      !isActiveGenerationStatus(this.activeRun()?.generationStatus)
    );
  }

  generateDisabledReason(): string | null {
    if (!this.canConfigure()) {
      return 'You need configure permission to generate the official Excel.';
    }
    if (!this.canMutate()) {
      return 'This reporting period is locked. Open data collection to generate.';
    }
    if (this.readiness()?.ready !== true) {
      return 'Official Excel is not ready. Fix the blocking issues first.';
    }
    if (this.submitting() || isActiveGenerationStatus(this.activeRun()?.generationStatus)) {
      return 'An official Excel generation is already in progress.';
    }
    return null;
  }

  generationStatusLabel(): string {
    return mapGenerationUiStatus(this.activeRun());
  }

  runStatusLabel(run: CbamOfficialSeeExportRun): string {
    return mapGenerationUiStatus(run);
  }

  parityLabel(status: string): string {
    return mapParityLabel(status);
  }

  validationLabel(status: string): string {
    return mapValidationLabel(status);
  }

  fileSizeLabel(bytes: number | null | undefined): string {
    return formatFileSizeBytes(bytes);
  }

  safeFileName(name: string | null | undefined): string {
    return sanitizeDownloadFileName(name);
  }

  canDownloadRun(run: CbamOfficialSeeExportRun): boolean {
    return canDownloadOfficialSeeRun(run);
  }

  navigate(target: OfficialSeeNavTarget): void {
    switch (target) {
      case 'productProfiles':
        this.goToProductProfiles.emit();
        break;
      case 'production':
        this.goToProduction.emit();
        break;
      case 'directEmissions':
        this.goToDirectEmissions.emit();
        break;
      case 'indirectEmissions':
        this.goToIndirectEmissions.emit();
        break;
      case 'processes':
        this.goToProcesses.emit();
        break;
      case 'purchasedInputs':
        this.goToPurchasedInputs.emit();
        break;
      case 'productResults':
        this.goToProductResults.emit();
        break;
      case 'allocation':
        this.goToAllocation.emit();
        break;
    }
  }

  refresh(): void {
    const id = this.bindingId();
    if (id) {
      this.load$.next(id);
    }
  }

  generate(): void {
    if (!this.canGenerate() || this.executingGuard) {
      return;
    }
    this.executingGuard = true;
    this.submitting.set(true);
    this.actionError.set(null);
    this.successMessage.set(null);
    this.liveMessage.set('Preparing');

    if (!this.activeClientRequestId) {
      this.activeClientRequestId = createClientRequestId();
    }
    const clientRequestId = this.activeClientRequestId;
    const bindingId = this.bindingId();

    this.api.createOfficialSeeExportRun(bindingId, { clientRequestId }).subscribe({
      next: (run) => {
        this.executingGuard = false;
        this.submitting.set(false);
        this.handleRunResult(run);
      },
      error: (err: unknown) => {
        this.executingGuard = false;
        this.submitting.set(false);
        const code = extractErrorCode(err);
        if (code === 'IDEMPOTENCY_KEY_REUSED') {
          this.activeClientRequestId = null;
        }
        this.actionError.set(mapOfficialSeeError(err));
        this.liveMessage.set('Failed');
      },
    });
  }

  downloadRun(run: CbamOfficialSeeExportRun): void {
    if (!this.canDownloadRun(run) || this.downloadingRunId()) {
      return;
    }
    this.downloadingRunId.set(run.id);
    this.actionError.set(null);
    this.api.listOfficialSeeExportArtifacts(run.id).subscribe({
      next: (artifacts) => {
        const artifact =
          artifacts.find((a) => a.artifactType === 'XLSX') ??
          artifacts.find((a) => a.fileName.toLowerCase().endsWith('.xlsx')) ??
          artifacts[0];
        if (!artifact) {
          this.downloadingRunId.set(null);
          this.actionError.set('The official Excel file was not found.');
          return;
        }
        this.downloadArtifact(artifact, run);
      },
      error: (err: unknown) => {
        this.downloadingRunId.set(null);
        this.actionError.set(mapOfficialSeeError(err));
      },
    });
  }

  downloadCurrent(): void {
    const run = this.currentDownloadableRun();
    if (run) {
      this.downloadRun(run);
    }
  }

  private downloadArtifact(
    artifact: CbamOfficialSeeExportArtifact,
    run: CbamOfficialSeeExportRun,
  ): void {
    this.api.downloadOfficialSeeExportArtifact(artifact.id).subscribe({
      next: (blob) => {
        this.downloadingRunId.set(null);
        const fileName = sanitizeDownloadFileName(artifact.fileName);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        a.rel = 'noopener';
        a.click();
        URL.revokeObjectURL(url);
        this.currentArtifact.set(artifact);
        this.currentDownloadableRun.set(run);
        this.liveMessage.set('Ready to download');
      },
      error: (err: unknown) => {
        this.downloadingRunId.set(null);
        this.actionError.set(mapOfficialSeeError(err));
      },
    });
  }

  private handleRunResult(run: CbamOfficialSeeExportRun): void {
    this.activeRun.set(run);
    this.mergeRunIntoHistory(run);
    const ui = mapGenerationUiStatus(run);
    this.liveMessage.set(ui);

    if (isActiveGenerationStatus(run.generationStatus)) {
      this.startPolling(run.id);
      return;
    }

    this.activeClientRequestId = null;
    this.stopPolling();

    if (canDownloadOfficialSeeRun(run)) {
      this.successMessage.set(
        run.idempotentReplay
          ? 'Using the existing official Excel for this request.'
          : 'Official Excel is ready to download.',
      );
      this.loadArtifactForRun(run);
      this.refreshReadinessAndHistory();
      return;
    }

    const diagCode =
      typeof run.failureDiagnostics?.['code'] === 'string'
        ? (run.failureDiagnostics['code'] as string)
        : null;
    this.actionError.set(
      diagCode
        ? mapOfficialSeeError({ status: 400, error: { error: { code: diagCode } } })
        : 'The official Excel generation failed.',
    );
    this.refreshReadinessAndHistory();
  }

  private loadArtifactForRun(run: CbamOfficialSeeExportRun): void {
    this.api.listOfficialSeeExportArtifacts(run.id).subscribe({
      next: (artifacts) => {
        const artifact =
          artifacts.find((a) => a.artifactType === 'XLSX') ??
          artifacts.find((a) => a.fileName.toLowerCase().endsWith('.xlsx')) ??
          artifacts[0] ??
          null;
        if (artifact) {
          this.currentArtifact.set(artifact);
          this.currentDownloadableRun.set(run);
        }
      },
      error: () => {
        /* Keep previous successful artifact if listing fails after a new success. */
      },
    });
  }

  private refreshReadinessAndHistory(): void {
    const bindingId = this.bindingId();
    forkJoin({
      readiness: this.api.getOfficialSeeExportReadiness(bindingId).pipe(catchError(() => of(null))),
      runs: this.api
        .listOfficialSeeExportRuns(bindingId, { page: 1, pageSize: 20 })
        .pipe(catchError(() => of(null))),
    }).subscribe({
      next: (result) => {
        if (result.readiness) {
          this.readiness.set(result.readiness);
        }
        if (result.runs) {
          this.runs.set(result.runs.items);
          // Do not clear currentArtifact on failure — hydrate only prefers newer success.
          this.preferSuccessfulCurrent(result.runs.items);
        }
      },
    });
  }

  private preferSuccessfulCurrent(items: CbamOfficialSeeExportRun[]): void {
    const current = this.currentDownloadableRun();
    if (current && canDownloadOfficialSeeRun(current)) {
      return;
    }
    this.hydrateCurrentFromHistory(items);
  }

  private hydrateCurrentFromHistory(items: CbamOfficialSeeExportRun[]): void {
    const existing = this.currentDownloadableRun();
    if (existing && canDownloadOfficialSeeRun(existing)) {
      return;
    }
    const latestOk = items.find((r) => canDownloadOfficialSeeRun(r));
    if (!latestOk) {
      return;
    }
    this.loadArtifactForRun(latestOk);
  }

  private mergeRunIntoHistory(run: CbamOfficialSeeExportRun): void {
    const existing = this.runs();
    const without = existing.filter((r) => r.id !== run.id);
    this.runs.set([run, ...without]);
  }

  private startPolling(runId: string): void {
    this.stopPolling();
    const generation = ++this.pollGeneration;
    const bindingId = this.bindingId();
    this.pollSub = timer(0, 2000)
      .pipe(
        switchMap(() =>
          this.api.getOfficialSeeExportRun(runId).pipe(
            catchError((err: unknown) => {
              if (generation === this.pollGeneration) {
                this.actionError.set(mapOfficialSeeError(err));
                this.liveMessage.set('Failed');
                this.stopPolling();
              }
              return of(null);
            }),
          ),
        ),
        takeWhile((run) => {
          if (generation !== this.pollGeneration) {
            return false;
          }
          if (!run) {
            return false;
          }
          if (this.bindingId() !== bindingId) {
            return false;
          }
          if (!this.canConfigure() && !this.canMutate()) {
            // Permission loss: stop active generation polling.
            return false;
          }
          this.activeRun.set(run);
          this.mergeRunIntoHistory(run);
          this.liveMessage.set(mapGenerationUiStatus(run));
          return isActiveGenerationStatus(run.generationStatus);
        }, true),
      )
      .subscribe({
        next: (run) => {
          if (!run || generation !== this.pollGeneration) {
            return;
          }
          if (!isActiveGenerationStatus(run.generationStatus)) {
            this.handleRunResult(run);
          }
        },
        complete: () => {
          if (generation === this.pollGeneration) {
            this.pollSub = null;
          }
        },
      });
  }

  private stopPolling(): void {
    this.pollGeneration += 1;
    this.pollSub?.unsubscribe();
    this.pollSub = null;
  }
}
