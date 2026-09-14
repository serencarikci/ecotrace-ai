import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ReportingPeriod } from '../../core/models/reporting-period.models';
import { AuthService } from '../../core/services/auth.service';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { ReportingPeriodService } from '../../core/services/reporting-period.service';
import { canConfigureCbam } from '../../core/services/roles.util';
import { bindingStatusLabel } from './cbam-display-labels';
import { CbamApiService, CbamPeriodBinding } from './cbam-api.service';

@Component({
  selector: 'app-cbam-period-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './period-list.component.html',
  styleUrl: './cbam-pages.scss',
})
export class CbamPeriodListComponent implements OnInit {
  private readonly api = inject(CbamApiService);
  private readonly periodsApi = inject(ReportingPeriodService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<CbamPeriodBinding[]>([]);
  readonly periods = signal<ReportingPeriod[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canConfigure = canConfigureCbam(this.auth.currentRoles());
  readonly displayedColumns = ['reportingPeriodId', 'status', 'revisionNumber', 'actions'];

  readonly createForm = this.fb.nonNullable.group({
    reportingPeriodId: ['', Validators.required],
  });

  ngOnInit(): void {
    this.load();
    this.periodsApi.list({ page: 1, pageSize: 200 }).subscribe({
      next: (page) => this.periods.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  load(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.api
      .listPeriodBindings({ page: this.page(), pageSize: this.pageSize() })
      .subscribe({
        next: (result) => {
          this.items.set(result.items);
          this.totalItems.set(result.totalItems);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }

  periodLabel(id: string): string {
    const found = this.periods().find((p) => p.id === id);
    return found ? `${found.code} — ${found.name}` : 'Reporting period';
  }

  statusLabel(status: string): string {
    return bindingStatusLabel(status);
  }

  onPage(event: PageEvent): void {
    this.page.set(event.pageIndex + 1);
    this.pageSize.set(event.pageSize);
    this.load();
  }

  create(): void {
    if (!this.canConfigure || this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    const reportingPeriodId = this.createForm.getRawValue().reportingPeriodId;
    this.api.createPeriodBinding({ reportingPeriodId }).subscribe({
      next: () => {
        this.createForm.reset({ reportingPeriodId: '' });
        this.load();
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
