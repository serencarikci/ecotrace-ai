import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivityRecordService } from '../../core/services/activity-record.service';
import { FacilityService } from '../../core/services/facility.service';
import { ReferenceService } from '../../core/services/reference.service';
import { ReportingPeriodService } from '../../core/services/reporting-period.service';
import { AuthService } from '../../core/services/auth.service';
import { ActivityRecord, ACTIVITY_STATUSES } from '../../core/models/activity-record.models';
import { Facility } from '../../core/models/facility.models';
import { ActivityType } from '../../core/models/reference.models';
import { ReportingPeriod } from '../../core/models/reporting-period.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canWriteActivity } from '../../core/services/roles.util';

@Component({
  selector: 'app-activity-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './activity-list.component.html',
})
export class ActivityListComponent implements OnInit {
  private readonly api = inject(ActivityRecordService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly referenceApi = inject(ReferenceService);
  private readonly periodsApi = inject(ReportingPeriodService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<ActivityRecord[]>([]);
  readonly facilities = signal<Facility[]>([]);
  readonly activityTypes = signal<ActivityType[]>([]);
  readonly periods = signal<ReportingPeriod[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canWrite = canWriteActivity(this.auth.currentRoles());
  readonly statuses = ACTIVITY_STATUSES;
  readonly displayedColumns = [
    'activityDate',
    'quantity',
    'unitCode',
    'status',
    'reportingPeriodId',
    'actions',
  ];

  readonly filters = this.fb.nonNullable.group({
    search: [''],
    facilityId: [''],
    activityTypeId: [''],
    reportingPeriodId: [''],
    status: [''],
    dateFrom: [''],
    dateTo: [''],
  });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100 }).subscribe({
      next: (p) => this.facilities.set(p.items),
    });
    this.referenceApi.listActivityTypes({ activeOnly: true }).subscribe({
      next: (p) => this.activityTypes.set(p.items),
    });
    this.periodsApi.list({ page: 1, pageSize: 100 }).subscribe({
      next: (p) => this.periods.set(p.items),
    });
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    const f = this.filters.getRawValue();
    this.api
      .list({
        page: this.page(),
        pageSize: this.pageSize(),
        search: f.search || undefined,
        facilityId: f.facilityId || undefined,
        activityTypeId: f.activityTypeId || undefined,
        reportingPeriodId: f.reportingPeriodId || undefined,
        status: f.status || undefined,
        dateFrom: f.dateFrom || undefined,
        dateTo: f.dateTo || undefined,
        sortBy: 'createdAt',
        sortDirection: 'desc',
      })
      .subscribe({
        next: (r) => {
          this.items.set(r.items);
          this.totalItems.set(r.totalItems);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }

  applyFilters(): void {
    this.page.set(1);
    this.load();
  }

  onPage(e: PageEvent): void {
    this.page.set(e.pageIndex + 1);
    this.pageSize.set(e.pageSize);
    this.load();
  }

  exportCsv(): void {
    const rows = this.items();
    const header = ['id', 'activityDate', 'quantity', 'unitCode', 'status'];
    const lines = [
      header.join(','),
      ...rows.map((r) =>
        [r.id, r.activityDate ?? '', r.quantity, r.unitCode, r.status].join(','),
      ),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'activity-records.csv';
    a.click();
    URL.revokeObjectURL(url);
  }
}
