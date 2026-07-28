import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="page center">
      <div class="surface-card">
        <h1 class="page-title">Page not found</h1>
        <p class="page-subtitle">The page you requested does not exist in EcoTrace AI.</p>
        <a mat-flat-button color="primary" routerLink="/app/dashboard">Go to dashboard</a>
      </div>
    </section>
  `,
  styles: `
    .center {
      display: grid;
      place-items: center;
      min-height: 60vh;
    }
  `,
})
export class NotFoundComponent {}
