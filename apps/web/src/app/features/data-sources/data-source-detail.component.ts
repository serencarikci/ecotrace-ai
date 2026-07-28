import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { DataSourceService } from '../../core/services/data-source.service';
import { AuthService } from '../../core/services/auth.service';
import { DataSource, LIVE_INTEGRATION_SOURCE_TYPES } from '../../core/models/data-source.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-data-source-detail',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="page">
      @if (errorMessage()) { <p class="error-text" role="alert">{{ errorMessage() }}</p> }
      @if (item(); as row) {
        <div class="header-row">
          <div><h1 class="page-title">{{ row.name }}</h1><p class="page-subtitle">{{ row.code }} · {{ row.sourceType }}</p></div>
          <div class="actions-row">
            <a mat-stroked-button routerLink="/app/data-sources">Back</a>
            @if (canManage) { <a mat-flat-button color="primary" [routerLink]="['/app/data-sources', row.id, 'edit']">Edit</a> }
          </div>
        </div>
        <div class="surface-card">
          <dl class="detail-grid">
            <div><dt>Status</dt><dd><span class="status-chip" [class.active]="row.isActive">{{ row.isActive ? 'Active' : 'Inactive' }}</span></dd></div>
            <div><dt>Facility</dt><dd>{{ row.facilityId || '—' }}</dd></div>
            <div><dt>Equipment</dt><dd>{{ row.equipmentId || '—' }}</dd></div>
            <div><dt>External reference</dt><dd>{{ row.externalReference || '—' }}</dd></div>
          </dl>
          @if (isLive) { <p class="muted-note">Integration is planned for a later phase.</p> }
          @if (row.description) { <p class="muted-note">{{ row.description }}</p> }
        </div>
      }
    </section>
  `,
})
export class DataSourceDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(DataSourceService);
  private readonly auth = inject(AuthService);
  readonly item = signal<DataSource | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageStructure(this.auth.currentRoles());
  isLive = false;
  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.api.get(id).subscribe({
      next: (item) => { this.item.set(item); this.isLive = LIVE_INTEGRATION_SOURCE_TYPES.includes(item.sourceType as never); },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
