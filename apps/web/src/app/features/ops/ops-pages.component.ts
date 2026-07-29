import { JsonPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { OpsApiService } from '../../core/services/ops-api.service';
import { extractApiErrorMessage } from '../../core/services/error.util';

const SHARED = [
  FormsModule,
  JsonPipe,
  RouterLink,
  MatButtonModule,
  MatFormFieldModule,
  MatInputModule,
  MatSelectModule,
  MatProgressSpinnerModule,
] as const;

function schedulePreview(expression: string): string {
  const map: Record<string, string> = {
    daily: 'Every day at 00:00 UTC (organization timezone applied when configured)',
    weekly: 'Every week (weekday from trigger config)',
    monthly: 'Every month on the configured day',
    quarterly: 'Every quarter',
    annual: 'Once per year',
  };
  if (map[expression]) return map[expression];
  if (expression.includes('*') || expression.split(' ').length >= 5) {
    return `Cron expression (validated server-side): ${expression}`;
  }
  return `Schedule: ${expression}`;
}

@Component({
  selector: 'app-automation-list',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Automation Rules</h1>
      <p class="page-subtitle">Organization-scoped workflows with idempotent execution.</p>
      <div class="actions">
        <a mat-flat-button color="primary" routerLink="/app/automation/new">New rule</a>
        <button mat-stroked-button type="button" (click)="load()">Refresh</button>
      </div>
      @if (error()) { <p class="error">{{ error() }}</p> }
      @if (loading()) { <mat-spinner diameter="32" /> }
      <ul class="list">
        @for (r of items(); track r.id) {
          <li class="surface-card">
            <a [routerLink]="['/app/automation', r.id]">{{ r.name }}</a>
            <span>{{ r.status }} · {{ r.triggerType }} · {{ r.actionType }}</span>
            <div class="row">
              <button mat-button type="button" (click)="activate(r.id)">Activate</button>
              <button mat-button type="button" (click)="pause(r.id)">Pause</button>
              <button mat-button type="button" (click)="run(r.id)">Run now</button>
              <a mat-button [routerLink]="['/app/automation', r.id, 'executions']">History</a>
            </div>
          </li>
        }
      </ul>
    </section>
  `,
  styles: `
    .list { list-style: none; padding: 0; display: grid; gap: 0.75rem; }
    .row { display: flex; flex-wrap: wrap; gap: 0.25rem; }
    .error { color: #8b1e1e; }
    .actions { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
  `,
})
export class AutomationListComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  readonly loading = signal(false);
  readonly error = signal('');
  ngOnInit() { this.load(); }
  load() {
    this.loading.set(true);
    this.api.listAutomationRules().subscribe({
      next: (rows) => { this.items.set(rows); this.loading.set(false); },
      error: (e) => { this.error.set(extractApiErrorMessage(e)); this.loading.set(false); },
    });
  }
  activate(id: string) { this.api.activateAutomation(id).subscribe({ next: () => this.load(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  pause(id: string) { this.api.pauseAutomation(id).subscribe({ next: () => this.load(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  run(id: string) { this.api.runAutomation(id).subscribe({ next: () => this.load(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
}

@Component({
  selector: 'app-automation-form',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">{{ id ? 'Automation detail' : 'New automation' }}</h1>
      @if (!id) {
        <mat-form-field appearance="outline">
          <mat-label>Template</mat-label>
          <mat-select [(ngModel)]="templateCode" (selectionChange)="applyTemplate()">
            @for (t of templates(); track t.code) {
              <mat-option [value]="t.code">{{ t.code }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <p class="preview">Schedule preview: {{ preview }}</p>
        <mat-form-field appearance="outline"><mat-label>Code</mat-label><input matInput [(ngModel)]="code" /></mat-form-field>
        <mat-form-field appearance="outline"><mat-label>Name</mat-label><input matInput [(ngModel)]="name" /></mat-form-field>
        <button mat-flat-button color="primary" type="button" (click)="create()">Create draft</button>
      } @else {
        @if (rule()) {
          <pre>{{ rule() | json }}</pre>
          <p class="preview">Schedule preview: {{ schedulePreview(rule()?.triggerConfig?.expression || rule()?.triggerType || '') }}</p>
        }
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </section>
  `,
  styles: `.preview { color: var(--et-muted); } .error { color: #8b1e1e; } mat-form-field { display:block; max-width: 28rem; }`,
})
export class AutomationFormComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly templates = signal<any[]>([]);
  readonly rule = signal<any>(null);
  readonly error = signal('');
  id = '';
  templateCode = 'weekly_anomaly_scan';
  code = '';
  name = '';
  preview = schedulePreview('weekly');
  schedulePreview = schedulePreview;
  ngOnInit() {
    this.id = this.route.snapshot.paramMap.get('id') || '';
    this.api.automationTemplates().subscribe({ next: (t) => this.templates.set(t) });
    if (this.id) {
      this.api.getAutomation(this.id).subscribe({
        next: (r) => this.rule.set(r),
        error: (e) => this.error.set(extractApiErrorMessage(e)),
      });
    }
  }
  applyTemplate() {
    const t = this.templates().find((x) => x.code === this.templateCode);
    this.preview = schedulePreview(t?.triggerConfig?.expression || t?.triggerType || 'custom');
  }
  create() {
    this.api.createAutomation({
      code: this.code || `rule-${Date.now()}`,
      name: this.name || this.templateCode,
      templateCode: this.templateCode,
    }).subscribe({
      next: (r) => (window.location.href = `/app/automation/${r.id}`),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
  }
}

@Component({
  selector: 'app-automation-executions',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Automation executions</h1>
      <a mat-button routerLink="/app/automation">Back</a>
      @if (error()) { <p class="error">{{ error() }}</p> }
      <pre>{{ items() | json }}</pre>
    </section>
  `,
})
export class AutomationExecutionsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly items = signal<any[]>([]);
  readonly error = signal('');
  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.automationExecutions(id).subscribe({
      next: (rows) => this.items.set(rows),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
  }
}

@Component({
  selector: 'app-agents-list',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">AI Agents</h1>
      <p class="page-subtitle">Allowlisted tools only. Write actions require approval.</p>
      <ul class="list">
        @for (a of agents(); track a.code) {
          <li class="surface-card">
            <a [routerLink]="['/app/agents', a.code]">{{ a.name }}</a>
            <p>{{ a.description }}</p>
          </li>
        }
      </ul>
      @if (error()) { <p class="error">{{ error() }}</p> }
    </section>
  `,
  styles: `.list { list-style:none; padding:0; display:grid; gap:.75rem; }`,
})
export class AgentsListComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly agents = signal<any[]>([]);
  readonly error = signal('');
  ngOnInit() {
    this.api.listAgents().subscribe({
      next: (rows) => this.agents.set(rows),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
  }
}

@Component({
  selector: 'app-agent-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">{{ agent()?.name || 'Agent' }}</h1>
      <p>{{ agent()?.description }}</p>
      <h2>Allowed tools</h2>
      <pre>{{ agent()?.allowedTools | json }}</pre>
      <mat-form-field appearance="outline" class="wide">
        <mat-label>Prompt</mat-label>
        <textarea matInput rows="4" [(ngModel)]="prompt"></textarea>
      </mat-form-field>
      <button mat-flat-button color="primary" type="button" (click)="run()">Execute</button>
      @if (result()) {
        <h2>Result</h2>
        <p>Status: {{ result()?.status }}</p>
        <p>Rationale: {{ result()?.rationale }}</p>
        <pre>{{ result()?.resultSummary | json }}</pre>
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </section>
  `,
  styles: `.wide { width: min(40rem, 100%); display:block; }`,
})
export class AgentDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly agent = signal<any>(null);
  readonly result = signal<any>(null);
  readonly error = signal('');
  prompt = 'Summarize current sustainability status using allowlisted tools.';
  ngOnInit() {
    const code = this.route.snapshot.paramMap.get('code')!;
    this.api.getAgent(code).subscribe({
      next: (a) => this.agent.set(a),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
  }
  run() {
    const code = this.route.snapshot.paramMap.get('code')!;
    this.api.executeAgent(code, this.prompt).subscribe({
      next: (r) => this.result.set(r),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
  }
}

@Component({
  selector: 'app-agent-executions',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Agent executions</h1>
      <ul>
        @for (e of items(); track e.id) {
          <li><a [routerLink]="['/app/agent-executions', e.id]">{{ e.agentCode }} · {{ e.status }}</a></li>
        }
      </ul>
    </section>
  `,
})
export class AgentExecutionsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.listExecutions().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-agent-execution-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Execution</h1>
      <p>No hidden chain-of-thought is exposed. Auditable rationale only.</p>
      <pre>{{ item() | json }}</pre>
    </section>
  `,
})
export class AgentExecutionDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly item = signal<any>(null);
  ngOnInit() {
    this.api.getExecution(this.route.snapshot.paramMap.get('id')!).subscribe({ next: (r) => this.item.set(r) });
  }
}

@Component({
  selector: 'app-agent-approvals',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Agent Approvals</h1>
      <p class="page-subtitle">Write actions never execute before approval.</p>
      @for (r of items(); track r.id) {
        <article class="surface-card">
          <h2>{{ r.title }}</h2>
          <p>Risk: {{ r.riskLevel }} · Status: {{ r.status }}</p>
          <pre>{{ r.proposedChanges | json }}</pre>
          @if (r.status === 'pending') {
            <button mat-flat-button color="primary" type="button" (click)="approve(r.id)">Approve</button>
            <button mat-stroked-button type="button" (click)="reject(r.id)">Reject</button>
          }
          @if (r.status === 'approved') {
            <button mat-flat-button type="button" (click)="execute(r.id)">Execute approved action</button>
          }
        </article>
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </section>
  `,
})
export class AgentApprovalsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  readonly error = signal('');
  ngOnInit() { this.reload(); }
  reload() { this.api.listActionRequests().subscribe({ next: (r) => this.items.set(r), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  approve(id: string) { this.api.approveAction(id).subscribe({ next: () => this.reload(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  reject(id: string) { this.api.rejectAction(id, 'Rejected in UI').subscribe({ next: () => this.reload(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  execute(id: string) { this.api.executeAction(id).subscribe({ next: () => this.reload(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
}

@Component({
  selector: 'app-anomalies',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Anomalies</h1>
      <p class="disclaimer">A statistical anomaly is not automatically an error.</p>
      <a mat-button routerLink="/app/anomaly-rules">Rules</a>
      <ul>
        @for (a of items(); track a.id) {
          <li><a [routerLink]="['/app/anomalies', a.id]">{{ a.metricCode || a.title || a.id }} · {{ a.severity }} · {{ a.status }}</a></li>
        }
      </ul>
    </section>
  `,
  styles: `.disclaimer { color: var(--et-muted); }`,
})
export class AnomaliesComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.listAnomalies().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-anomaly-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Anomaly detail</h1>
      <p class="disclaimer">Detection method and thresholds are informative; investigate before changing source records.</p>
      <pre>{{ item() | json }}</pre>
      <button mat-button type="button" (click)="ack()">Acknowledge</button>
      <button mat-button type="button" (click)="resolve()">Resolve</button>
      <button mat-button type="button" (click)="dismiss()">Dismiss</button>
      @if (error()) { <p class="error">{{ error() }}</p> }
    </section>
  `,
})
export class AnomalyDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly item = signal<any>(null);
  readonly error = signal('');
  ngOnInit() { this.reload(); }
  reload() {
    this.api.getAnomaly(this.route.snapshot.paramMap.get('id')!).subscribe({ next: (r) => this.item.set(r) });
  }
  ack() { this.api.acknowledgeAnomaly(this.route.snapshot.paramMap.get('id')!).subscribe({ next: () => this.reload(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  resolve() { this.api.resolveAnomaly(this.route.snapshot.paramMap.get('id')!, 'Resolved after review').subscribe({ next: () => this.reload(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
  dismiss() { this.api.dismissAnomaly(this.route.snapshot.paramMap.get('id')!, 'False positive after review').subscribe({ next: () => this.reload(), error: (e) => this.error.set(extractApiErrorMessage(e)) }); }
}

@Component({
  selector: 'app-anomaly-rules',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Anomaly rules</h1>
      @for (r of items(); track r.id) {
        <div class="surface-card">
          <strong>{{ r.name }}</strong> · {{ r.detectionMethod }}
          <button mat-button type="button" (click)="run(r.id)">Run</button>
        </div>
      }
    </section>
  `,
})
export class AnomalyRulesComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.listAnomalyRules().subscribe({ next: (r) => this.items.set(r) }); }
  run(id: string) { this.api.runAnomalyRule(id).subscribe(); }
}

@Component({
  selector: 'app-forecasts',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Forecasts</h1>
      <p class="disclaimer">Forecasts are model-based estimates, not guarantees.</p>
      <a mat-flat-button color="primary" routerLink="/app/forecasts/new">New forecast</a>
      <ul>
        @for (f of items(); track f.id) {
          <li>
            <a [routerLink]="['/app/forecasts', f.id]">{{ f.name }}</a>
            · {{ f.method }}
            <a mat-button [routerLink]="['/app/forecasts', f.id, 'results']">Results</a>
          </li>
        }
      </ul>
    </section>
  `,
})
export class ForecastsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.listForecasts().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-forecast-form',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">{{ id ? 'Forecast' : 'New forecast' }}</h1>
      @if (!id) {
        <mat-form-field appearance="outline"><mat-label>Code</mat-label><input matInput [(ngModel)]="code" /></mat-form-field>
        <mat-form-field appearance="outline"><mat-label>Name</mat-label><input matInput [(ngModel)]="name" /></mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Method</mat-label>
          <mat-select [(ngModel)]="method">
            <mat-option value="linear_trend">Linear trend</mat-option>
            <mat-option value="moving_average">Moving average</mat-option>
            <mat-option value="seasonal_naive">Seasonal naive</mat-option>
            <mat-option value="simple_exponential_smoothing">SES</mat-option>
          </mat-select>
        </mat-form-field>
        <button mat-flat-button color="primary" type="button" (click)="create()">Create</button>
      } @else {
        <pre>{{ item() | json }}</pre>
        <button mat-flat-button type="button" (click)="run()">Run (with backtest)</button>
        @if (runResult()) { <pre>{{ runResult() | json }}</pre> }
        @if (insufficient()) { <p class="disclaimer">Insufficient historical data for a reliable forecast.</p> }
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </section>
  `,
})
export class ForecastFormComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  id = '';
  code = '';
  name = '';
  method = 'linear_trend';
  readonly item = signal<any>(null);
  readonly runResult = signal<any>(null);
  readonly error = signal('');
  readonly insufficient = signal(false);
  ngOnInit() {
    this.id = this.route.snapshot.paramMap.get('id') || '';
    if (this.id) this.api.getForecast(this.id).subscribe({ next: (r) => this.item.set(r) });
  }
  create() {
    this.api.createForecast({ code: this.code, name: this.name, method: this.method, metricType: 'total_emissions' }).subscribe({
      next: (r) => (window.location.href = `/app/forecasts/${r.id}`),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
  }
  run() {
    this.insufficient.set(false);
    this.api.runForecast(this.id).subscribe({
      next: (r) => this.runResult.set(r),
      error: (e) => {
        const msg = extractApiErrorMessage(e);
        this.error.set(msg);
        if (msg.toLowerCase().includes('insufficient')) this.insufficient.set(true);
      },
    });
  }
}

@Component({
  selector: 'app-forecast-results',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Forecast results</h1>
      <p class="disclaimer">Estimates only. Confidence bands shown when supported by the method.</p>
      <h2>Runs</h2>
      <pre>{{ runs() | json }}</pre>
      <h2>Points</h2>
      <pre>{{ points() | json }}</pre>
      <h2>Target trajectory</h2>
      <pre>{{ trajectory() | json }}</pre>
    </section>
  `,
})
export class ForecastResultsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly runs = signal<any[]>([]);
  readonly points = signal<any[]>([]);
  readonly trajectory = signal<any[]>([]);
  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.forecastRuns(id).subscribe({
      next: (runs) => {
        this.runs.set(runs);
        if (runs[0]?.id) this.api.forecastPoints(runs[0].id).subscribe({ next: (p) => this.points.set(p) });
      },
    });
    this.api.targetTrajectory().subscribe({ next: (t) => this.trajectory.set(t) });
  }
}

@Component({
  selector: 'app-data-quality',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Data quality</h1>
      <button mat-flat-button color="primary" type="button" (click)="scan()">Scan now</button>
      <ul>
        @for (i of items(); track i.id) {
          <li><a [routerLink]="['/app/data-quality', i.id]">{{ i.title }} · {{ i.severity }} · {{ i.status }}</a></li>
        }
      </ul>
    </section>
  `,
})
export class DataQualityComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.reload(); }
  reload() { this.api.dqIssues().subscribe({ next: (r) => this.items.set(r) }); }
  scan() { this.api.dqScan().subscribe({ next: () => this.reload() }); }
}

@Component({
  selector: 'app-data-quality-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Issue</h1>
      <pre>{{ item() | json }}</pre>
      <button mat-button type="button" (click)="resolve()">Resolve</button>
    </section>
  `,
})
export class DataQualityDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly item = signal<any>(null);
  ngOnInit() { this.api.dqIssue(this.route.snapshot.paramMap.get('id')!).subscribe({ next: (r) => this.item.set(r) }); }
  resolve() { this.api.dqResolve(this.route.snapshot.paramMap.get('id')!, 'Resolved').subscribe({ next: (r) => this.item.set(r) }); }
}

@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Alerts</h1>
      <ul>
        @for (a of items(); track a.id) {
          <li><a [routerLink]="['/app/alerts', a.id]">{{ a.title }} · {{ a.severity }} · {{ a.status }}</a></li>
        }
      </ul>
    </section>
  `,
})
export class AlertsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.listAlerts().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-alert-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Alert</h1>
      <pre>{{ item() | json }}</pre>
      <button mat-button type="button" (click)="ack()">Acknowledge</button>
      <button mat-button type="button" (click)="resolve()">Resolve</button>
    </section>
  `,
})
export class AlertDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly item = signal<any>(null);
  ngOnInit() { this.reload(); }
  reload() { this.api.getAlert(this.route.snapshot.paramMap.get('id')!).subscribe({ next: (r) => this.item.set(r) }); }
  ack() { this.api.ackAlert(this.route.snapshot.paramMap.get('id')!).subscribe({ next: () => this.reload() }); }
  resolve() { this.api.resolveAlert(this.route.snapshot.paramMap.get('id')!).subscribe({ next: () => this.reload() }); }
}

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Notifications</h1>
      <button mat-button type="button" (click)="readAll()">Mark all read</button>
      <a mat-button routerLink="/app/notification-settings">Settings</a>
      <ul>
        @for (n of items(); track n.id) {
          <li>{{ n.title }} · {{ n.status }} <button mat-button type="button" (click)="read(n.id)">Read</button></li>
        }
      </ul>
    </section>
  `,
})
export class NotificationsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.reload(); }
  reload() { this.api.notifications().subscribe({ next: (r) => this.items.set(r) }); }
  read(id: string) { this.api.markRead(id).subscribe({ next: () => this.reload() }); }
  readAll() { this.api.markAllRead().subscribe({ next: () => this.reload() }); }
}

@Component({
  selector: 'app-notification-settings',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Notification settings</h1>
      <pre>{{ prefs() | json }}</pre>
      <mat-form-field appearance="outline">
        <mat-label>Minimum severity</mat-label>
        <mat-select [(ngModel)]="minSeverity">
          <mat-option value="info">info</mat-option>
          <mat-option value="low">low</mat-option>
          <mat-option value="medium">medium</mat-option>
          <mat-option value="high">high</mat-option>
        </mat-select>
      </mat-form-field>
      <button mat-flat-button type="button" (click)="save()">Save</button>
    </section>
  `,
})
export class NotificationSettingsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly prefs = signal<any>(null);
  minSeverity = 'medium';
  ngOnInit() { this.api.getPrefs().subscribe({ next: (p) => { this.prefs.set(p); this.minSeverity = p?.minimumSeverity || 'medium'; } }); }
  save() { this.api.updatePrefs({ minimumSeverity: this.minSeverity }).subscribe({ next: (p) => this.prefs.set(p) }); }
}

@Component({
  selector: 'app-scheduled-reports',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Scheduled reports</h1>
      <a mat-flat-button color="primary" routerLink="/app/scheduled-reports/new">New</a>
      <a mat-button routerLink="/app/generated-reports">Generated</a>
      <ul>
        @for (r of items(); track r.id) {
          <li>
            <a [routerLink]="['/app/scheduled-reports', r.id]">{{ r.name }}</a>
            · next {{ r.nextGenerationAt || 'n/a' }}
            <button mat-button type="button" (click)="run(r.id)">Run</button>
          </li>
        }
      </ul>
    </section>
  `,
})
export class ScheduledReportsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.reload(); }
  reload() { this.api.scheduledReports().subscribe({ next: (r) => this.items.set(r) }); }
  run(id: string) { this.api.runScheduled(id).subscribe({ next: () => this.reload() }); }
}

@Component({
  selector: 'app-scheduled-report-form',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">{{ id ? 'Scheduled report' : 'New scheduled report' }}</h1>
      @if (!id) {
        <mat-form-field appearance="outline"><mat-label>Code</mat-label><input matInput [(ngModel)]="code" /></mat-form-field>
        <mat-form-field appearance="outline"><mat-label>Name</mat-label><input matInput [(ngModel)]="name" /></mat-form-field>
        <p class="preview">{{ schedulePreview('monthly') }}</p>
        <button mat-flat-button color="primary" type="button" (click)="create()">Create</button>
      } @else {
        <pre>{{ item() | json }}</pre>
        <button mat-button type="button" (click)="activate()">Activate</button>
        <button mat-button type="button" (click)="pause()">Pause</button>
        <button mat-button type="button" (click)="run()">Run now</button>
      }
    </section>
  `,
})
export class ScheduledReportFormComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  schedulePreview = schedulePreview;
  id = '';
  code = '';
  name = '';
  readonly item = signal<any>(null);
  ngOnInit() {
    this.id = this.route.snapshot.paramMap.get('id') || '';
    if (this.id) this.api.getScheduledReport(this.id).subscribe({ next: (r) => this.item.set(r) });
  }
  create() {
    this.api.createScheduledReport({ code: this.code, name: this.name, scheduleExpression: 'monthly', outputFormat: 'json' }).subscribe({
      next: (r) => (window.location.href = `/app/scheduled-reports/${r.id}`),
    });
  }
  activate() { this.api.activateScheduled(this.id).subscribe({ next: (r) => this.item.set(r) }); }
  pause() { this.api.pauseScheduled(this.id).subscribe({ next: (r) => this.item.set(r) }); }
  run() { this.api.runScheduled(this.id).subscribe({ next: (r) => this.item.set(r) }); }
}

@Component({
  selector: 'app-generated-reports',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Generated reports</h1>
      <ul>
        @for (r of items(); track r.id) {
          <li><a [routerLink]="['/app/generated-reports', r.id]">{{ r.title }} · {{ r.status }} · {{ r.checksum?.slice?.(0,12) }}</a></li>
        }
      </ul>
    </section>
  `,
})
export class GeneratedReportsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.generatedReports().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-generated-report-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Generated report</h1>
      <pre>{{ item() | json }}</pre>
      <button mat-flat-button type="button" (click)="download()">Download</button>
    </section>
  `,
})
export class GeneratedReportDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly item = signal<any>(null);
  ngOnInit() { this.api.getGenerated(this.route.snapshot.paramMap.get('id')!).subscribe({ next: (r) => this.item.set(r) }); }
  download() {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.downloadGenerated(id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report-${id}`;
        a.click();
        URL.revokeObjectURL(url);
      },
    });
  }
}

@Component({
  selector: 'app-supplier-monitoring',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Supplier monitoring</h1>
      <p class="disclaimer">Scores are internal and non-certified.</p>
      <ul>
        @for (s of items(); track s.supplierId || s.id) {
          <li><a [routerLink]="['/app/supplier-monitoring', s.supplierId || s.id]">{{ s.supplierName || s.supplierId }} · risk {{ s.riskLevel }}</a></li>
        }
      </ul>
    </section>
  `,
})
export class SupplierMonitoringComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.supplierMonitoring().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-supplier-monitoring-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Supplier profile</h1>
      <p class="disclaimer">Internal non-certified assessment for decision support only.</p>
      <pre>{{ profile() | json }}</pre>
      <button mat-flat-button type="button" (click)="assess()">Run assessment</button>
      <h2>Assessments</h2>
      <pre>{{ assessments() | json }}</pre>
    </section>
  `,
})
export class SupplierMonitoringDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly profile = signal<any>(null);
  readonly assessments = signal<any[]>([]);
  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('supplierId')!;
    this.api.supplierProfile(id).subscribe({ next: (r) => this.profile.set(r) });
    this.api.supplierAssessments(id).subscribe({ next: (r) => this.assessments.set(r) });
  }
  assess() {
    const id = this.route.snapshot.paramMap.get('supplierId')!;
    this.api.assessSupplier(id).subscribe({ next: () => this.api.supplierAssessments(id).subscribe({ next: (r) => this.assessments.set(r) }) });
  }
}

const REG_DISCLAIMER =
  'This module provides document intelligence and internal decision support. It does not provide legal advice or guarantee regulatory compliance.';

@Component({
  selector: 'app-regulatory',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Regulatory intelligence</h1>
      <p class="disclaimer">{{ disclaimer }}</p>
      <a mat-button routerLink="/app/regulatory-assessments">Assessments</a>
      <ul>
        @for (d of items(); track d.id) {
          <li><a [routerLink]="['/app/regulatory-intelligence', d.id]">{{ d.title }} · {{ d.jurisdictionCode }}</a></li>
        }
      </ul>
    </section>
  `,
})
export class RegulatoryListComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly disclaimer = REG_DISCLAIMER;
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.regulatoryDocs().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-regulatory-detail',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Regulatory document</h1>
      <p class="disclaimer">{{ disclaimer }}</p>
      <pre>{{ item() | json }}</pre>
    </section>
  `,
})
export class RegulatoryDetailComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  private readonly route = inject(ActivatedRoute);
  readonly disclaimer = REG_DISCLAIMER;
  readonly item = signal<any>(null);
  ngOnInit() { this.api.regulatoryDoc(this.route.snapshot.paramMap.get('id')!).subscribe({ next: (r) => this.item.set(r) }); }
}

@Component({
  selector: 'app-regulatory-assessments',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Regulatory assessments</h1>
      <p class="disclaimer">{{ disclaimer }}</p>
      <button mat-flat-button type="button" (click)="scan()">Scan applicability</button>
      @for (a of items(); track a.id) {
        <article class="surface-card">
          <pre>{{ a | json }}</pre>
          <button mat-button type="button" (click)="review(a.id, 'applicable')">Mark applicable</button>
          <button mat-button type="button" (click)="review(a.id, 'not_applicable')">Not applicable</button>
        </article>
      }
    </section>
  `,
})
export class RegulatoryAssessmentsComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly disclaimer = REG_DISCLAIMER;
  readonly items = signal<any[]>([]);
  ngOnInit() { this.reload(); }
  reload() { this.api.regulatoryAssessments().subscribe({ next: (r) => this.items.set(r) }); }
  scan() { this.api.scanRegulatory().subscribe({ next: () => this.reload() }); }
  review(id: string, status: string) { this.api.reviewAssessment(id, status, 'Reviewed in UI').subscribe({ next: () => this.reload() }); }
}

@Component({
  selector: 'app-job-monitoring',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Job monitoring</h1>
      <pre>{{ items() | json }}</pre>
    </section>
  `,
})
export class JobMonitoringComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly items = signal<any[]>([]);
  ngOnInit() { this.api.listJobs().subscribe({ next: (r) => this.items.set(r) }); }
}

@Component({
  selector: 'app-system-health',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">System health</h1>
      <button mat-button type="button" (click)="load()">Refresh</button>
      @if (error()) { <p class="error">{{ error() }}</p> }
      <pre>{{ health() | json }}</pre>
      <pre>{{ version() | json }}</pre>
    </section>
  `,
})
export class SystemHealthComponent implements OnInit {
  private readonly api = inject(OpsApiService);
  readonly health = signal<any>(null);
  readonly version = signal<any>(null);
  readonly error = signal('');
  ngOnInit() { this.load(); }
  load() {
    this.api.systemHealth().subscribe({
      next: (h) => this.health.set(h),
      error: (e) => this.error.set(extractApiErrorMessage(e)),
    });
    this.api.systemVersion().subscribe({ next: (v) => this.version.set(v), error: () => undefined });
  }
}

@Component({
  selector: 'app-system-operations',
  standalone: true,
  imports: [...SHARED],
  template: `
    <section class="page">
      <h1 class="page-title">Operations</h1>
      <p>Use Health for dependency checks and Job Monitoring for failed executions.</p>
      <a mat-button routerLink="/app/system/health">Health</a>
      <a mat-button routerLink="/app/system/job-monitoring">Jobs</a>
    </section>
  `,
})
export class SystemOperationsComponent {}

export { schedulePreview, REG_DISCLAIMER };
