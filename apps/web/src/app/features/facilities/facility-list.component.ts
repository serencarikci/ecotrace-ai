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
import { FacilityService } from '../../core/services/facility.service';
import { AuthService } from '../../core/services/auth.service';
import { Facility, FACILITY_TYPES } from '../../core/models/facility.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-facility-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './facility-list.component.html',
  styleUrl: './facility-list.component.scss',
})
export class FacilityListComponent implements OnInit {
  private readonly api = inject(FacilityService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  readonly facilities = signal<Facility[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canManage = canManageStructure(this.auth.currentRoles());
  readonly facilityTypes = FACILITY_TYPES;
  readonly displayedColumns = ['code', 'name', 'facilityType', 'city', 'status', 'actions'];

  readonly filters = this.fb.nonNullable.group({
    search: [''],
    facilityType: [''],
    isActive: [''],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    const f = this.filters.getRawValue();
    this.api
      .list({
        page: this.page(),
        pageSize: this.pageSize(),
        search: f.search || undefined,
        facilityType: f.facilityType || undefined,
        isActive: f.isActive === '' ? undefined : f.isActive === 'true',
      })
      .subscribe({
        next: (result) => {
          this.facilities.set(result.items);
          this.totalItems.set(result.totalItems);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }

  applyFilters(): void {
    this.page.set(1);
    this.load();
  }

  onPage(event: PageEvent): void {
    this.page.set(event.pageIndex + 1);
    this.pageSize.set(event.pageSize);
    this.load();
  }

  archive(facility: Facility): void {
    if (!confirm(`Archive facility ${facility.name}?`)) {
      return;
    }
    this.api.archive(facility.id).subscribe({
      next: () => this.load(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
