import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { OrganizationService } from '../../core/services/organization.service';
import { AuthService } from '../../core/services/auth.service';
import { Organization } from '../../core/models/api.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-organization-detail',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
  ],
  templateUrl: './organization-detail.component.html',
  styleUrl: './organization-detail.component.scss',
})
export class OrganizationDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(OrganizationService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly organization = signal<Organization | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly canEdit = signal(false);

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    legalName: [''],
    countryCode: ['', [Validators.required, Validators.pattern(/^[A-Za-z]{2}$/)]],
    timezone: ['', [Validators.required]],
    isActive: [true],
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.errorMessage.set('Organization not found.');
      return;
    }
    this.api.get(id).subscribe({
      next: (org) => {
        this.organization.set(org);
        this.form.patchValue({
          name: org.name,
          legalName: org.legalName ?? '',
          countryCode: org.countryCode,
          timezone: org.timezone,
          isActive: org.isActive,
        });
        this.canEdit.set(
          this.auth.hasAnyRole('system_admin', 'organization_admin'),
        );
        if (!this.canEdit()) {
          this.form.disable();
        }
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  save(): void {
    const org = this.organization();
    if (!org || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.api
      .update(org.id, {
        name: value.name,
        legalName: value.legalName || null,
        countryCode: value.countryCode.toUpperCase(),
        timezone: value.timezone,
        isActive: value.isActive,
      })
      .subscribe({
        next: (updated) => {
          this.organization.set(updated);
          this.successMessage.set('Organization updated.');
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }
}
