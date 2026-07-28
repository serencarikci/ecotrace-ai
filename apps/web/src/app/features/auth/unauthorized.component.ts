import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="page center">
      <div class="surface-card">
        <h1 class="page-title">Unauthorized</h1>
        <p class="page-subtitle">You do not have permission to access this resource.</p>
        <a mat-flat-button color="primary" routerLink="/app/dashboard">Back to dashboard</a>
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
export class UnauthorizedComponent {}
