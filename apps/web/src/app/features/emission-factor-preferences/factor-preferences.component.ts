import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { CarbonService } from '../../core/services/carbon.service';
import { ReferenceService } from '../../core/services/reference.service';
import { AuthService } from '../../core/services/auth.service';
import { EmissionFactor, FactorPreference } from '../../core/models/carbon.models';
import { ActivityType } from '../../core/models/reference.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageFactorPreferences } from '../../core/services/roles.util';

@Component({
  selector: 'app-factor-preferences',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
  ],
  template: `
    <div class="page">
      <h1>Emission Factor Preferences</h1>
      <p class="hint">Organization-approved factor overrides used at matching priority 1.</p>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      <table mat-table [dataSource]="items()" class="full">
        <ng-container matColumnDef="activity"><th mat-header-cell *matHeaderCellDef>Activity type</th><td mat-cell *matCellDef="let r">{{ r.activityTypeId }}</td></ng-container>
        <ng-container matColumnDef="factor"><th mat-header-cell *matHeaderCellDef>Factor</th><td mat-cell *matCellDef="let r">{{ r.emissionFactorId }}</td></ng-container>
        <ng-container matColumnDef="priority"><th mat-header-cell *matHeaderCellDef>Priority</th><td mat-cell *matCellDef="let r">{{ r.priority }}</td></ng-container>
        <ng-container matColumnDef="reason"><th mat-header-cell *matHeaderCellDef>Reason</th><td mat-cell *matCellDef="let r">{{ r.reason || '—' }}</td></ng-container>
        <ng-container matColumnDef="actions"><th mat-header-cell *matHeaderCellDef></th>
          <td mat-cell *matCellDef="let r">
            @if (canManage) {
              <button mat-button color="warn" type="button" (click)="remove(r.id)">Deactivate</button>
            }
          </td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="cols"></tr>
        <tr mat-row *matRowDef="let row; columns: cols"></tr>
      </table>

      @if (canManage) {
        <h2>Add preference</h2>
        <form [formGroup]="form" (ngSubmit)="create()" class="form">
          <mat-form-field appearance="outline">
            <mat-label>Activity type</mat-label>
            <mat-select formControlName="activityTypeId">
              @for (t of activityTypes(); track t.id) {
                <mat-option [value]="t.id">{{ t.code }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Emission factor</mat-label>
            <mat-select formControlName="emissionFactorId">
              @for (f of factors(); track f.id) {
                <mat-option [value]="f.id">{{ f.code }} v{{ f.version }} ({{ f.geographyCode }})</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Priority</mat-label>
            <input matInput type="number" formControlName="priority" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Reason</mat-label>
            <input matInput formControlName="reason" />
          </mat-form-field>
          <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">Save</button>
        </form>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 1rem; }
      .full { width: 100%; margin-bottom: 1.5rem; }
      .form { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
      .hint { opacity: 0.75; }
      .error { color: #b00020; }
    `,
  ],
})
export class FactorPreferencesComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly reference = inject(ReferenceService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<FactorPreference[]>([]);
  readonly factors = signal<EmissionFactor[]>([]);
  readonly activityTypes = signal<ActivityType[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageFactorPreferences(this.auth.currentRoles());
  readonly cols = ['activity', 'factor', 'priority', 'reason', 'actions'];
  readonly form = this.fb.nonNullable.group({
    activityTypeId: ['', Validators.required],
    emissionFactorId: ['', Validators.required],
    priority: [1, Validators.required],
    reason: ['Organization preferred factor'],
  });

  ngOnInit(): void {
    this.reload();
    this.reference.listActivityTypes({ pageSize: 100 }).subscribe({
      next: (p) => this.activityTypes.set(p.items),
    });
    this.api.listFactors({ status: 'active', pageSize: 100 }).subscribe({
      next: (p) => this.factors.set(p.items),
    });
  }

  reload(): void {
    this.api.listPreferences().subscribe({
      next: (rows) => this.items.set(rows),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  create(): void {
    this.api.createPreference(this.form.getRawValue()).subscribe({
      next: () => {
        this.form.patchValue({ reason: 'Organization preferred factor' });
        this.reload();
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  remove(id: string): void {
    this.api.deletePreference(id).subscribe({
      next: () => this.reload(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
