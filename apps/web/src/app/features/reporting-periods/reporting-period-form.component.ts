import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ReportingPeriodService } from '../../core/services/reporting-period.service';
import { PERIOD_TYPES } from '../../core/models/reporting-period.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-reporting-period-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule],
  templateUrl: './reporting-period-form.component.html',
})
export class ReportingPeriodFormComponent {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ReportingPeriodService);
  private readonly router = inject(Router);
  readonly types = PERIOD_TYPES;
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly form = this.fb.nonNullable.group({
    code: ['', Validators.required],
    name: ['', [Validators.required, Validators.minLength(2)]],
    periodType: ['monthly', Validators.required],
    startDate: ['', Validators.required],
    endDate: ['', Validators.required],
  });

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.api.create(this.form.getRawValue()).subscribe({
      next: (period) => { this.loading.set(false); void this.router.navigate(['/app/reporting-periods', period.id]); },
      error: (err: unknown) => { this.loading.set(false); this.errorMessage.set(extractApiErrorMessage(err)); },
    });
  }
}
