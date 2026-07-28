import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ProductionLineService } from '../../core/services/production-line.service';
import { FacilityService } from '../../core/services/facility.service';
import { AuthService } from '../../core/services/auth.service';
import { ProductionLine } from '../../core/models/production-line.models';
import { Facility } from '../../core/models/facility.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-production-line-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './production-line-list.component.html',
})
export class ProductionLineListComponent implements OnInit {
  private readonly api = inject(ProductionLineService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly lines = signal<ProductionLine[]>([]);
  readonly facilities = signal<Facility[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageStructure(this.auth.currentRoles());
  readonly displayedColumns = ['code', 'name', 'capacity', 'status', 'actions'];
  readonly filters = this.fb.nonNullable.group({ facilityId: [''] });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100, isActive: true }).subscribe({
      next: (page) => {
        this.facilities.set(page.items);
        if (page.items[0]) {
          this.filters.controls.facilityId.setValue(page.items[0].id);
          this.load();
        }
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  load(): void {
    const facilityId = this.filters.controls.facilityId.value;
    if (!facilityId) {
      this.lines.set([]);
      return;
    }
    this.loading.set(true);
    this.errorMessage.set(null);
    this.api.listByFacility(facilityId).subscribe({
      next: (page) => {
        this.lines.set(page.items);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  archive(row: ProductionLine): void {
    if (!confirm(`Archive production line ${row.name}?`)) return;
    this.api.archive(row.id).subscribe({
      next: () => this.load(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
