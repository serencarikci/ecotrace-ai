import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EquipmentService } from '../../core/services/equipment.service';
import { FacilityService } from '../../core/services/facility.service';
import { AuthService } from '../../core/services/auth.service';
import { Equipment, EQUIPMENT_TYPES } from '../../core/models/equipment.models';
import { Facility } from '../../core/models/facility.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-equipment-list',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, MatTableModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatPaginatorModule, MatProgressSpinnerModule],
  templateUrl: './equipment-list.component.html',
})
export class EquipmentListComponent implements OnInit {
  private readonly api = inject(EquipmentService);
  private readonly facilitiesApi = inject(FacilityService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<Equipment[]>([]);
  readonly facilities = signal<Facility[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canManage = canManageStructure(this.auth.currentRoles());
  readonly equipmentTypes = EQUIPMENT_TYPES;
  readonly displayedColumns = ['code', 'name', 'equipmentType', 'manufacturer', 'status', 'actions'];
  readonly filters = this.fb.nonNullable.group({ search: [''], facilityId: [''], equipmentType: [''], isActive: [''] });

  ngOnInit(): void {
    this.facilitiesApi.list({ page: 1, pageSize: 100 }).subscribe({ next: (p) => this.facilities.set(p.items) });
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    const f = this.filters.getRawValue();
    this.api.list({
      page: this.page(), pageSize: this.pageSize(), search: f.search || undefined,
      facilityId: f.facilityId || undefined, equipmentType: f.equipmentType || undefined,
      isActive: f.isActive === '' ? undefined : f.isActive === 'true',
    }).subscribe({
      next: (r) => { this.items.set(r.items); this.totalItems.set(r.totalItems); this.loading.set(false); },
      error: (err: unknown) => { this.loading.set(false); this.errorMessage.set(extractApiErrorMessage(err)); },
    });
  }

  applyFilters(): void { this.page.set(1); this.load(); }
  onPage(e: PageEvent): void { this.page.set(e.pageIndex + 1); this.pageSize.set(e.pageSize); this.load(); }
  archive(row: Equipment): void {
    if (!confirm(`Archive equipment ${row.name}?`)) return;
    this.api.archive(row.id).subscribe({ next: () => this.load(), error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)) });
  }
}
