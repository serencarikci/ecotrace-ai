import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ActivityRecordService } from '../../core/services/activity-record.service';
import { FacilityService } from '../../core/services/facility.service';
import { ProductionLineService } from '../../core/services/production-line.service';
import { EquipmentService } from '../../core/services/equipment.service';
import { DataSourceService } from '../../core/services/data-source.service';
import { ReferenceService } from '../../core/services/reference.service';
import { ReportingPeriodService } from '../../core/services/reporting-period.service';
import { Facility } from '../../core/models/facility.models';
import { ProductionLine } from '../../core/models/production-line.models';
import { Equipment } from '../../core/models/equipment.models';
import { DataSource } from '../../core/models/data-source.models';
import { ActivityType, Unit } from '../../core/models/reference.models';
import { ReportingPeriod } from '../../core/models/reporting-period.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-activity-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
  templateUrl: './activity-form.component.html',
})
export class ActivityFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ActivityRecordService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly linesApi = inject(ProductionLineService);
  private readonly equipmentApi = inject(EquipmentService);
  private readonly dataSourcesApi = inject(DataSourceService);
  private readonly referenceApi = inject(ReferenceService);
  private readonly periodsApi = inject(ReportingPeriodService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly facilities = signal<Facility[]>([]);
  readonly lines = signal<ProductionLine[]>([]);
  readonly equipment = signal<Equipment[]>([]);
  readonly dataSources = signal<DataSource[]>([]);
  readonly activityTypes = signal<ActivityType[]>([]);
  readonly periods = signal<ReportingPeriod[]>([]);
  readonly units = signal<Unit[]>([]);
  readonly allUnits = signal<Unit[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly isEdit = signal(false);
  private recordId: string | null = null;
  private rowVersion = 1;

  readonly form = this.fb.nonNullable.group({
    facilityId: [''],
    productionLineId: [''],
    equipmentId: [''],
    dataSourceId: [''],
    activityTypeId: ['', Validators.required],
    reportingPeriodId: ['', Validators.required],
    activityDate: [''],
    periodStart: [''],
    periodEnd: [''],
    quantity: ['', [Validators.required, Validators.min(0)]],
    unitCode: ['', Validators.required],
    sourceReference: [''],
    description: [''],
    notes: [''],
  });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100, isActive: true }).subscribe({
      next: (p) => this.facilities.set(p.items),
    });
    this.dataSourcesApi.list({ page: 1, pageSize: 100, isActive: true }).subscribe({
      next: (p) => this.dataSources.set(p.items),
    });
    this.referenceApi.listActivityTypes({ activeOnly: true }).subscribe({
      next: (p) => this.activityTypes.set(p.items),
    });
    this.periodsApi.list({ page: 1, pageSize: 100 }).subscribe({
      next: (p) => this.periods.set(p.items.filter((x) => x.status !== 'locked' && x.status !== 'archived')),
    });
    this.referenceApi.listUnits({ activeOnly: true, pageSize: 200 }).subscribe({
      next: (p) => {
        this.allUnits.set(p.items);
        this.units.set(p.items);
      },
    });

    this.form.controls.facilityId.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((facilityId) => {
        this.loadLines(facilityId);
        this.loadEquipment(facilityId);
      });

    this.form.controls.activityTypeId.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((typeId) => this.filterUnits(typeId));

    const id = this.route.snapshot.paramMap.get('id');
    if (id && this.route.snapshot.routeConfig?.path?.includes('edit')) {
      this.isEdit.set(true);
      this.recordId = id;
      this.api.get(id).subscribe({
        next: (record) => {
          this.rowVersion = record.rowVersion;
          this.form.patchValue({
            facilityId: record.facilityId ?? '',
            productionLineId: record.productionLineId ?? '',
            equipmentId: record.equipmentId ?? '',
            dataSourceId: record.dataSourceId ?? '',
            activityTypeId: record.activityTypeId,
            reportingPeriodId: record.reportingPeriodId,
            activityDate: record.activityDate ?? '',
            periodStart: record.periodStart ?? '',
            periodEnd: record.periodEnd ?? '',
            quantity: String(record.quantity),
            unitCode: record.unitCode,
            sourceReference: record.sourceReference ?? '',
            description: record.description ?? '',
            notes: record.notes ?? '',
          });
          this.loadLines(record.facilityId ?? '');
          this.loadEquipment(record.facilityId ?? '');
          this.filterUnits(record.activityTypeId);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  loadLines(facilityId: string): void {
    if (!facilityId) {
      this.lines.set([]);
      return;
    }
    this.linesApi.listByFacility(facilityId).subscribe({
      next: (p) => this.lines.set(p.items),
    });
  }

  loadEquipment(facilityId: string): void {
    if (!facilityId) {
      this.equipment.set([]);
      return;
    }
    this.equipmentApi.list({ facilityId, pageSize: 100 }).subscribe({
      next: (p) => this.equipment.set(p.items),
    });
  }

  filterUnits(activityTypeId: string): void {
    const type = this.activityTypes().find((t) => t.id === activityTypeId);
    if (!type) {
      this.units.set(this.allUnits());
      return;
    }
    const filtered = this.allUnits().filter((u) => u.dimension === type.allowedUnitDimension);
    this.units.set(filtered);
    if (!filtered.some((u) => u.code === this.form.controls.unitCode.value)) {
      this.form.controls.unitCode.setValue(type.defaultUnitCode);
    }
  }

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const payload = {
      facilityId: v.facilityId || null,
      productionLineId: v.productionLineId || null,
      equipmentId: v.equipmentId || null,
      dataSourceId: v.dataSourceId || null,
      activityTypeId: v.activityTypeId,
      reportingPeriodId: v.reportingPeriodId,
      activityDate: v.activityDate || null,
      periodStart: v.periodStart || null,
      periodEnd: v.periodEnd || null,
      quantity: v.quantity,
      unitCode: v.unitCode,
      sourceReference: v.sourceReference || null,
      description: v.description || null,
      notes: v.notes || null,
    };
    this.loading.set(true);
    const req$ =
      this.isEdit() && this.recordId
        ? this.api.update(this.recordId, { ...payload, rowVersion: this.rowVersion })
        : this.api.create(payload);
    req$.subscribe({
      next: (record) => {
        this.loading.set(false);
        void this.router.navigate(['/app/activity-data', record.id]);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }
}
