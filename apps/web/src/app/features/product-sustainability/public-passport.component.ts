import { JsonPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';
import {
  ProductSustainabilityService,
  PublicPassport,
} from '../../core/services/product-sustainability.service';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-public-passport',
  standalone: true,
  imports: [RouterLink, JsonPipe],
  template: `
    <main class="public">
      @if (loading()) {
        <p>Loading passport…</p>
      } @else if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      } @else if (passport()) {
        <header>
          <p class="brand">EcoTrace AI</p>
          <h1>{{ passport()!.product['name'] || passport()!.title }}</h1>
          <p>Non-certified Digital Product Passport · {{ passport()!.status }}</p>
        </header>
        @if (passport()!.status === 'revoked') {
          <section class="banner revoked">This passport has been revoked.</section>
        }
        <section>
          <h2>Product identity</h2>
          <p>Category: {{ passport()!.product['productCategory'] || '—' }}</p>
          <p>Origin: {{ passport()!.product['countryOfOrigin'] || '—' }}</p>
          <p>Manufacturer: {{ passport()!.manufacturer['organizationName'] || '—' }}</p>
        </section>
        <section>
          <h2>Indicators</h2>
          <p>Recycled content: {{ passport()!.product['recycledContentPercentage'] || '—' }}%</p>
          <p>Recyclability: {{ passport()!.product['recyclabilityPercentage'] || '—' }}%</p>
          <p>Repairability (1–10): {{ passport()!.product['repairabilityScore'] ?? '—' }}</p>
        </section>
        @if (passport()!.carbonFootprint) {
          <section>
            <h2>Product carbon footprint estimate</h2>
            <p>
              {{ passport()!.carbonFootprint!['totalKgCO2e'] }} kgCO2e /
              {{ passport()!.carbonFootprint!['functionalUnitQuantity'] }}
              {{ passport()!.carbonFootprint!['functionalUnitCode'] }}
            </p>
          </section>
        }
        @for (section of passport()!.sections; track section['sectionCode']) {
          <section>
            <h2>{{ section['title'] }}</h2>
            <pre>{{ section['structuredData'] | json }}</pre>
          </section>
        }
        <section>
          <h2>QR</h2>
          @if (qrSvg()) {
            <div class="qr" [innerHTML]="qrSvg()"></div>
          }
          <p><a [routerLink]="['/passport', slug, 'documents']">Documents</a></p>
        </section>
        <footer>
          <p>Version {{ passport()!.version }} · {{ passport()!.publishedAt || '—' }}</p>
          <p class="disclaimer">{{ passport()!.disclaimer }}</p>
        </footer>
      }
    </main>
  `,
  styles: `
    .public {
      max-width: 720px;
      margin: 0 auto;
      padding: 1.5rem;
      min-height: 100vh;
      background: linear-gradient(180deg, #f3f7f4, #e7eee8);
      color: #1c2b22;
    }
    .brand {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.8rem;
      color: #3d5c4a;
    }
    h1 {
      font-family: var(--et-font-display, Georgia, serif);
      font-size: clamp(1.8rem, 4vw, 2.6rem);
    }
    section {
      padding: 1rem 0;
      border-bottom: 1px solid #c9d5cc;
    }
    .banner {
      background: #fff4d6;
      padding: 0.75rem 1rem;
      margin: 1rem 0;
    }
    .revoked {
      background: #f8d7da;
    }
    .disclaimer {
      color: #5a6b60;
      font-size: 0.9rem;
    }
    .qr {
      max-width: 180px;
    }
    pre {
      white-space: pre-wrap;
      font-size: 0.85rem;
    }
    .error {
      color: #8b1e1e;
    }
  `,
})
export class PublicPassportComponent implements OnInit {
  private readonly api = inject(ProductSustainabilityService);
  private readonly route = inject(ActivatedRoute);
  private readonly sanitizer = inject(DomSanitizer);
  readonly passport = signal<PublicPassport | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly qrSvg = signal<SafeHtml | null>(null);
  slug = '';

  ngOnInit(): void {
    this.slug = this.route.snapshot.paramMap.get('publicSlug') || '';
    this.api.getPublicPassport(this.slug).subscribe({
      next: (p) => {
        this.passport.set(p);
        this.loading.set(false);
        this.api.getPublicQr(this.slug).subscribe({
          next: (qr) => this.qrSvg.set(this.sanitizer.bypassSecurityTrustHtml(qr.svg)),
        });
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }
}
