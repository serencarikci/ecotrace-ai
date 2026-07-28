import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { EquipmentService } from '../../core/services/equipment.service';
import { AuthService } from '../../core/services/auth.service';
import { Equipment } from '../../core/models/equipment.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-equipment-detail',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="page">
      @if (errorMessage()) { <p class="error-text" role="alert">{{ errorMessage() }}</p> }
      @if (item(); as row) {
        <div class="header-row">
          <div><h1 class="page-title">{{ row.name }}</h1><p class="page-subtitle">{{ row.code }} · {{ row.equipmentType }}</p></div>
          <div class="actions-row">
            <a mat-stroked-button routerLink="/app/equipment">Back</a>
            @if (canManage) { <a mat-flat-button color="primary" [routerLink]="['/app/equipment', row.id, 'edit']">Edit</a> }
          </div>
        </div>
        <div class="surface-card">
          <dl class="detail-grid">
            <div><dt>Facility</dt><dd>{{ row.facilityId }}</dd></div>
            <div><dt>Production line</dt><dd>{{ row.productionLineId || '—' }}</dd></div>
            <div><dt>Manufacturer</dt><dd>{{ row.manufacturer || '—' }}</dd></div>
            <div><dt>Model</dt><dd>{{ row.model || '—' }}</dd></div>
            <div><dt>Serial</dt><dd>{{ row.serialNumber || '—' }}</dd></div>
            <div><dt>Status</dt><dd><span class="status-chip" [class.active]="row.isActive">{{ row.isActive ? 'Active' : 'Inactive' }}</span></dd></div>
          </dl>
        </div>
      }
    </section>
  `,
})
export class EquipmentDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(EquipmentService);
  private readonly auth = inject(AuthService);
  readonly item = signal<Equipment | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageStructure(this.auth.currentRoles());
  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.api.get(id).subscribe({ next: (item) => this.item.set(item), error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)) });
  }
}
