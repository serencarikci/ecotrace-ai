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
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { Subject, forkJoin, of } from 'rxjs';
import { catchError, finalize, switchMap, tap } from 'rxjs/operators';
import { ApiErrorBody } from '../../../core/models/api.models';
import { extractApiErrorMessage } from '../../../core/services/error.util';
import {
  CbamApiService,
  CbamCombustionCompatibilityItem,
  CbamMonthlyProductionBasis,
  CbamMonthlyProductionBasisSummary,
  CbamProductionReconciliationMonth,
} from '../cbam-api.service';
import {
  MASS_UNIT_OPTIONS,
  formatCbamShareDisplay,
  formatMonthLabel,
  isNegativeQuantitySyntax,
  isValidQuantitySyntax,
  mapCoverageLabel,
  mapIssueCodeMessage,
  mapReconciliationLabel,
  quantityPayloadValue,
} from './monthly-allocation-data.util';

export interface MonthlyRowView {
  monthStart: string;
  coverage: string;
  record: CbamMonthlyProductionBasis | null;
  reconciliation: CbamProductionReconciliationMonth | null;
  issueCodes: string[];
}

@Component({
  selector: 'app-cbam-monthly-allocation-data',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './monthly-allocation-data.component.html',
  styleUrl: './monthly-allocation-data.component.scss',
})
export class CbamMonthlyAllocationDataComponent {
  private readonly api = inject(CbamApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);
  private readonly load$ = new Subject<string>();
  private loadSeq = 0;

  readonly bindingId = input.required<string>();
  readonly canConfigure = input(false);
  readonly canMutate = input(false);
  readonly goToDirectEmissions = output<void>();

  readonly summaryLoading = signal(false);
  readonly summaryError = signal<string | null>(null);
  readonly summary = signal<CbamMonthlyProductionBasisSummary | null>(null);
  readonly rowsByMonth = signal<Record<string, CbamMonthlyProductionBasis>>({});
  readonly editingMonth = signal<string | null>(null);
  readonly savingMonth = signal<string | null>(null);
  readonly rowError = signal<string | null>(null);
  readonly liveMessage = signal<string>('');
  readonly concurrencyMonth = signal<string | null>(null);

  readonly massUnits = MASS_UNIT_OPTIONS;

  readonly editForm = this.fb.nonNullable.group({
    totalProductionQuantity: [''],
    cbamQuantity: [''],
    quantityUnit: ['t'],
  });

  constructor() {
    this.load$
      .pipe(
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          this.summaryLoading.set(true);
          this.summaryError.set(null);
          return forkJoin({
            summary: this.api.getMonthlyProductionBasisSummary(bindingId),
            page: this.api.listMonthlyProductionBasis(bindingId, { page: 1, pageSize: 100 }),
          }).pipe(
            tap(({ summary, page }) => {
              if (seq !== this.loadSeq) {
                return;
              }
              this.summary.set(summary);
              const map: Record<string, CbamMonthlyProductionBasis> = {};
              for (const row of page.items) {
                map[row.monthStart] = row;
              }
              this.rowsByMonth.set(map);
            }),
            catchError((err: unknown) => {
              if (seq === this.loadSeq) {
                this.summaryError.set(
                  extractApiErrorMessage(err, 'Monthly allocation data could not be loaded.'),
                );
              }
              return of(null);
            }),
            finalize(() => {
              if (seq === this.loadSeq) {
                this.summaryLoading.set(false);
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
        if (id) {
          this.reload();
        }
      });
    });
  }

  reload(): void {
    const id = this.bindingId();
    if (!id) {
      return;
    }
    this.load$.next(id);
  }

  monthRows(): MonthlyRowView[] {
    const summary = this.summary();
    if (!summary) {
      return [];
    }
    const rows = this.rowsByMonth();
    const reconByMonth = new Map(
      summary.productionReconciliation.map((r) => [r.monthStart, r] as const),
    );
    return summary.monthCoverage.map((c) => ({
      monthStart: c.monthStart,
      coverage: c.coverage,
      record: rows[c.monthStart] ?? null,
      reconciliation: reconByMonth.get(c.monthStart) ?? null,
      issueCodes: c.issueCodes,
    }));
  }

  monthLabel = formatMonthLabel;
  coverageLabel = mapCoverageLabel;
  shareDisplay = formatCbamShareDisplay;
  reconciliationLabel = mapReconciliationLabel;
  issueMessage = mapIssueCodeMessage;

  summaryReadyText(): string {
    const s = this.summary();
    if (!s) {
      return '';
    }
    return s.allocationBasisReady
      ? 'Monthly data is ready.'
      : 'Complete the monthly data before allocation.';
  }

  blockingMessages(): Array<{ code: string; text: string }> {
    return (this.summary()?.blockingIssueCodes ?? []).map((code) => ({
      code,
      text: this.issueMessage(code),
    }));
  }

  combustionItems(): CbamCombustionCompatibilityItem[] {
    return (this.summary()?.combustionItems ?? []).filter((i) => i.status === 'BLOCKED');
  }

  startEdit(row: MonthlyRowView): void {
    if (!this.canMutate()) {
      return;
    }
    this.rowError.set(null);
    this.concurrencyMonth.set(null);
    this.editingMonth.set(row.monthStart);
    this.editForm.setValue({
      totalProductionQuantity: row.record?.totalProductionQuantity ?? '',
      cbamQuantity: row.record?.cbamQuantity ?? '',
      quantityUnit: row.record?.quantityUnit ?? 't',
    });
  }

  cancelEdit(): void {
    this.editingMonth.set(null);
    this.rowError.set(null);
    this.concurrencyMonth.set(null);
  }

  clientValidationError(): string | null {
    const v = this.editForm.getRawValue();
    if (!v.quantityUnit) {
      return 'Select a unit.';
    }
    if (!(MASS_UNIT_OPTIONS as readonly string[]).includes(v.quantityUnit)) {
      return 'Use a supported mass unit.';
    }
    for (const field of [v.totalProductionQuantity, v.cbamQuantity]) {
      if (isNegativeQuantitySyntax(field)) {
        return 'Value cannot be negative.';
      }
      if (!isValidQuantitySyntax(field)) {
        return 'Enter a valid number.';
      }
    }
    return null;
  }

  saveMonth(row: MonthlyRowView): void {
    if (!this.canMutate() || this.savingMonth()) {
      return;
    }
    const clientErr = this.clientValidationError();
    if (clientErr) {
      this.rowError.set(clientErr);
      this.liveMessage.set(clientErr);
      return;
    }
    const v = this.editForm.getRawValue();
    const total = quantityPayloadValue(v.totalProductionQuantity);
    const cbam = quantityPayloadValue(v.cbamQuantity);
    this.savingMonth.set(row.monthStart);
    this.rowError.set(null);
    this.concurrencyMonth.set(null);

    const req$ = row.record
      ? this.api.updateMonthlyProductionBasis(row.record.id, {
          rowVersion: row.record.rowVersion,
          totalProductionQuantity: total,
          cbamQuantity: cbam,
          quantityUnit: v.quantityUnit,
        })
      : this.api.createMonthlyProductionBasis(this.bindingId(), {
          monthStart: row.monthStart,
          totalProductionQuantity: total,
          cbamQuantity: cbam,
          quantityUnit: v.quantityUnit,
        });

    req$.subscribe({
      next: () => {
        this.savingMonth.set(null);
        this.editingMonth.set(null);
        this.liveMessage.set(`Saved ${formatMonthLabel(row.monthStart)}.`);
        this.reload();
      },
      error: (err: unknown) => {
        this.savingMonth.set(null);
        if (err instanceof HttpErrorResponse && err.status === 409) {
          this.concurrencyMonth.set(row.monthStart);
          this.rowError.set('This record changed. Reload it and try again.');
          this.liveMessage.set('This record changed. Reload it and try again.');
          return;
        }
        const mapped = this.mapSaveError(err);
        this.rowError.set(mapped);
        this.liveMessage.set(mapped);
      },
    });
  }

  reloadMonth(row: MonthlyRowView): void {
    this.cancelEdit();
    this.reload();
    this.liveMessage.set(`Reloaded ${formatMonthLabel(row.monthStart)}.`);
  }

  deleteMonth(row: MonthlyRowView): void {
    if (!this.canMutate() || !row.record) {
      return;
    }
    const ok = confirm(
      `Delete this monthly record?\n\nYou will need to enter ${formatMonthLabel(row.monthStart)} again before allocation.`,
    );
    if (!ok) {
      return;
    }
    this.savingMonth.set(row.monthStart);
    this.api.deleteMonthlyProductionBasis(row.record.id).subscribe({
      next: () => {
        this.savingMonth.set(null);
        this.editingMonth.set(null);
        this.liveMessage.set(`${formatMonthLabel(row.monthStart)} deleted.`);
        this.reload();
      },
      error: (err: unknown) => {
        this.savingMonth.set(null);
        const mapped = extractApiErrorMessage(err, 'The monthly record could not be deleted.');
        this.rowError.set(mapped);
        this.liveMessage.set(mapped);
      },
    });
  }

  openDirectEmissions(): void {
    this.goToDirectEmissions.emit();
  }

  private mapSaveError(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const body = error.error as ApiErrorBody | null;
      const details = body?.error?.details ?? [];
      const code = details
        .map((d) => (d as { code?: string }).code)
        .find((c): c is string => typeof c === 'string' && c.length > 0);
      if (code) {
        return mapIssueCodeMessage(code);
      }
    }
    return extractApiErrorMessage(error, 'The monthly record could not be saved.');
  }
}
