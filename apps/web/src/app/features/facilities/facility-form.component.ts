import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { FacilityService } from '../../core/services/facility.service';
import { FACILITY_TYPES } from '../../core/models/facility.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-facility-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCheckboxModule,
  ],
  templateUrl: './facility-form.component.html',
  styleUrl: './facility-form.component.scss',
})
export class FacilityFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(FacilityService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly facilityTypes = FACILITY_TYPES;
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly isEdit = signal(false);
  private facilityId: string | null = null;

  readonly form = this.fb.nonNullable.group({
    code: ['', [Validators.required, Validators.maxLength(64)]],
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(255)]],
    description: [''],
    facilityType: ['manufacturing', Validators.required],
    countryCode: ['TR', [Validators.required, Validators.pattern(/^[A-Za-z]{2}$/)]],
    city: [''],
    district: [''],
    addressLine: [''],
    postalCode: [''],
    latitude: [''],
    longitude: [''],
    timezone: ['Europe/Istanbul', Validators.required],
    operationalStartDate: [''],
    operationalEndDate: [''],
    isActive: [true],
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id && this.route.snapshot.routeConfig?.path?.includes('edit')) {
      this.isEdit.set(true);
      this.facilityId = id;
      this.form.controls.code.disable();
      this.loading.set(true);
      this.api.get(id).subscribe({
        next: (facility) => {
          this.form.patchValue({
            code: facility.code,
            name: facility.name,
            description: facility.description ?? '',
            facilityType: facility.facilityType,
            countryCode: facility.countryCode,
            city: facility.city ?? '',
            district: facility.district ?? '',
            addressLine: facility.addressLine ?? '',
            postalCode: facility.postalCode ?? '',
            latitude: facility.latitude != null ? String(facility.latitude) : '',
            longitude: facility.longitude != null ? String(facility.longitude) : '',
            timezone: facility.timezone,
            operationalStartDate: facility.operationalStartDate ?? '',
            operationalEndDate: facility.operationalEndDate ?? '',
            isActive: facility.isActive,
          });
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
    }
  }

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const payload = {
      code: value.code,
      name: value.name,
      description: value.description || null,
      facilityType: value.facilityType,
      countryCode: value.countryCode.toUpperCase(),
      city: value.city || null,
      district: value.district || null,
      addressLine: value.addressLine || null,
      postalCode: value.postalCode || null,
      latitude: value.latitude === '' ? null : Number(value.latitude),
      longitude: value.longitude === '' ? null : Number(value.longitude),
      timezone: value.timezone,
      operationalStartDate: value.operationalStartDate || null,
      operationalEndDate: value.operationalEndDate || null,
      isActive: value.isActive,
    };
    this.loading.set(true);
    const request$ =
      this.isEdit() && this.facilityId
        ? this.api.update(this.facilityId, payload)
        : this.api.create(payload);
    request$.subscribe({
      next: (facility) => {
        this.loading.set(false);
        void this.router.navigate(['/app/facilities', facility.id]);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }
}
