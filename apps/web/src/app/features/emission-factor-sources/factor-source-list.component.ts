import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CarbonService } from '../../core/services/carbon.service';
import { AuthService } from '../../core/services/auth.service';
import { EmissionFactorSource } from '../../core/models/carbon.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageReferenceData } from '../../core/services/roles.util';

@Component({
  selector: 'app-factor-source-list',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatTableModule, MatProgressSpinnerModule],
  template: `
    <div class="page">
      <div class="header">
        <h1>Emission Factor Sources</h1>
        @if (canManage) {
          <a mat-flat-button color="primary" routerLink="/app/emission-factor-sources/new">New source</a>
        }
      </div>
      <p class="hint">Demo sources are labeled clearly and are not authoritative.</p>
      @if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      }
      @if (loading()) {
        <mat-spinner diameter="36"></mat-spinner>
      } @else {
        <table mat-table [dataSource]="items()" class="full">
          <ng-container matColumnDef="code">
            <th mat-header-cell *matHeaderCellDef>Code</th>
            <td mat-cell *matCellDef="let row">{{ row.code }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="demo">
            <th mat-header-cell *matHeaderCellDef>Demo</th>
            <td mat-cell *matCellDef="let row">{{ row.isDemo ? 'Yes' : 'No' }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Active</th>
            <td mat-cell *matCellDef="let row">{{ row.isActive ? 'Active' : 'Archived' }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              <a mat-button [routerLink]="['/app/emission-factor-sources', row.id]">Open</a>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="cols"></tr>
          <tr mat-row *matRowDef="let row; columns: cols"></tr>
        </table>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 1rem; }
      .header { display: flex; justify-content: space-between; align-items: center; }
      .full { width: 100%; }
      .hint { opacity: 0.75; }
      .error { color: #b00020; }
    `,
  ],
})
export class FactorSourceListComponent implements OnInit {
  private readonly api = inject(CarbonService);
  private readonly auth = inject(AuthService);
  readonly items = signal<EmissionFactorSource[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly canManage = canManageReferenceData(this.auth.currentRoles());
  readonly cols = ['code', 'name', 'demo', 'status', 'actions'];

  ngOnInit(): void {
    this.loading.set(true);
    this.api.listSources({ pageSize: 50 }).subscribe({
      next: (page) => {
        this.items.set(page.items);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }
}
