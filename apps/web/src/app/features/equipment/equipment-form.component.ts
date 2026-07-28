import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { EquipmentService } from '../../core/services/equipment.service';
import { FacilityService } from '../../core/services/facility.service';
import { ProductionLineService } from '../../core/services/production-line.service';
import { EQUIPMENT_TYPES } from '../../core/models/equipment.models';
import { Facility } from '../../core/models/facility.models';
import { ProductionLine } from '../../core/models/production-line.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-equipment-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule, MatCheckboxModule],
  templateUrl: './equipment-form.component.html',
})
export class EquipmentFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(EquipmentService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly linesApi = inject(ProductionLineService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly facilities = signal<Facility[]>([]);
  readonly lines = signal<ProductionLine[]>([]);
  readonly equipmentTypes = EQUIPMENT_TYPES;
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly isEdit = signal(false);
  private equipmentId: string | null = null;

  readonly form = this.fb.nonNullable.group({
    facilityId: ['', Validators.required],
    productionLineId: [''],
    code: ['', Validators.required],
    name: ['', [Validators.required, Validators.minLength(2)]],
    description: [''],
    equipmentType: ['electricity_meter', Validators.required],
    manufacturer: [''],
    model: [''],
    serialNumber: [''],
    commissioningDate: [''],
    decommissioningDate: [''],
    isActive: [true],
  });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100, isActive: true }).subscribe({ next: (p) => this.facilities.set(p.items) });
    this.form.controls.facilityId.valueChanges.subscribe((facilityId) => this.loadLines(facilityId));
    const id = this.route.snapshot.paramMap.get('id');
    if (id && this.route.snapshot.routeConfig?.path?.includes('edit')) {
      this.isEdit.set(true);
      this.equipmentId = id;
      this.form.controls.code.disable();
      this.api.get(id).subscribe({
        next: (item) => {
          this.form.patchValue({
            facilityId: item.facilityId,
            productionLineId: item.productionLineId ?? '',
            code: item.code,
            name: item.name,
            description: item.description ?? '',
            equipmentType: item.equipmentType,
            manufacturer: item.manufacturer ?? '',
            model: item.model ?? '',
            serialNumber: item.serialNumber ?? '',
            commissioningDate: item.commissioningDate ?? '',
            decommissioningDate: item.decommissioningDate ?? '',
            isActive: item.isActive,
          });
          this.loadLines(item.facilityId);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  loadLines(facilityId: string): void {
    if (!facilityId) { this.lines.set([]); return; }
    this.linesApi.listByFacility(facilityId).subscribe({ next: (p) => this.lines.set(p.items) });
  }

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const v = this.form.getRawValue();
    const payload = {
      facilityId: v.facilityId,
      productionLineId: v.productionLineId || null,
      code: v.code,
      name: v.name,
      description: v.description || null,
      equipmentType: v.equipmentType,
      manufacturer: v.manufacturer || null,
      model: v.model || null,
      serialNumber: v.serialNumber || null,
      commissioningDate: v.commissioningDate || null,
      decommissioningDate: v.decommissioningDate || null,
      isActive: v.isActive,
    };
    this.loading.set(true);
    const req$ = this.isEdit() && this.equipmentId ? this.api.update(this.equipmentId, payload) : this.api.create(payload);
    req$.subscribe({
      next: (item) => { this.loading.set(false); void this.router.navigate(['/app/equipment', item.id]); },
      error: (err: unknown) => { this.loading.set(false); this.errorMessage.set(extractApiErrorMessage(err)); },
    });
  }
}
