import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { Facility } from '../../core/models/facility.models';
import { FacilityService } from '../../core/services/facility.service';
import { AuthService } from '../../core/services/auth.service';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canConfigureCbam } from '../../core/services/roles.util';
import { CbamApiService } from './cbam-api.service';

@Component({
  selector: 'app-cbam-installation-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
  templateUrl: './installation-form.component.html',
  styleUrl: './cbam-pages.scss',
})
export class CbamInstallationFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(CbamApiService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly facilities = signal<Facility[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly canConfigure = canConfigureCbam(this.auth.currentRoles());

  readonly form = this.fb.nonNullable.group({
    facilityId: ['', Validators.required],
    code: ['', [Validators.required, Validators.maxLength(64)]],
    name: ['', [Validators.required, Validators.maxLength(255)]],
    timezone: ['Europe/Istanbul', Validators.required],
    operatorIdentityRef: [''],
  });

  ngOnInit(): void {
    if (!this.canConfigure) {
      this.errorMessage.set('You do not have permission to do this.');
      return;
    }
    this.facilitiesApi.list({ page: 1, pageSize: 100, isActive: true }).subscribe({
      next: (page) => this.facilities.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  submit(): void {
    this.errorMessage.set(null);
    if (!this.canConfigure) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.loading.set(true);
    this.api
      .createInstallation({
        facilityId: value.facilityId,
        code: value.code.trim(),
        name: value.name.trim(),
        timezone: value.timezone.trim(),
        operatorIdentityRef: value.operatorIdentityRef.trim() || null,
      })
      .subscribe({
        next: (created) => {
          this.loading.set(false);
          void this.router.navigate(['/app/cbam/installations', created.id]);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }
}
