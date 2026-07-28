import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { DataSourceService } from '../../core/services/data-source.service';
import { FacilityService } from '../../core/services/facility.service';
import { EquipmentService } from '../../core/services/equipment.service';
import { DATA_SOURCE_TYPES, LIVE_INTEGRATION_SOURCE_TYPES } from '../../core/models/data-source.models';
import { Facility } from '../../core/models/facility.models';
import { Equipment } from '../../core/models/equipment.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-data-source-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule, MatCheckboxModule],
  templateUrl: './data-source-form.component.html',
})
export class DataSourceFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(DataSourceService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly equipmentApi = inject(EquipmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly facilities = signal<Facility[]>([]);
  readonly equipment = signal<Equipment[]>([]);
  readonly sourceTypes = DATA_SOURCE_TYPES;
  readonly liveTypes = LIVE_INTEGRATION_SOURCE_TYPES;
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly isEdit = signal(false);
  private dataSourceId: string | null = null;

  readonly form = this.fb.nonNullable.group({
    facilityId: [''],
    equipmentId: [''],
    code: ['', Validators.required],
    name: ['', [Validators.required, Validators.minLength(2)]],
    sourceType: ['manual_entry', Validators.required],
    description: [''],
    externalReference: [''],
    isActive: [true],
  });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100 }).subscribe({ next: (p) => this.facilities.set(p.items) });
    this.equipmentApi.list({ page: 1, pageSize: 100 }).subscribe({ next: (p) => this.equipment.set(p.items) });
    const id = this.route.snapshot.paramMap.get('id');
    if (id && this.route.snapshot.routeConfig?.path?.includes('edit')) {
      this.isEdit.set(true); this.dataSourceId = id; this.form.controls.code.disable();
      this.api.get(id).subscribe({
        next: (item) => this.form.patchValue({
          facilityId: item.facilityId ?? '', equipmentId: item.equipmentId ?? '', code: item.code, name: item.name,
          sourceType: item.sourceType, description: item.description ?? '', externalReference: item.externalReference ?? '', isActive: item.isActive,
        }),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  isLiveType(): boolean { return this.liveTypes.includes(this.form.controls.sourceType.value as never); }

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const v = this.form.getRawValue();
    const payload = {
      facilityId: v.facilityId || null, equipmentId: v.equipmentId || null, code: v.code, name: v.name,
      sourceType: v.sourceType, description: v.description || null, externalReference: v.externalReference || null, isActive: v.isActive,
    };
    this.loading.set(true);
    const req$ = this.isEdit() && this.dataSourceId ? this.api.update(this.dataSourceId, payload) : this.api.create(payload);
    req$.subscribe({
      next: (item) => { this.loading.set(false); void this.router.navigate(['/app/data-sources', item.id]); },
      error: (err: unknown) => { this.loading.set(false); this.errorMessage.set(extractApiErrorMessage(err)); },
    });
  }
}
