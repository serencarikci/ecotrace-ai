import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink],
  template: `
    <section class="page dashboard">
      <header class="hero">
        <p class="eyebrow">EcoTrace AI</p>
        <h1 class="page-title">Command center for sustainability work</h1>
        <p class="page-subtitle">
          Move from activity data to carbon inventories, product LCA, grounded AI answers, and
          automation — without leaving the system of record.
        </p>
      </header>

      <div class="lanes">
        @for (lane of lanes; track lane.title; let i = $index) {
          <a class="lane" [routerLink]="lane.link" [style.animation-delay]="0.08 * (i + 1) + 's'">
            <span class="lane-kicker">{{ lane.kicker }}</span>
            <strong>{{ lane.title }}</strong>
            <span>{{ lane.blurb }}</span>
          </a>
        }
      </div>
    </section>
  `,
  styles: `
    .dashboard .hero {
      margin-bottom: 0.25rem;
    }

    .eyebrow {
      margin: 0 0 0.55rem;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--et-moss);
    }

    .lanes {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
    }

    .lane {
      display: grid;
      gap: 0.45rem;
      padding: 1.25rem 1.2rem;
      border-radius: var(--et-radius);
      border: 1px solid var(--et-border);
      background:
        linear-gradient(165deg, rgba(255, 255, 255, 0.92), rgba(238, 244, 240, 0.85));
      box-shadow: var(--et-shadow-soft);
      color: inherit;
      transition:
        transform 0.22s ease,
        box-shadow 0.22s ease,
        border-color 0.22s ease;
      animation: et-rise 0.45s ease-out both;
    }

    .lane:hover {
      transform: translateY(-3px);
      border-color: rgba(45, 106, 79, 0.35);
      box-shadow: var(--et-shadow);
    }

    .lane-kicker {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--et-moss);
    }

    .lane strong {
      font-size: 1.05rem;
      letter-spacing: -0.02em;
      color: var(--et-forest-deep);
    }

    .lane span:last-child {
      color: var(--et-muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }
  `,
})
export class DashboardComponent {
  readonly lanes = [
    {
      kicker: 'Operations',
      title: 'Facilities & activity data',
      blurb: 'Sites, assets, periods, and auditable activity records.',
      link: '/app/facilities',
    },
    {
      kicker: 'Carbon',
      title: 'Inventories & factors',
      blurb: 'Calculate, review, and snapshot organizational emissions.',
      link: '/app/carbon-inventories',
    },
    {
      kicker: 'Products',
      title: 'LCA & passports',
      blurb: 'BOM-driven footprints and Digital Product Passports.',
      link: '/app/products',
    },
    {
      kicker: 'Intelligence',
      title: 'AI, agents & forecasts',
      blurb: 'Grounded Copilot, anomalies, automation, and ops alerts.',
      link: '/app/ai',
    },
  ];
}
