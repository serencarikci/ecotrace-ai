import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { CarbonService } from '../../core/services/carbon.service';
import { EmissionFactorSource } from '../../core/models/carbon.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { AuthService } from '../../core/services/auth.service';
import { canManageReferenceData } from '../../core/services/roles.util';

@Component({
  selector: 'app-factor-source-detail',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  template: `
    <div class="page">
      <a routerLink="/app/emission-factor-sources">← Sources</a>
      <h1>{{ isNew ? 'New factor source' : (source()?.name || 'Factor source') }}</h1>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      @if (isNew && canManage) {
        <form [formGroup]="form" (ngSubmit)="create()">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Code</mat-label>
            <input matInput formControlName="code" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Name</mat-label>
            <input matInput formControlName="name" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Publisher</mat-label>
            <input matInput formControlName="publisher" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Description</mat-label>
            <textarea matInput rows="3" formControlName="description"></textarea>
          </mat-form-field>
          <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">Create</button>
        </form>
      } @else if (source()) {
        <dl>
          <dt>Code</dt><dd>{{ source()!.code }}</dd>
          <dt>Publisher</dt><dd>{{ source()!.publisher || '—' }}</dd>
          <dt>Demo</dt><dd>{{ source()!.isDemo ? 'Yes — not for regulatory use' : 'No' }}</dd>
          <dt>Active</dt><dd>{{ source()!.isActive }}</dd>
          <dt>Description</dt><dd>{{ source()!.description || '—' }}</dd>
        </dl>
        @if (canManage && source()!.isActive) {
          <button mat-stroked-button color="warn" type="button" (click)="archive()">Archive</button>
        }
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 1rem; max-width: 720px; }
      .full { width: 100%; display: block; margin-bottom: 0.5rem; }
      .error { color: #b00020; }
      dl { display: grid; grid-template-columns: 160px 1fr; gap: 0.5rem 1rem; }
      dt { font-weight: 600; }
    `,
  ],
})
export class FactorSourceDetailComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);

  readonly source = signal<EmissionFactorSource | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageReferenceData(this.auth.currentRoles());
  isNew = false;

  readonly form = this.fb.nonNullable.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    publisher: [''],
    description: ['Demo/reference source — not authoritative.'],
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    this.isNew = id === 'new' || this.router.url.endsWith('/new');
    if (!this.isNew && id) {
      this.api.getSource(id).subscribe({
        next: (s) => this.source.set(s),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  create(): void {
    this.api.createSource({ ...this.form.getRawValue(), isDemo: true }).subscribe({
      next: (s) => void this.router.navigate(['/app/emission-factor-sources', s.id]),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  archive(): void {
    const s = this.source();
    if (!s) return;
    this.api.archiveSource(s.id).subscribe({
      next: (updated) => this.source.set(updated),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
