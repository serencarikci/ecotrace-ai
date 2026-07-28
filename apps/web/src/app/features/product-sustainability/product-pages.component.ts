import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import type { EChartsCoreOption } from 'echarts/core';
import {
  DigitalProductPassport,
  Product,
  ProductSustainabilityService,
} from '../../core/services/product-sustainability.service';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { AuthService } from '../../core/services/auth.service';
import { ChartComponent } from '../../shared/chart.component';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <section class="page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Products</h1>
          <p class="page-subtitle">Product master data for LCA and passport workflows.</p>
        </div>
        <a mat-flat-button color="primary" routerLink="/app/products/new">Create product</a>
      </div>
      <form class="filters" [formGroup]="filters" (ngSubmit)="load()">
        <mat-form-field appearance="outline">
          <mat-label>Search</mat-label>
          <input matInput formControlName="search" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Type</mat-label>
          <mat-select formControlName="productType">
            <mat-option value="">All</mat-option>
            <mat-option value="finished_good">Finished good</mat-option>
            <mat-option value="component">Component</mat-option>
            <mat-option value="packaging">Packaging</mat-option>
          </mat-select>
        </mat-form-field>
        <button mat-stroked-button type="submit">Filter</button>
      </form>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else if (!items().length) {
        <p>No products yet.</p>
      } @else {
        <table mat-table [dataSource]="items()" class="surface-card full-width">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row.code }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">
              <a [routerLink]="['/app/products', row.id]">{{ row.name }}</a>
            </td>
          </ng-container>
          <ng-container matColumnDef="productType">
            <th mat-header-cell *matHeaderCellDef>Type</th>
            <td mat-cell *matCellDef="let row">{{ row.productType }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row.isActive ? 'Active' : 'Archived' }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="cols"></tr>
          <tr mat-row *matRowDef="let row; columns: cols"></tr>
        </table>
      }
    </section>
  `,
  styles: `
    .page-header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }
    .full-width {
      width: 100%;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class ProductListComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly fb = inject(FormBuilder);
  readonly items = signal<Product[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly cols = ['code', 'name', 'productType', 'status'];
  readonly filters = this.fb.nonNullable.group({ search: [''], productType: [''] });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    const f = this.filters.getRawValue();
    this.api
      .listProducts({
        search: f.search || undefined,
        productType: f.productType || undefined,
        isActive: true,
      })
      .subscribe({
        next: (page) => {
          this.items.set(page.items);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }
}

@Component({
  selector: 'app-product-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    RouterLink,
  ],
  template: `
    <section class="page">
      <h1 class="page-title">New product</h1>
      <form class="surface-card form" [formGroup]="form" (ngSubmit)="save()">
        <mat-form-field appearance="outline"
          ><mat-label>Code</mat-label><input matInput formControlName="code"
        /></mat-form-field>
        <mat-form-field appearance="outline"
          ><mat-label>Name</mat-label><input matInput formControlName="name"
        /></mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Type</mat-label>
          <mat-select formControlName="productType">
            <mat-option value="finished_good">Finished good</mat-option>
            <mat-option value="component">Component</mat-option>
            <mat-option value="packaging">Packaging</mat-option>
            <mat-option value="intermediate_good">Intermediate</mat-option>
            <mat-option value="other">Other</mat-option>
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline"
          ><mat-label>Default unit</mat-label
          ><input matInput formControlName="defaultUnitCode"
        /></mat-form-field>
        <mat-form-field appearance="outline"
          ><mat-label>Recyclability %</mat-label
          ><input matInput formControlName="recyclabilityPercentage"
        /></mat-form-field>
        <mat-form-field appearance="outline"
          ><mat-label>Recycled content %</mat-label
          ><input matInput formControlName="recycledContentPercentage"
        /></mat-form-field>
        <mat-form-field appearance="outline"
          ><mat-label>Repairability 1-10</mat-label
          ><input matInput type="number" formControlName="repairabilityScore"
        /></mat-form-field>
        @if (errorMessage()) {
          <p class="error">{{ errorMessage() }}</p>
        }
        <div class="actions">
          <a mat-button routerLink="/app/products">Cancel</a>
          <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid || saving()">
            Save
          </button>
        </div>
      </form>
    </section>
  `,
  styles: `
    .form {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
      padding: 1rem;
    }
    .actions {
      grid-column: 1 / -1;
      display: flex;
      gap: 0.75rem;
    }
    .error {
      color: #8b1e1e;
      grid-column: 1 / -1;
    }
  `,
})
export class ProductFormComponent {
  private readonly api = inject(ProductSustainabilityService);
  private readonly fb = inject(FormBuilder);
  readonly saving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly form = this.fb.nonNullable.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    productType: ['finished_good', Validators.required],
    defaultUnitCode: ['unit', Validators.required],
    recyclabilityPercentage: [''],
    recycledContentPercentage: [''],
    repairabilityScore: [null as number | null],
  });

  save(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    const raw = this.form.getRawValue();
    this.api
      .createProduct({
        code: raw.code,
        name: raw.name,
        productType: raw.productType,
        defaultUnitCode: raw.defaultUnitCode,
        recyclabilityPercentage: raw.recyclabilityPercentage || null,
        recycledContentPercentage: raw.recycledContentPercentage || null,
        repairabilityScore: raw.repairabilityScore,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          history.back();
        },
        error: (err: unknown) => {
          this.saving.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }
}

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatProgressSpinnerModule],
  template: `
    <section class="page">
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (product()) {
        <h1 class="page-title">{{ product()!.name }}</h1>
        <p class="page-subtitle">{{ product()!.code }} · {{ product()!.productType }}</p>
        <div class="surface-card block">
          <p>Recycled content: {{ product()!.recycledContentPercentage || '—' }}%</p>
          <p>Recyclability: {{ product()!.recyclabilityPercentage || '—' }}%</p>
          <p>Repairability (1–10): {{ product()!.repairabilityScore ?? '—' }}</p>
          <p class="muted">No certification badges. Demo values are not authoritative.</p>
        </div>
        <a mat-stroked-button [routerLink]="['/app/products', product()!.id, 'boms']">BOMs</a>
      }
    </section>
  `,
  styles: `
    .block {
      padding: 1rem;
      margin-bottom: 1rem;
    }
    .muted {
      color: var(--et-muted);
    }
  `,
})
export class ProductDetailComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly route = inject(ActivatedRoute);
  readonly product = signal<Product | null>(null);
  readonly loading = signal(true);
  ngOnInit(): void {
    this.api.getProduct(this.route.snapshot.paramMap.get('id')!).subscribe({
      next: (p) => {
        this.product.set(p);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}

@Component({
  selector: 'app-simple-entity-list',
  standalone: true,
  imports: [MatTableModule, MatProgressSpinnerModule],
  template: `
    <section class="page">
      <h1 class="page-title">{{ title }}</h1>
      <p class="page-subtitle">{{ subtitle }}</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <table mat-table [dataSource]="rows()" class="surface-card full-width">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row['code'] }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row['name'] }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row['status'] }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="cols"></tr>
          <tr mat-row *matRowDef="let row; columns: cols"></tr>
        </table>
      }
    </section>
  `,
  styles: `
    .full-width {
      width: 100%;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class SimpleEntityListComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly route = inject(ActivatedRoute);
  readonly rows = signal<Record<string, unknown>[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly cols = ['code', 'name', 'status'];
  title = 'List';
  subtitle = '';

  ngOnInit(): void {
    const kind = this.route.snapshot.data['kind'] as string;
    this.loading.set(true);
    const finish = (rows: Record<string, unknown>[]) => {
      this.rows.set(rows);
      this.loading.set(false);
    };
    const fail = (err: unknown) => {
      this.loading.set(false);
      this.errorMessage.set(extractApiErrorMessage(err));
    };
    if (kind === 'suppliers') {
      this.title = 'Suppliers';
      this.subtitle = 'Internal sustainability ratings are not certified assessments.';
      this.api.listSuppliers().subscribe({
        next: (p) => finish(p.items as unknown as Record<string, unknown>[]),
        error: fail,
      });
    } else if (kind === 'materials') {
      this.title = 'Materials';
      this.subtitle = 'Material masters for BOM and LCA inventory.';
      this.api.listMaterials().subscribe({
        next: (p) =>
          finish(
            p.items.map((m) => ({
              code: m.code,
              name: m.name,
              status: m.isActive ? 'active' : 'archived',
            })),
          ),
        error: fail,
      });
    } else if (kind === 'batches') {
      this.title = 'Product batches';
      this.subtitle = 'Batch tracking with validated status transitions.';
      this.api.listBatches().subscribe({
        next: (p) =>
          finish(
            p.items.map((b) => ({
              code: b['batchCode'],
              name: b['batchCode'],
              status: b['status'],
            })),
          ),
        error: fail,
      });
    } else if (kind === 'studies') {
      this.title = 'LCA studies';
      this.subtitle = 'ISO 14040/14044-inspired prototype LCA studies.';
      this.api.listStudies().subscribe({
        next: (p) => finish(p.items as unknown as Record<string, unknown>[]),
        error: fail,
      });
    } else if (kind === 'footprints') {
      this.title = 'Product carbon footprints';
      this.subtitle = 'Functional-unit normalized product carbon footprint estimates.';
      this.api.listFootprints().subscribe({
        next: (p) =>
          finish(
            p.items.map((f) => ({
              code: f.id.slice(0, 8),
              name: `${f.totalKgCo2e} kgCO2e / FU`,
              status: f.status,
            })),
          ),
        error: fail,
      });
    } else {
      this.title = 'Digital Product Passports';
      this.subtitle = 'Non-certified passport drafts and publications.';
      this.api.listPassports().subscribe({
        next: (p) =>
          finish(
            p.items.map((x) => ({
              code: x.passportCode,
              name: x.title,
              status: x.status,
            })),
          ),
        error: fail,
      });
    }
  }
}

@Component({
  selector: 'app-lca-study-detail',
  standalone: true,
  imports: [MatButtonModule, MatProgressSpinnerModule, ChartComponent],
  template: `
    <section class="page">
      <h1 class="page-title">LCA results</h1>
      <p class="page-subtitle">Methodology-informed product carbon footprint estimate.</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else if (results()) {
        <div class="metric-row">
          <div class="surface-card metric">
            <div class="label">FU kgCO2e</div>
            <div class="value">{{ run()?.['functionalUnitKgCo2e'] }}</div>
          </div>
          <div class="surface-card metric">
            <div class="label">Total kgCO2e</div>
            <div class="value">{{ run()?.['totalKgCo2e'] }}</div>
          </div>
        </div>
        <div class="surface-card">
          <h2>Lifecycle stages</h2>
          <app-chart [option]="stageOption()" />
        </div>
        <p class="muted">{{ results()?.['disclaimer'] }}</p>
      }
    </section>
  `,
  styles: `
    .metric-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .metric .value {
      font-family: var(--et-font-display);
      font-size: 1.3rem;
    }
    .muted {
      color: var(--et-muted);
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class LcaStudyDetailComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly route = inject(ActivatedRoute);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly results = signal<Record<string, unknown> | null>(null);
  readonly stageOption = signal<EChartsCoreOption>({});

  ngOnInit(): void {
    this.api.getStudyResults(this.route.snapshot.paramMap.get('id')!).subscribe({
      next: (res) => {
        this.results.set(res);
        const run = res['run'] as Record<string, unknown>;
        const summary = (run?.['resultSummaryJson'] as Record<string, unknown>) || {};
        const byStage = (summary['byLifecycleStage'] as Record<string, string>) || {};
        this.stageOption.set({
          tooltip: { trigger: 'item' },
          series: [
            {
              type: 'pie',
              radius: ['35%', '65%'],
              data: Object.entries(byStage).map(([name, value]) => ({
                name,
                value: Number(value),
              })),
            },
          ],
        });
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  run(): Record<string, unknown> | null {
    return (this.results()?.['run'] as Record<string, unknown>) ?? null;
  }
}

@Component({
  selector: 'app-passport-detail',
  standalone: true,
  imports: [MatButtonModule, MatProgressSpinnerModule, RouterLink],
  template: `
    <section class="page">
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (passport()) {
        <h1 class="page-title">{{ passport()!.title }}</h1>
        <p class="page-subtitle">
          {{ passport()!.passportCode }} · v{{ passport()!.version }} · {{ passport()!.status }}
        </p>
        <p>{{ passport()!.disclaimer }}</p>
        <a mat-stroked-button [routerLink]="['/passport', passport()!.publicSlug]">Public preview</a>
        @if (canPublish() && passport()!.status !== 'published') {
          <button mat-flat-button color="primary" type="button" (click)="publish()">Publish</button>
        }
        @if (errorMessage()) {
          <p class="error">{{ errorMessage() }}</p>
        }
      }
    </section>
  `,
  styles: `
    .error {
      color: #8b1e1e;
    }
  `,
})
export class PassportDetailComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  readonly passport = signal<DigitalProductPassport | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.api.getPassport(this.route.snapshot.paramMap.get('id')!).subscribe({
      next: (p) => {
        this.passport.set(p);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  canPublish(): boolean {
    const roles = this.auth.currentRoles();
    return roles.includes('organization_admin') || roles.includes('system_admin');
  }

  publish(): void {
    const id = this.passport()?.id;
    if (!id) return;
    this.api.publishPassport(id).subscribe({
      next: (p) => this.passport.set(p),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-product-bom-list',
  standalone: true,
  imports: [MatTableModule, MatProgressSpinnerModule],
  template: `
    <section class="page">
      <h1 class="page-title">Bills of materials</h1>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else {
        <table mat-table [dataSource]="rows()" class="surface-card full-width">
          <ng-container matColumnDef="version">
            <th mat-header-cell *matHeaderCellDef>Version</th>
            <td mat-cell *matCellDef="let row">{{ row['version'] }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row['name'] }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row['status'] }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="cols"></tr>
          <tr mat-row *matRowDef="let row; columns: cols"></tr>
        </table>
      }
    </section>
  `,
  styles: `
    .full-width {
      width: 100%;
    }
  `,
})
export class ProductBomListComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly route = inject(ActivatedRoute);
  readonly rows = signal<Record<string, unknown>[]>([]);
  readonly loading = signal(true);
  readonly cols = ['version', 'name', 'status'];
  ngOnInit(): void {
    this.api.listBoms(this.route.snapshot.paramMap.get('id')!).subscribe({
      next: (rows) => {
        this.rows.set(rows);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}

@Component({
  selector: 'app-product-placeholder',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="page">
      <h1 class="page-title">{{ title }}</h1>
      <p class="page-subtitle">{{ subtitle }}</p>
      <a mat-stroked-button routerLink="/app/products">Back</a>
    </section>
  `,
})
export class ProductPlaceholderComponent {
  private readonly route = inject(ActivatedRoute);
  title = (this.route.snapshot.data['title'] as string) || 'Workspace';
  subtitle =
    (this.route.snapshot.data['subtitle'] as string) ||
    'Manage this area via detail screens and API workflows.';
}
