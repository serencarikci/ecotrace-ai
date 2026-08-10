import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '../../core/services/auth.service';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canConfigureCbam } from '../../core/services/roles.util';
import { CbamApiService, CbamInstallation } from './cbam-api.service';

@Component({
  selector: 'app-cbam-installation-detail',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './installation-detail.component.html',
  styleUrl: './cbam-pages.scss',
})
export class CbamInstallationDetailComponent implements OnInit {
  private readonly api = inject(CbamApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);

  readonly item = signal<CbamInstallation | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly canConfigure = canConfigureCbam(this.auth.currentRoles());

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(255)]],
    timezone: ['', Validators.required],
    operatorIdentityRef: [''],
  });

  private installationId = '';

  ngOnInit(): void {
    this.installationId = this.route.snapshot.paramMap.get('installationId') ?? '';
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.api.getInstallation(this.installationId).subscribe({
      next: (row) => {
        this.item.set(row);
        this.form.patchValue({
          name: row.name,
          timezone: row.timezone,
          operatorIdentityRef: row.operatorIdentityRef ?? '',
        });
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  save(): void {
    const current = this.item();
    if (!current || !this.canConfigure || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.api
      .updateInstallation(current.id, {
        rowVersion: current.rowVersion,
        name: value.name.trim(),
        timezone: value.timezone.trim(),
        operatorIdentityRef: value.operatorIdentityRef.trim() || null,
      })
      .subscribe({
        next: (row) => {
          this.item.set(row);
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  activate(): void {
    const current = this.item();
    if (!current || !this.canConfigure) {
      return;
    }
    this.api.activateInstallation(current.id, current.rowVersion).subscribe({
      next: (row) => this.item.set(row),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  archive(): void {
    const current = this.item();
    if (!current || !this.canConfigure) {
      return;
    }
    if (!confirm(`Archive “${current.name}”?`)) {
      return;
    }
    this.api.archiveInstallation(current.id, current.rowVersion).subscribe({
      next: (row) => this.item.set(row),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
