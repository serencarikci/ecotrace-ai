import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { CarbonService } from '../../core/services/carbon.service';
import { ReferenceService } from '../../core/services/reference.service';
import { AuthService } from '../../core/services/auth.service';
import { EmissionFactor, EmissionFactorSource } from '../../core/models/carbon.models';
import { ActivityType } from '../../core/models/reference.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageReferenceData } from '../../core/services/roles.util';

@Component({
  selector: 'app-emission-factor-detail',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
  ],
  template: `
    <div class="page">
      <a routerLink="/app/emission-factors">← Factors</a>
      <h1>{{ mode === 'new' ? 'New draft factor' : (factor()?.name || 'Factor') }}</h1>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }

      @if (mode === 'new' || mode === 'edit') {
        <form [formGroup]="form" (ngSubmit)="save()">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Source</mat-label>
            <mat-select formControlName="sourceId">
              @for (s of sources(); track s.id) {
                <mat-option [value]="s.id">{{ s.code }} — {{ s.name }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Code</mat-label>
            <input matInput formControlName="code" [readonly]="mode==='edit'" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Name</mat-label>
            <input matInput formControlName="name" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Activity type</mat-label>
            <mat-select formControlName="activityTypeId">
              @for (t of activityTypes(); track t.id) {
                <mat-option [value]="t.id">{{ t.code }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Scope</mat-label>
            <mat-select formControlName="scope">
              <mat-option value="scope_1">scope_1</mat-option>
              <mat-option value="scope_2">scope_2</mat-option>
              <mat-option value="scope_3">scope_3</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Category</mat-label>
            <input matInput formControlName="category" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Geography</mat-label>
            <input matInput formControlName="geographyCode" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Unit code</mat-label>
            <input matInput formControlName="unitCode" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Factor value (kgCO2e / unit)</mat-label>
            <input matInput formControlName="factorValue" />
          </mat-form-field>
          <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid || !canManage">Save draft</button>
        </form>
      } @else if (factor()) {
        @if (factor()!.isDemo) {
          <p class="demo">DEMO / REFERENCE — not for regulatory reporting.</p>
        }
        <dl>
          <dt>Code / version</dt><dd>{{ factor()!.code }} / v{{ factor()!.version }}</dd>
          <dt>Status</dt><dd>{{ factor()!.status }}</dd>
          <dt>Scope / category</dt><dd>{{ factor()!.scope }} / {{ factor()!.category }}</dd>
          <dt>Geography</dt><dd>{{ factor()!.geographyCode }}</dd>
          <dt>Unit</dt><dd>{{ factor()!.unitCode }}</dd>
          <dt>Factor value</dt><dd>{{ factor()!.factorValue }}</dd>
          <dt>CO2 / CH4 / N2O</dt><dd>{{ factor()!.co2Factor }} / {{ factor()!.ch4Factor }} / {{ factor()!.n2oFactor }}</dd>
          <dt>Usage count</dt><dd>{{ factor()!.usageCount }}</dd>
        </dl>
        <div class="actions">
          @if (canManage && factor()!.status === 'draft') {
            <a mat-stroked-button [routerLink]="['/app/emission-factors', factor()!.id, 'edit']">Edit draft</a>
            <button mat-flat-button color="primary" type="button" (click)="activate()">Activate</button>
          }
          @if (canManage && factor()!.status === 'active') {
            <button mat-stroked-button type="button" (click)="clone()">Clone as new version</button>
            <button mat-stroked-button color="warn" type="button" (click)="supersede()">Supersede</button>
          }
        </div>
        <h2>Version history</h2>
        <table mat-table [dataSource]="versions()" class="full">
          <ng-container matColumnDef="version"><th mat-header-cell *matHeaderCellDef>Version</th><td mat-cell *matCellDef="let r">v{{ r.version }}</td></ng-container>
          <ng-container matColumnDef="status"><th mat-header-cell *matHeaderCellDef>Status</th><td mat-cell *matCellDef="let r">{{ r.status }}</td></ng-container>
          <ng-container matColumnDef="value"><th mat-header-cell *matHeaderCellDef>Value</th><td mat-cell *matCellDef="let r">{{ r.factorValue }}</td></ng-container>
          <ng-container matColumnDef="open"><th mat-header-cell *matHeaderCellDef></th><td mat-cell *matCellDef="let r"><a mat-button [routerLink]="['/app/emission-factors', r.id]">Open</a></td></ng-container>
          <tr mat-header-row *matHeaderRowDef="['version','status','value','open']"></tr>
          <tr mat-row *matRowDef="let row; columns: ['version','status','value','open']"></tr>
        </table>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 1rem; max-width: 880px; }
      .full { width: 100%; display: block; margin-bottom: 0.5rem; }
      .error { color: #b00020; }
      .demo { background: #fff3cd; padding: 0.75rem; border-radius: 4px; }
      dl { display: grid; grid-template-columns: 180px 1fr; gap: 0.4rem 1rem; }
      .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }
    `,
  ],
})
export class EmissionFactorDetailComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly reference = inject(ReferenceService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);

  readonly factor = signal<EmissionFactor | null>(null);
  readonly versions = signal<EmissionFactor[]>([]);
  readonly sources = signal<EmissionFactorSource[]>([]);
  readonly activityTypes = signal<ActivityType[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageReferenceData(this.auth.currentRoles());
  mode: 'view' | 'new' | 'edit' = 'view';

  readonly form = this.fb.nonNullable.group({
    sourceId: ['', Validators.required],
    code: ['', Validators.required],
    name: ['', Validators.required],
    activityTypeId: ['', Validators.required],
    scope: ['scope_2', Validators.required],
    category: ['purchased_electricity', Validators.required],
    geographyCode: ['GLOBAL', Validators.required],
    unitCode: ['kWh', Validators.required],
    factorValue: ['0', Validators.required],
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    const url = this.router.url;
    if (url.endsWith('/new')) {
      this.mode = 'new';
      this.loadLookups();
      return;
    }
    if (url.endsWith('/edit') && id) {
      this.mode = 'edit';
      this.loadLookups();
      this.api.getFactor(id).subscribe({
        next: (f) => {
          if (f.status !== 'draft') {
            this.errorMessage.set('Only draft factors can be edited.');
            this.mode = 'view';
            this.factor.set(f);
            return;
          }
          this.factor.set(f);
          this.form.patchValue({
            sourceId: f.sourceId,
            code: f.code,
            name: f.name,
            activityTypeId: f.activityTypeId,
            scope: f.scope,
            category: f.category,
            geographyCode: f.geographyCode,
            unitCode: f.unitCode,
            factorValue: f.factorValue ?? '0',
          });
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
      return;
    }
    if (id) {
      this.mode = 'view';
      this.api.getFactor(id).subscribe({
        next: (f) => {
          this.factor.set(f);
          this.api.listFactorVersions(id).subscribe({ next: (v) => this.versions.set(v) });
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  private loadLookups(): void {
    this.api.listSources({ pageSize: 100 }).subscribe({ next: (p) => this.sources.set(p.items) });
    this.reference.listActivityTypes({ pageSize: 100 }).subscribe({
      next: (p) => this.activityTypes.set(p.items),
    });
  }

  save(): void {
    const raw = this.form.getRawValue();
    const payload = {
      ...raw,
      factorValue: raw.factorValue,
      version: 1,
      isDemo: true,
    };
    if (this.mode === 'new') {
      this.api.createFactor(payload).subscribe({
        next: (f) => void this.router.navigate(['/app/emission-factors', f.id]),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    } else if (this.factor()) {
      this.api.updateFactor(this.factor()!.id, {
        name: raw.name,
        scope: raw.scope,
        category: raw.category,
        geographyCode: raw.geographyCode,
        unitCode: raw.unitCode,
        factorValue: raw.factorValue,
      }).subscribe({
        next: (f) => void this.router.navigate(['/app/emission-factors', f.id]),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  activate(): void {
    const f = this.factor();
    if (!f) return;
    this.api.activateFactor(f.id).subscribe({
      next: (updated) => {
        this.factor.set(updated);
        this.api.listFactorVersions(updated.id).subscribe({ next: (v) => this.versions.set(v) });
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  clone(): void {
    const f = this.factor();
    if (!f) return;
    this.api.cloneFactor(f.id).subscribe({
      next: (created) => void this.router.navigate(['/app/emission-factors', created.id]),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  supersede(): void {
    const f = this.factor();
    if (!f) return;
    this.api.supersedeFactor(f.id).subscribe({
      next: (updated) => this.factor.set(updated),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
