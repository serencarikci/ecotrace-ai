import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CarbonService } from '../../core/services/carbon.service';
import { AuthService } from '../../core/services/auth.service';
import { EmissionFactor } from '../../core/models/carbon.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageReferenceData } from '../../core/services/roles.util';

@Component({
  selector: 'app-emission-factor-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="header">
        <h1>Emission Factors</h1>
        @if (canManage) {
          <a mat-flat-button color="primary" routerLink="/app/emission-factors/new">New draft factor</a>
        }
      </div>
      <p class="hint">Seeded factors are demo/reference data and must not be used for regulatory reporting.</p>
      <form class="filters" [formGroup]="filters" (ngSubmit)="apply()">
        <mat-form-field appearance="outline">
          <mat-label>Search</mat-label>
          <input matInput formControlName="search" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Scope</mat-label>
          <mat-select formControlName="scope">
            <mat-option value="">All</mat-option>
            <mat-option value="scope_1">Scope 1</mat-option>
            <mat-option value="scope_2">Scope 2</mat-option>
            <mat-option value="scope_3">Scope 3</mat-option>
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Status</mat-label>
          <mat-select formControlName="status">
            <mat-option value="">All</mat-option>
            <mat-option value="draft">Draft</mat-option>
            <mat-option value="active">Active</mat-option>
            <mat-option value="superseded">Superseded</mat-option>
            <mat-option value="archived">Archived</mat-option>
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Geography</mat-label>
          <input matInput formControlName="geographyCode" />
        </mat-form-field>
        <button mat-stroked-button type="submit">Filter</button>
      </form>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      @if (loading()) {
        <mat-spinner diameter="36"></mat-spinner>
      } @else {
        <table mat-table [dataSource]="items()" class="full">
          <ng-container matColumnDef="code"><th mat-header-cell *matHeaderCellDef>Code</th><td mat-cell *matCellDef="let r">{{ r.code }} v{{ r.version }}</td></ng-container>
          <ng-container matColumnDef="name"><th mat-header-cell *matHeaderCellDef>Name</th><td mat-cell *matCellDef="let r">{{ r.name }}</td></ng-container>
          <ng-container matColumnDef="scope"><th mat-header-cell *matHeaderCellDef>Scope</th><td mat-cell *matCellDef="let r">{{ r.scope }}</td></ng-container>
          <ng-container matColumnDef="geo"><th mat-header-cell *matHeaderCellDef>Geo</th><td mat-cell *matCellDef="let r">{{ r.geographyCode }}</td></ng-container>
          <ng-container matColumnDef="status"><th mat-header-cell *matHeaderCellDef>Status</th><td mat-cell *matCellDef="let r">{{ r.status }}</td></ng-container>
          <ng-container matColumnDef="demo"><th mat-header-cell *matHeaderCellDef>Demo</th><td mat-cell *matCellDef="let r">{{ r.isDemo ? 'Yes' : 'No' }}</td></ng-container>
          <ng-container matColumnDef="actions"><th mat-header-cell *matHeaderCellDef></th><td mat-cell *matCellDef="let r"><a mat-button [routerLink]="['/app/emission-factors', r.id]">Open</a></td></ng-container>
          <tr mat-header-row *matHeaderRowDef="cols"></tr>
          <tr mat-row *matRowDef="let row; columns: cols"></tr>
        </table>
        <mat-paginator [length]="totalItems()" [pageSize]="pageSize()" [pageIndex]="page()-1" (page)="onPage($event)"></mat-paginator>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 1rem; }
      .header { display: flex; justify-content: space-between; align-items: center; }
      .filters { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; margin-bottom: 1rem; }
      .full { width: 100%; }
      .hint { opacity: 0.75; }
      .error { color: #b00020; }
    `,
  ],
})
export class EmissionFactorListComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  readonly items = signal<EmissionFactor[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canManage = canManageReferenceData(this.auth.currentRoles());
  readonly cols = ['code', 'name', 'scope', 'geo', 'status', 'demo', 'actions'];
  readonly filters = this.fb.nonNullable.group({
    search: [''],
    scope: [''],
    status: [''],
    geographyCode: [''],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    const f = this.filters.getRawValue();
    this.api
      .listFactors({
        page: this.page(),
        pageSize: this.pageSize(),
        search: f.search || undefined,
        scope: f.scope || undefined,
        status: f.status || undefined,
        geographyCode: f.geographyCode || undefined,
        includeDrafts: this.canManage,
      })
      .subscribe({
        next: (page) => {
          this.items.set(page.items);
          this.totalItems.set(page.totalItems);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }

  apply(): void {
    this.page.set(1);
    this.load();
  }

  onPage(event: PageEvent): void {
    this.page.set(event.pageIndex + 1);
    this.pageSize.set(event.pageSize);
    this.load();
  }
}
