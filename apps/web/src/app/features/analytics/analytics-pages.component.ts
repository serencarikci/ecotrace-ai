import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import type { EChartsCoreOption } from 'echarts/core';
import { AnalyticsService } from '../../core/services/analytics.service';
import { extractApiErrorMessage } from '../../core/services/error.util';
import {
  AnalyticsDashboard,
  Baseline,
  Recommendation,
  ReductionInitiative,
  Scenario,
  SustainabilityTarget,
  TrendPoint,
} from '../../core/models/analytics.models';
import { ChartComponent } from '../../shared/chart.component';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [MatButtonModule, MatProgressSpinnerModule, ChartComponent],
  template: `
    <section class="page">
      <h1 class="page-title">Executive Analytics</h1>
      <p class="page-subtitle">Approved inventory totals and scope distribution.</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else if (dashboard()) {
        @if (dashboard()!.metadata.provisional) {
          <p class="warning">Provisional inventory — not approved.</p>
        }
        <div class="metric-row">
          <div class="surface-card metric">
            <div class="label">Total tCO2e</div>
            <div class="value">{{ dashboard()!.summary.totalEmissionsTCo2e }}</div>
          </div>
          <div class="surface-card metric">
            <div class="label">Scope 1</div>
            <div class="value">{{ dashboard()!.summary.scope1KgCo2e }} kg</div>
          </div>
          <div class="surface-card metric">
            <div class="label">Scope 2</div>
            <div class="value">{{ dashboard()!.summary.scope2KgCo2e }} kg</div>
          </div>
          <div class="surface-card metric">
            <div class="label">Scope 3</div>
            <div class="value">{{ dashboard()!.summary.scope3KgCo2e }} kg</div>
          </div>
        </div>
        @if (!dashboard()!.empty) {
          <div class="chart-grid">
            <div class="surface-card">
              <h2>Scope share</h2>
              <app-chart [option]="scopeOption()" />
            </div>
            <div class="surface-card">
              <h2>Top categories</h2>
              <app-chart [option]="categoryOption()" />
            </div>
          </div>
        } @else {
          <p>No calculated items for the selected inventory.</p>
        }
      }
    </section>
  `,
  styles: `
    .metric-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .metric .label {
      color: var(--et-muted);
      font-size: 0.85rem;
    }
    .metric .value {
      font-family: var(--et-font-display);
      font-size: 1.4rem;
      margin-top: 0.35rem;
    }
    .chart-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
    .warning {
      color: #8a5a00;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class AnalyticsDashboardComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly dashboard = signal<AnalyticsDashboard | null>(null);
  readonly scopeOption = signal<EChartsCoreOption | null>(null);
  readonly categoryOption = signal<EChartsCoreOption | null>(null);

  ngOnInit(): void {
    this.api.dashboard().subscribe({
      next: (data) => {
        this.dashboard.set(data);
        this.scopeOption.set({
          tooltip: { trigger: 'item' },
          series: [
            {
              type: 'pie',
              radius: ['40%', '70%'],
              data: [
                { name: 'Scope 1', value: Number(data.summary.scope1KgCo2e) },
                { name: 'Scope 2', value: Number(data.summary.scope2KgCo2e) },
                { name: 'Scope 3', value: Number(data.summary.scope3KgCo2e) },
              ],
            },
          ],
        });
        this.categoryOption.set({
          tooltip: { trigger: 'axis' },
          xAxis: {
            type: 'category',
            data: data.categoryDistribution.slice(0, 6).map((r) => r.name),
          },
          yAxis: { type: 'value' },
          series: [
            {
              type: 'bar',
              data: data.categoryDistribution.slice(0, 6).map((r) => Number(r.totalKgCo2e)),
            },
          ],
        });
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-analytics-trends',
  standalone: true,
  imports: [MatProgressSpinnerModule, ChartComponent],
  template: `
    <section class="page">
      <h1 class="page-title">Emission Trends</h1>
      <p class="page-subtitle">Monthly totals from activity dates in the selected inventory.</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else if (empty()) {
        <p>No trend points available.</p>
      } @else {
        <div class="surface-card"><app-chart [option]="option()" height="320px" /></div>
      }
    </section>
  `,
  styles: `.error { color: #8b1e1e; }`,
})
export class AnalyticsTrendsComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly empty = signal(false);
  readonly option = signal<EChartsCoreOption | null>(null);

  ngOnInit(): void {
    this.api.monthlyTrends().subscribe({
      next: (res) => {
        this.empty.set(res.empty || res.points.length === 0);
        const points: TrendPoint[] = res.points;
        this.option.set({
          tooltip: { trigger: 'axis' },
          legend: { data: ['Total', 'Scope 1', 'Scope 2', 'Scope 3'] },
          xAxis: { type: 'category', data: points.map((p) => p.period) },
          yAxis: { type: 'value' },
          series: [
            { name: 'Total', type: 'line', data: points.map((p) => Number(p.totalKgCo2e)) },
            { name: 'Scope 1', type: 'line', data: points.map((p) => Number(p.scope1KgCo2e)) },
            { name: 'Scope 2', type: 'line', data: points.map((p) => Number(p.scope2KgCo2e)) },
            { name: 'Scope 3', type: 'line', data: points.map((p) => Number(p.scope3KgCo2e)) },
          ],
        });
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-analytics-breakdown',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatTableModule, ChartComponent],
  template: `
    <section class="page">
      <h1 class="page-title">Breakdown</h1>
      <p class="page-subtitle">Dimension: {{ dimension }}</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <div class="surface-card"><app-chart [option]="option()" /></div>
        <table mat-table [dataSource]="rows()" class="mat-elevation-z0">
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="totalKgCo2e">
            <th mat-header-cell *matHeaderCellDef>kgCO2e</th>
            <td mat-cell *matCellDef="let row">{{ row.totalKgCo2e }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
      }
    </section>
  `,
  styles: `
    table {
      width: 100%;
      margin-top: 1rem;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class AnalyticsBreakdownComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  private readonly route = inject(ActivatedRoute);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly rows = signal<Array<{ name: string; totalKgCo2e: string }>>([]);
  readonly option = signal<EChartsCoreOption | null>(null);
  readonly columns = ['name', 'totalKgCo2e'];
  dimension = 'categories';

  ngOnInit(): void {
    this.dimension = this.route.snapshot.data['dimension'] || 'categories';
    this.api.breakdown(this.dimension).subscribe({
      next: (res) => {
        const items = (res.items || []).map((item) => {
          const row = item as { name?: string; totalKgCo2e?: string };
          return {
            name: String(row.name ?? ''),
            totalKgCo2e: String(row.totalKgCo2e ?? '0'),
          };
        });
        this.rows.set(items);
        this.option.set({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: items.map((i) => i.name) },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: items.map((i) => Number(i.totalKgCo2e)) }],
        });
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-analytics-intensity-kpis',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatTableModule],
  template: `
    <section class="page">
      <h1 class="page-title">Intensity &amp; KPIs</h1>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <h2>Intensity</h2>
        <pre class="surface-card">{{ intensityJson() }}</pre>
        <h2>KPIs</h2>
        <pre class="surface-card">{{ kpiJson() }}</pre>
      }
    </section>
  `,
  styles: `
    pre {
      white-space: pre-wrap;
      font-size: 0.85rem;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class AnalyticsIntensityKpisComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly intensityJson = signal('');
  readonly kpiJson = signal('');

  ngOnInit(): void {
    this.api.intensity().subscribe({
      next: (intensity) => {
        this.intensityJson.set(JSON.stringify(intensity.items, null, 2));
        this.api.kpis().subscribe({
          next: (kpis) => {
            this.kpiJson.set(JSON.stringify(kpis.items, null, 2));
            this.loading.set(false);
          },
          error: (err) => {
            this.errorMessage.set(extractApiErrorMessage(err));
            this.loading.set(false);
          },
        });
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-planning-baselines',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatTableModule],
  template: `
    <section class="page">
      <h1 class="page-title">Baselines</h1>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <table mat-table [dataSource]="rows()" class="mat-elevation-z0">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row.code }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row.status }}</td>
          </ng-container>
          <ng-container matColumnDef="baselineValue">
            <th mat-header-cell *matHeaderCellDef>Value</th>
            <td mat-cell *matCellDef="let row">{{ row.baselineValue }} {{ row.baselineUnit }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
      }
    </section>
  `,
  styles: `
    table {
      width: 100%;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class PlanningBaselinesComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly rows = signal<Baseline[]>([]);
  readonly columns = ['code', 'name', 'status', 'baselineValue'];

  ngOnInit(): void {
    this.api.listBaselines().subscribe({
      next: (page) => {
        this.rows.set(page.items);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-planning-targets',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatTableModule, MatButtonModule],
  template: `
    <section class="page">
      <h1 class="page-title">Targets</h1>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <table mat-table [dataSource]="rows()" class="mat-elevation-z0">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row.code }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row.status }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              <button mat-button type="button" (click)="loadProgress(row.id)">Progress</button>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
        @if (progressJson()) {
          <pre class="surface-card">{{ progressJson() }}</pre>
        }
      }
    </section>
  `,
  styles: `
    table {
      width: 100%;
    }
    pre {
      white-space: pre-wrap;
      margin-top: 1rem;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class PlanningTargetsComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly rows = signal<SustainabilityTarget[]>([]);
  readonly progressJson = signal('');
  readonly columns = ['code', 'name', 'status', 'actions'];

  ngOnInit(): void {
    this.api.listTargets().subscribe({
      next: (page) => {
        this.rows.set(page.items);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  loadProgress(id: string): void {
    this.api.targetProgress(id).subscribe({
      next: (data) => this.progressJson.set(JSON.stringify(data, null, 2)),
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-planning-initiatives',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatTableModule],
  template: `
    <section class="page">
      <h1 class="page-title">Reduction Initiatives</h1>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <table mat-table [dataSource]="rows()" class="mat-elevation-z0">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row.code }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row.status }}</td>
          </ng-container>
          <ng-container matColumnDef="expectedReductionKgCo2e">
            <th mat-header-cell *matHeaderCellDef>Expected kgCO2e</th>
            <td mat-cell *matCellDef="let row">{{ row.expectedReductionKgCo2e }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
      }
    </section>
  `,
  styles: `
    table {
      width: 100%;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class PlanningInitiativesComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly rows = signal<ReductionInitiative[]>([]);
  readonly columns = ['code', 'name', 'status', 'expectedReductionKgCo2e'];

  ngOnInit(): void {
    this.api.listInitiatives().subscribe({
      next: (page) => {
        this.rows.set(page.items);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-planning-scenarios',
  standalone: true,
  imports: [MatProgressSpinnerModule, MatTableModule, MatButtonModule],
  template: `
    <section class="page">
      <h1 class="page-title">Scenarios</h1>
      <p class="page-subtitle">What-if runs never mutate activity records or inventories.</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else {
        <table mat-table [dataSource]="rows()" class="mat-elevation-z0">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row.code }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">{{ row.status }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              <button mat-button type="button" (click)="calculate(row.id)">Calculate</button>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
        @if (runJson()) {
          <pre class="surface-card">{{ runJson() }}</pre>
        }
      }
    </section>
  `,
  styles: `
    table {
      width: 100%;
    }
    pre {
      white-space: pre-wrap;
      margin-top: 1rem;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class PlanningScenariosComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly rows = signal<Scenario[]>([]);
  readonly runJson = signal('');
  readonly columns = ['code', 'name', 'status', 'actions'];

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.api.listScenarios().subscribe({
      next: (page) => {
        this.rows.set(page.items);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  calculate(id: string): void {
    this.api.calculateScenario(id).subscribe({
      next: (run) => {
        this.runJson.set(JSON.stringify(run, null, 2));
        this.reload();
      },
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-decision-support',
  standalone: true,
  imports: [MatProgressSpinnerModule],
  template: `
    <section class="page">
      <h1 class="page-title">Decision Support</h1>
      <p class="page-subtitle">Rule-based recommendations from real inventory metrics.</p>
      @if (loading()) {
        <mat-spinner diameter="36" />
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else if (rows().length === 0) {
        <p>No recommendations for the current inventory.</p>
      } @else {
        @for (row of rows(); track row.code) {
          <article class="surface-card rec">
            <h2>{{ row.title }}</h2>
            <p>{{ row.description }}</p>
            <small>{{ row.priority }} · {{ row.recommendationType }}</small>
          </article>
        }
      }
    </section>
  `,
  styles: `
    .rec {
      margin-bottom: 1rem;
    }
    .rec h2 {
      margin-top: 0;
      font-family: var(--et-font-display);
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class DecisionSupportComponent implements OnInit {
  private readonly api = inject(AnalyticsService);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly rows = signal<Recommendation[]>([]);

  ngOnInit(): void {
    this.api.decisionSupport().subscribe({
      next: (rows) => {
        this.rows.set(rows);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-report-center',
  standalone: true,
  imports: [MatButtonModule],
  template: `
    <section class="page">
      <h1 class="page-title">Reporting</h1>
      <p class="page-subtitle">JSON preview via API; download filtered CSV exports here.</p>
      <div class="actions">
        <button mat-stroked-button type="button" (click)="download('executive')">
          Executive CSV
        </button>
        <button mat-stroked-button type="button" (click)="download('inventory-summary')">
          Inventory summary CSV
        </button>
        <button mat-stroked-button type="button" (click)="download('target-progress')">
          Target progress CSV
        </button>
        <button mat-stroked-button type="button" (click)="download('scenario-comparison')">
          Scenario comparison CSV
        </button>
      </div>
      @if (message()) {
        <p>{{ message() }}</p>
      }
    </section>
  `,
  styles: `
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
    }
  `,
})
export class ReportCenterComponent {
  private readonly api = inject(AnalyticsService);
  readonly message = signal<string | null>(null);

  download(path: string): void {
    this.api.downloadReport(path).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ecotrace-${path}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.message.set(`Downloaded ${path}.csv`);
      },
      error: (err) => this.message.set(extractApiErrorMessage(err)),
    });
  }
}
