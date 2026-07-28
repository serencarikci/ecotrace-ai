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
import { DataSourceService } from '../../core/services/data-source.service';
import { AuthService } from '../../core/services/auth.service';
import { DataSource, DATA_SOURCE_TYPES } from '../../core/models/data-source.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-data-source-list',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, MatTableModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatPaginatorModule, MatProgressSpinnerModule],
  templateUrl: './data-source-list.component.html',
})
export class DataSourceListComponent implements OnInit {
  private readonly api = inject(DataSourceService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  readonly items = signal<DataSource[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canManage = canManageStructure(this.auth.currentRoles());
  readonly sourceTypes = DATA_SOURCE_TYPES;
  readonly displayedColumns = ['code', 'name', 'sourceType', 'status', 'actions'];
  readonly filters = this.fb.nonNullable.group({ search: [''], sourceType: [''], isActive: [''] });

  ngOnInit(): void { this.load(); }
  load(): void {
    this.loading.set(true); this.errorMessage.set(null);
    const f = this.filters.getRawValue();
    this.api.list({
      page: this.page(), pageSize: this.pageSize(), search: f.search || undefined,
      sourceType: f.sourceType || undefined, isActive: f.isActive === '' ? undefined : f.isActive === 'true',
    }).subscribe({
      next: (r) => { this.items.set(r.items); this.totalItems.set(r.totalItems); this.loading.set(false); },
      error: (err: unknown) => { this.loading.set(false); this.errorMessage.set(extractApiErrorMessage(err)); },
    });
  }
  applyFilters(): void { this.page.set(1); this.load(); }
  onPage(e: PageEvent): void { this.page.set(e.pageIndex + 1); this.pageSize.set(e.pageSize); this.load(); }
  archive(row: DataSource): void {
    if (!confirm(`Archive data source ${row.name}?`)) return;
    this.api.archive(row.id).subscribe({ next: () => this.load(), error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)) });
  }
}
