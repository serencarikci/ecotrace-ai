import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ImportService } from '../../core/services/import.service';
import { AuthService } from '../../core/services/auth.service';
import { ImportJob } from '../../core/models/import.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canRunImports } from '../../core/services/roles.util';

@Component({
  selector: 'app-import-list',
  standalone: true,
  imports: [
    RouterLink,
    MatTableModule,
    MatButtonModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <section class="page">
      <div class="header-row">
        <div>
          <h1 class="page-title">Data Imports</h1>
          <p class="page-subtitle">CSV import jobs for activity records.</p>
        </div>
        @if (canImport) {
          <a mat-flat-button color="primary" routerLink="/app/data-imports/new">New import</a>
        }
      </div>
      @if (errorMessage()) {
        <p class="error-text" role="alert">{{ errorMessage() }}</p>
      }
      <div class="surface-card table-wrap">
        @if (loading()) {
          <div class="loading-state"><mat-spinner diameter="36" /></div>
        } @else {
          <table mat-table [dataSource]="items()" class="full-width">
            <ng-container matColumnDef="fileName">
              <th mat-header-cell *matHeaderCellDef>File</th>
              <td mat-cell *matCellDef="let row">{{ row.fileName }}</td>
            </ng-container>
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let row">
                <span class="status-chip" [class]="row.status">{{ row.status }}</span>
              </td>
            </ng-container>
            <ng-container matColumnDef="counts">
              <th mat-header-cell *matHeaderCellDef>Rows</th>
              <td mat-cell *matCellDef="let row">
                {{ row.validRows }}/{{ row.totalRows }} valid · {{ row.importedRows }} imported
              </td>
            </ng-container>
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef></th>
              <td mat-cell *matCellDef="let row">
                <a [routerLink]="['/app/data-imports', row.id]">Open</a>
              </td>
            </ng-container>
            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
          </table>
          @if (items().length === 0) {
            <p class="empty-state">No import jobs are available.</p>
          }
          <mat-paginator
            [length]="totalItems()"
            [pageIndex]="page() - 1"
            [pageSize]="pageSize()"
            [pageSizeOptions]="[10, 20, 50]"
            (page)="onPage($event)"
          />
        }
      </div>
    </section>
  `,
})
export class ImportListComponent implements OnInit {
  private readonly api = inject(ImportService);
  private readonly auth = inject(AuthService);
  readonly items = signal<ImportJob[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly totalItems = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly canImport = canRunImports(this.auth.currentRoles());
  readonly displayedColumns = ['fileName', 'status', 'counts', 'actions'];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.list({ page: this.page(), pageSize: this.pageSize() }).subscribe({
      next: (r) => {
        this.items.set(r.items);
        this.totalItems.set(r.totalItems);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  onPage(e: PageEvent): void {
    this.page.set(e.pageIndex + 1);
    this.pageSize.set(e.pageSize);
    this.load();
  }
}
