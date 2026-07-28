import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ProductionLineService } from '../../core/services/production-line.service';
import { FacilityService } from '../../core/services/facility.service';
import { ReferenceService } from '../../core/services/reference.service';
import { Facility } from '../../core/models/facility.models';
import { Unit } from '../../core/models/reference.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-production-line-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule, MatCheckboxModule],
  templateUrl: './production-line-form.component.html',
})
export class ProductionLineFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ProductionLineService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly referenceApi = inject(ReferenceService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly facilities = signal<Facility[]>([]);
  readonly units = signal<Unit[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly isEdit = signal(false);
  private lineId: string | null = null;

  readonly form = this.fb.nonNullable.group({
    facilityId: ['', Validators.required],
    code: ['', [Validators.required, Validators.maxLength(64)]],
    name: ['', [Validators.required, Validators.minLength(2)]],
    description: [''],
    productionCategory: [''],
    capacityValue: [''],
    capacityUnitCode: [''],
    isActive: [true],
  });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100, isActive: true }).subscribe({
      next: (p) => this.facilities.set(p.items),
    });
    this.referenceApi.listUnits({ activeOnly: true, pageSize: 200 }).subscribe({
      next: (p) => this.units.set(p.items),
    });
    const id = this.route.snapshot.paramMap.get('id');
    if (id && this.route.snapshot.routeConfig?.path?.includes('edit')) {
      this.isEdit.set(true);
      this.lineId = id;
      this.form.controls.code.disable();
      this.form.controls.facilityId.disable();
      this.api.get(id).subscribe({
        next: (line) => {
          this.form.patchValue({
            facilityId: line.facilityId,
            code: line.code,
            name: line.name,
            description: line.description ?? '',
            productionCategory: line.productionCategory ?? '',
            capacityValue: line.capacityValue != null ? String(line.capacityValue) : '',
            capacityUnitCode: line.capacityUnitCode ?? '',
            isActive: line.isActive,
          });
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const v = this.form.getRawValue();
    const payload = {
      code: v.code,
      name: v.name,
      description: v.description || null,
      productionCategory: v.productionCategory || null,
      capacityValue: v.capacityValue === '' ? null : Number(v.capacityValue),
      capacityUnitCode: v.capacityUnitCode || null,
      isActive: v.isActive,
    };
    this.loading.set(true);
    const req$ = this.isEdit() && this.lineId
      ? this.api.update(this.lineId, payload)
      : this.api.create(v.facilityId, payload);
    req$.subscribe({
      next: (line) => { this.loading.set(false); void this.router.navigate(['/app/production-lines', line.id]); },
      error: (err: unknown) => { this.loading.set(false); this.errorMessage.set(extractApiErrorMessage(err)); },
    });
  }
}
