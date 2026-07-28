import { Component } from '@angular/core';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  template: `
    <section class="page">
      <h1 class="page-title">Dashboard</h1>
      <p class="page-subtitle">
        Platform overview for EcoTrace AI. Domain analytics are not available yet.
      </p>
      <div class="surface-card placeholder">
        <h2>Operational data and carbon accounting are available.</h2>
        <p>
          Manage facilities, equipment, reporting periods, activity records, CSV imports,
          emission factors, and carbon inventories. LCA, ESG indicators, and AI insights
          remain intentionally out of scope for now.
        </p>
      </div>
    </section>
  `,
  styles: `
    .placeholder h2 {
      font-family: var(--et-font-display);
      color: var(--et-forest-deep);
      margin-top: 0;
    }
    .placeholder p {
      color: var(--et-muted);
      max-width: 60ch;
      margin-bottom: 0;
    }
  `,
})
export class DashboardComponent {}
