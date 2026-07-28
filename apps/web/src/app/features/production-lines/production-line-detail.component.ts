import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { ProductionLineService } from '../../core/services/production-line.service';
import { AuthService } from '../../core/services/auth.service';
import { ProductionLine } from '../../core/models/production-line.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-production-line-detail',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="page">
      @if (errorMessage()) { <p class="error-text" role="alert">{{ errorMessage() }}</p> }
      @if (line(); as row) {
        <div class="header-row">
          <div>
            <h1 class="page-title">{{ row.name }}</h1>
            <p class="page-subtitle">{{ row.code }}</p>
          </div>
          <div class="actions-row">
            <a mat-stroked-button routerLink="/app/production-lines">Back</a>
            @if (canManage) {
              <a mat-flat-button color="primary" [routerLink]="['/app/production-lines', row.id, 'edit']">Edit</a>
            }
          </div>
        </div>
        <div class="surface-card">
          <dl class="detail-grid">
            <div><dt>Facility ID</dt><dd>{{ row.facilityId }}</dd></div>
            <div><dt>Category</dt><dd>{{ row.productionCategory || '—' }}</dd></div>
            <div><dt>Capacity</dt><dd>{{ row.capacityValue ?? '—' }} {{ row.capacityUnitCode || '' }}</dd></div>
            <div><dt>Status</dt><dd><span class="status-chip" [class.active]="row.isActive">{{ row.isActive ? 'Active' : 'Inactive' }}</span></dd></div>
          </dl>
          @if (row.description) { <p class="muted-note">{{ row.description }}</p> }
        </div>
      }
    </section>
  `,
})
export class ProductionLineDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ProductionLineService);
  private readonly auth = inject(AuthService);
  readonly line = signal<ProductionLine | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageStructure(this.auth.currentRoles());

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.api.get(id).subscribe({
      next: (line) => this.line.set(line),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
