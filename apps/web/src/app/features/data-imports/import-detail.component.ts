import { JsonPipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { forkJoin } from 'rxjs';
import { ImportService } from '../../core/services/import.service';
import { ImportJob, ImportJobRow } from '../../core/models/import.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-import-detail',
  standalone: true,
  imports: [
    JsonPipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './import-detail.component.html',
})
export class ImportDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ImportService);
  private readonly fb = inject(FormBuilder);

  readonly job = signal<ImportJob | null>(null);
  readonly rows = signal<ImportJobRow[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly displayedColumns = ['rowNumber', 'validationStatus', 'errors', 'raw'];
  readonly filters = this.fb.nonNullable.group({ validationStatus: [''] });

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      return;
    }
    const status = this.filters.controls.validationStatus.value || undefined;
    forkJoin({
      job: this.api.get(id),
      rows: this.api.rows(id, { page: 1, pageSize: 100, validationStatus: status }),
    }).subscribe({
      next: (result) => {
        this.job.set(result.job);
        this.rows.set(result.rows.items);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  formatErrors(row: ImportJobRow): string {
    const errors = row.validationErrorsJson;
    if (!errors) {
      return '—';
    }
    if (Array.isArray(errors)) {
      return errors
        .map((e) => (typeof e === 'string' ? e : `${e.field ?? ''}: ${e.message}`))
        .join('; ');
    }
    return String(errors);
  }
}
