import { Component, EventEmitter, inject, Output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { OrganizationService } from '../../core/services/organization.service';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-organization-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
  ],
  template: `
    <h2>Create organization</h2>
    <form [formGroup]="form" (ngSubmit)="submit()" class="form-grid">
      <mat-form-field appearance="outline">
        <mat-label>Name</mat-label>
        <input matInput formControlName="name" />
        @if (form.controls.name.touched && form.controls.name.invalid) {
          <mat-error>Name is required.</mat-error>
        }
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Legal name</mat-label>
        <input matInput formControlName="legalName" />
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Slug</mat-label>
        <input matInput formControlName="slug" />
        @if (form.controls.slug.touched && form.controls.slug.invalid) {
          <mat-error>Use lowercase letters, numbers, and hyphens.</mat-error>
        }
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Country code</mat-label>
        <input matInput formControlName="countryCode" maxlength="2" />
        @if (form.controls.countryCode.touched && form.controls.countryCode.invalid) {
          <mat-error>Use a 2-letter country code.</mat-error>
        }
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Timezone</mat-label>
        <input matInput formControlName="timezone" />
      </mat-form-field>
      <mat-checkbox formControlName="isActive">Active</mat-checkbox>
      @if (errorMessage()) {
        <p class="error-text" role="alert">{{ errorMessage() }}</p>
      }
      <button mat-flat-button color="primary" type="submit" [disabled]="loading()">Create</button>
    </form>
  `,
  styles: `
    h2 {
      margin-top: 0;
      font-size: 1.1rem;
    }
    .form-grid {
      display: grid;
      gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      align-items: center;
    }
  `,
})
export class OrganizationFormComponent {
  @Output() readonly created = new EventEmitter<void>();

  private readonly fb = inject(FormBuilder);
  private readonly api = inject(OrganizationService);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    legalName: [''],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]],
    countryCode: ['DE', [Validators.required, Validators.pattern(/^[A-Za-z]{2}$/)]],
    timezone: ['Europe/Berlin', [Validators.required]],
    isActive: [true],
  });

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    const value = this.form.getRawValue();
    this.api
      .create({
        name: value.name,
        legalName: value.legalName || null,
        slug: value.slug,
        countryCode: value.countryCode.toUpperCase(),
        timezone: value.timezone,
        isActive: value.isActive,
      })
      .subscribe({
        next: () => {
          this.loading.set(false);
          this.created.emit();
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }
}
