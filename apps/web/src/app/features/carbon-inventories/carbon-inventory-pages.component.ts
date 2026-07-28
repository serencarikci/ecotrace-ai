import { JsonPipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { CarbonService } from '../../core/services/carbon.service';
import { ReportingPeriodService } from '../../core/services/reporting-period.service';
import { AuthService } from '../../core/services/auth.service';
import {
  CalculationItem,
  CalculationRun,
  CarbonInventory,
  InventorySummary,
  ValidationResult,
} from '../../core/models/carbon.models';
import { ReportingPeriod } from '../../core/models/reporting-period.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import {
  canApproveInventory,
  canCalculateInventory,
  canCreateInventory,
} from '../../core/services/roles.util';

@Component({
  selector: 'app-carbon-inventory-list',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatTableModule],
  template: `
    <div class="page">
      <div class="header">
        <h1>Carbon Inventories</h1>
        @if (canCreate) {
          <a mat-flat-button color="primary" routerLink="/app/carbon-inventories/new">New inventory</a>
        }
      </div>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      <table mat-table [dataSource]="items()" class="full">
        <ng-container matColumnDef="name"><th mat-header-cell *matHeaderCellDef>Name</th><td mat-cell *matCellDef="let r">{{ r.name }}</td></ng-container>
        <ng-container matColumnDef="status"><th mat-header-cell *matHeaderCellDef>Status</th><td mat-cell *matCellDef="let r">{{ r.status }}</td></ng-container>
        <ng-container matColumnDef="version"><th mat-header-cell *matHeaderCellDef>Version</th><td mat-cell *matCellDef="let r">v{{ r.version }}</td></ng-container>
        <ng-container matColumnDef="gwp"><th mat-header-cell *matHeaderCellDef>GWP</th><td mat-cell *matCellDef="let r">{{ r.gwpDatasetCode }}</td></ng-container>
        <ng-container matColumnDef="actions"><th mat-header-cell *matHeaderCellDef></th><td mat-cell *matCellDef="let r"><a mat-button [routerLink]="['/app/carbon-inventories', r.id]">Open</a></td></ng-container>
        <tr mat-header-row *matHeaderRowDef="cols"></tr>
        <tr mat-row *matRowDef="let row; columns: cols"></tr>
      </table>
    </div>
  `,
  styles: [`.page{padding:1rem}.header{display:flex;justify-content:space-between;align-items:center}.full{width:100%}.error{color:#b00020}`],
})
export class CarbonInventoryListComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly auth = inject(AuthService);
  readonly items = signal<CarbonInventory[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly canCreate = canCreateInventory(this.auth.currentRoles());
  readonly cols = ['name', 'status', 'version', 'gwp', 'actions'];

  ngOnInit(): void {
    this.api.listInventories({ pageSize: 50 }).subscribe({
      next: (p) => this.items.set(p.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-carbon-inventory-detail',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
    MatCardModule,
  ],
  template: `
    <div class="page">
      <a routerLink="/app/carbon-inventories">← Inventories</a>
      @if (isNew) {
        <h1>Create carbon inventory</h1>
        @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
        <form [formGroup]="form" (ngSubmit)="create()">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Reporting period</mat-label>
            <mat-select formControlName="reportingPeriodId">
              @for (p of periods(); track p.id) {
                <mat-option [value]="p.id">{{ p.code }} — {{ p.name }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Name</mat-label>
            <input matInput formControlName="name" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Description</mat-label>
            <textarea matInput rows="3" formControlName="description"></textarea>
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>GWP dataset</mat-label>
            <input matInput formControlName="gwpDatasetCode" />
          </mat-form-field>
          <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">Create</button>
        </form>
      } @else if (inventory()) {
        <h1>{{ inventory()!.name }}</h1>
        <p>Status: <strong>{{ inventory()!.status }}</strong> · GWP {{ inventory()!.gwpDatasetCode }} · engine methodology {{ inventory()!.calculationMethodologyVersion }}</p>
        @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
        <div class="actions">
          @if (canCreate && inventory()!.status !== 'approved') {
            <a mat-stroked-button [routerLink]="['/app/carbon-inventories', inventory()!.id, 'validation']">Validate</a>
          }
          @if (canCalc && inventory()!.status !== 'approved') {
            <button mat-flat-button color="primary" type="button" (click)="calculate(false)">Calculate</button>
            <button mat-stroked-button type="button" (click)="calculate(true)">Partial calculate</button>
            <button mat-stroked-button type="button" (click)="recalculate()">Recalculate</button>
          }
          @if (canCalc && inventory()!.status === 'calculated') {
            <button mat-stroked-button type="button" (click)="submitReview()">Submit review</button>
          }
          @if (canApprove && (inventory()!.status === 'calculated' || inventory()!.status === 'under_review')) {
            <button mat-flat-button color="accent" type="button" (click)="approve()">Approve</button>
          }
          <a mat-button [routerLink]="['/app/carbon-inventories', inventory()!.id, 'results']">Results</a>
        </div>

        @if (summary()) {
          <div class="cards">
            <mat-card><mat-card-title>Total tCO2e</mat-card-title><mat-card-content>{{ summary()!.totalTCo2e }}</mat-card-content></mat-card>
            <mat-card><mat-card-title>Scope 1</mat-card-title><mat-card-content>{{ summary()!.scope1TotalTCo2e || summary()!.scope1TotalKgCo2e }}</mat-card-content></mat-card>
            <mat-card><mat-card-title>Scope 2</mat-card-title><mat-card-content>{{ summary()!.scope2TotalTCo2e || summary()!.scope2TotalKgCo2e }}</mat-card-content></mat-card>
            <mat-card><mat-card-title>Scope 3</mat-card-title><mat-card-content>{{ summary()!.scope3TotalTCo2e || summary()!.scope3TotalKgCo2e }}</mat-card-content></mat-card>
          </div>
        }

        <h2>Runs</h2>
        <table mat-table [dataSource]="runs()" class="full">
          <ng-container matColumnDef="run"><th mat-header-cell *matHeaderCellDef>Run</th><td mat-cell *matCellDef="let r">#{{ r.runNumber }}</td></ng-container>
          <ng-container matColumnDef="status"><th mat-header-cell *matHeaderCellDef>Status</th><td mat-cell *matCellDef="let r">{{ r.status }}</td></ng-container>
          <ng-container matColumnDef="total"><th mat-header-cell *matHeaderCellDef>tCO2e</th><td mat-cell *matCellDef="let r">{{ r.totalTCo2e }}</td></ng-container>
          <ng-container matColumnDef="engine"><th mat-header-cell *matHeaderCellDef>Engine</th><td mat-cell *matCellDef="let r">{{ r.engineVersion }}</td></ng-container>
          <ng-container matColumnDef="open"><th mat-header-cell *matHeaderCellDef></th><td mat-cell *matCellDef="let r"><a mat-button [routerLink]="['/app/carbon-inventories', inventory()!.id, 'runs', r.id]">Open</a></td></ng-container>
          <tr mat-header-row *matHeaderRowDef="runCols"></tr>
          <tr mat-row *matRowDef="let row; columns: runCols"></tr>
        </table>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 1rem; }
      .full { width: 100%; display: block; margin-bottom: 0.75rem; }
      .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }
      .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }
      .error { color: #b00020; }
    `,
  ],
})
export class CarbonInventoryDetailComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly periodsApi = inject(ReportingPeriodService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly inventory = signal<CarbonInventory | null>(null);
  readonly summary = signal<InventorySummary | null>(null);
  readonly runs = signal<CalculationRun[]>([]);
  readonly periods = signal<ReportingPeriod[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly canCreate = canCreateInventory(this.auth.currentRoles());
  readonly canCalc = canCalculateInventory(this.auth.currentRoles());
  readonly canApprove = canApproveInventory(this.auth.currentRoles());
  readonly runCols = ['run', 'status', 'total', 'engine', 'open'];
  isNew = false;

  readonly form = this.fb.nonNullable.group({
    reportingPeriodId: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    gwpDatasetCode: ['AR5-demo', Validators.required],
  });

  ngOnInit(): void {
    this.isNew = this.router.url.endsWith('/new');
    if (this.isNew) {
      this.periodsApi.list({ pageSize: 100 }).subscribe({
        next: (p) => this.periods.set(p.items),
      });
      return;
    }
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.load(id);
  }

  private load(id: string): void {
    this.api.getInventory(id).subscribe({
      next: (inv) => {
        this.inventory.set(inv);
        this.api.getSummary(id).subscribe({ next: (s) => this.summary.set(s) });
        this.api.listRuns(id).subscribe({ next: (r) => this.runs.set(r) });
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  create(): void {
    this.api.createInventory(this.form.getRawValue()).subscribe({
      next: (inv) => void this.router.navigate(['/app/carbon-inventories', inv.id]),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  calculate(partial: boolean): void {
    const inv = this.inventory();
    if (!inv) return;
    this.api.calculateInventory(inv.id, partial).subscribe({
      next: () => this.load(inv.id),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  recalculate(): void {
    const inv = this.inventory();
    if (!inv) return;
    this.api.recalculate(inv.id, true).subscribe({
      next: () => this.load(inv.id),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  submitReview(): void {
    const inv = this.inventory();
    if (!inv) return;
    this.api.submitReview(inv.id).subscribe({
      next: (updated) => this.inventory.set(updated),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  approve(): void {
    const inv = this.inventory();
    if (!inv) return;
    this.api.approveInventory(inv.id).subscribe({
      next: (updated) => this.inventory.set(updated),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-carbon-inventory-validation',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatCardModule, JsonPipe],
  template: `
    <div class="page">
      <a [routerLink]="['/app/carbon-inventories', id]">← Inventory</a>
      <h1>Validation results</h1>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      <button mat-flat-button color="primary" type="button" (click)="run()">Run validation</button>
      @if (result()) {
        <div class="cards">
          <mat-card><mat-card-title>Valid</mat-card-title><mat-card-content>{{ result()!.valid.length }}</mat-card-content></mat-card>
          <mat-card><mat-card-title>Missing factors</mat-card-title><mat-card-content>{{ result()!.missingFactors.length }}</mat-card-content></mat-card>
          <mat-card><mat-card-title>Ambiguous</mat-card-title><mat-card-content>{{ result()!.ambiguousFactors.length }}</mat-card-content></mat-card>
          <mat-card><mat-card-title>Unapproved</mat-card-title><mat-card-content>{{ result()!.unapprovedRecords.length }}</mat-card-content></mat-card>
          <mat-card><mat-card-title>Blocking errors</mat-card-title><mat-card-content>{{ result()!.blockingErrorCount }}</mat-card-content></mat-card>
        </div>
        <pre>{{ result() | json }}</pre>
      }
    </div>
  `,
  styles: [`.page{padding:1rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem;margin-top:1rem}.error{color:#b00020}pre{white-space:pre-wrap;background:#f7f7f7;padding:1rem}`],
})
export class CarbonInventoryValidationComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly route = inject(ActivatedRoute);
  readonly result = signal<ValidationResult | null>(null);
  readonly errorMessage = signal<string | null>(null);
  id = '';

  ngOnInit(): void {
    this.id = this.route.snapshot.paramMap.get('id') || '';
    this.run();
  }

  run(): void {
    this.api.validateInventory(this.id).subscribe({
      next: (r) => this.result.set(r),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-carbon-inventory-results',
  standalone: true,
  imports: [RouterLink, MatTableModule, MatCardModule],
  template: `
    <div class="page">
      <a [routerLink]="['/app/carbon-inventories', id]">← Inventory</a>
      <h1>Calculation results</h1>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      @if (summary()) {
        <div class="cards">
          <mat-card><mat-card-title>Total tCO2e</mat-card-title><mat-card-content>{{ summary()!.totalTCo2e }}</mat-card-content></mat-card>
          <mat-card><mat-card-title>Errors</mat-card-title><mat-card-content>{{ summary()!.errorCounts }}</mat-card-content></mat-card>
        </div>
        <h2>Category totals</h2>
        <table mat-table [dataSource]="summary()!.categoryTotals" class="full">
          <ng-container matColumnDef="category"><th mat-header-cell *matHeaderCellDef>Category</th><td mat-cell *matCellDef="let r">{{ r.category }}</td></ng-container>
          <ng-container matColumnDef="t"><th mat-header-cell *matHeaderCellDef>tCO2e</th><td mat-cell *matCellDef="let r">{{ r.tCo2e }}</td></ng-container>
          <tr mat-header-row *matHeaderRowDef="['category','t']"></tr>
          <tr mat-row *matRowDef="let row; columns: ['category','t']"></tr>
        </table>
      }
      <h2>Items</h2>
      <table mat-table [dataSource]="items()" class="full">
        <ng-container matColumnDef="scope"><th mat-header-cell *matHeaderCellDef>Scope</th><td mat-cell *matCellDef="let r">{{ r.scope }}</td></ng-container>
        <ng-container matColumnDef="status"><th mat-header-cell *matHeaderCellDef>Status</th><td mat-cell *matCellDef="let r">{{ r.status }}</td></ng-container>
        <ng-container matColumnDef="total"><th mat-header-cell *matHeaderCellDef>kgCO2e</th><td mat-cell *matCellDef="let r">{{ r.totalKgCo2e }}</td></ng-container>
        <ng-container matColumnDef="formula"><th mat-header-cell *matHeaderCellDef>Formula</th><td mat-cell *matCellDef="let r">{{ r.calculationFormula }}</td></ng-container>
        <ng-container matColumnDef="open"><th mat-header-cell *matHeaderCellDef></th><td mat-cell *matCellDef="let r"><a mat-button [routerLink]="['/app/carbon-calculation-items', r.id]">Detail</a></td></ng-container>
        <tr mat-header-row *matHeaderRowDef="itemCols"></tr>
        <tr mat-row *matRowDef="let row; columns: itemCols"></tr>
      </table>
    </div>
  `,
  styles: [`.page{padding:1rem}.full{width:100%;margin-bottom:1rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.75rem}.error{color:#b00020}`],
})
export class CarbonInventoryResultsComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly route = inject(ActivatedRoute);
  readonly summary = signal<InventorySummary | null>(null);
  readonly items = signal<CalculationItem[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly itemCols = ['scope', 'status', 'total', 'formula', 'open'];
  id = '';

  ngOnInit(): void {
    this.id = this.route.snapshot.paramMap.get('id') || '';
    this.api.getSummary(this.id).subscribe({
      next: (s) => this.summary.set(s),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listItems(this.id, { pageSize: 100 }).subscribe({
      next: (p) => this.items.set(p.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-calculation-item-detail',
  standalone: true,
  imports: [MatCardModule, JsonPipe],
  template: `
    <div class="page">
      <h1>Calculation item audit detail</h1>
      @if (errorMessage()) { <p class="error">{{ errorMessage() }}</p> }
      @if (detail()) {
        <pre>{{ detail() | json }}</pre>
      }
    </div>
  `,
  styles: [`.page{padding:1rem}pre{white-space:pre-wrap;background:#f7f7f7;padding:1rem}.error{color:#b00020}`],
})
export class CalculationItemDetailComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly route = inject(ActivatedRoute);
  readonly detail = signal<Record<string, unknown> | null>(null);
  readonly errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('itemId') || this.route.snapshot.paramMap.get('id') || '';
    this.api.getItemDetail(id).subscribe({
      next: (d) => this.detail.set(d),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
