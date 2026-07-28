import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ImportService } from '../../core/services/import.service';
import { extractApiErrorMessage } from '../../core/services/error.util';

export type ImportWizardStep =
  | 'template'
  | 'select'
  | 'upload'
  | 'validate'
  | 'review'
  | 'execute'
  | 'results';

@Component({
  selector: 'app-import-wizard',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatStepperModule, MatFormFieldModule, MatInputModule],
  templateUrl: './import-wizard.component.html',
  styleUrl: './import-wizard.component.scss',
})
export class ImportWizardComponent {
  private readonly api = inject(ImportService);
  private readonly router = inject(Router);

  readonly step = signal<ImportWizardStep>('template');
  readonly selectedFile = signal<File | null>(null);
  readonly jobId = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly loading = signal(false);
  readonly steps: ImportWizardStep[] = [
    'template',
    'select',
    'upload',
    'validate',
    'review',
    'execute',
    'results',
  ];

  downloadTemplate(): void {
    this.errorMessage.set(null);
    this.api.downloadTemplate().subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'activity-records-template.csv';
        a.click();
        URL.revokeObjectURL(url);
        this.step.set('select');
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedFile.set(file);
    if (file) {
      this.step.set('upload');
    }
  }

  upload(): void {
    const file = this.selectedFile();
    if (!file) {
      this.errorMessage.set('Select a CSV file first.');
      return;
    }
    this.loading.set(true);
    this.errorMessage.set(null);
    this.api.upload(file).subscribe({
      next: (job) => {
        this.jobId.set(job.id);
        this.loading.set(false);
        this.step.set('validate');
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  validate(): void {
    const id = this.jobId();
    if (!id) {
      return;
    }
    this.loading.set(true);
    this.api.validate(id).subscribe({
      next: () => {
        this.loading.set(false);
        this.step.set('review');
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  goToExecute(): void {
    this.step.set('execute');
  }

  execute(): void {
    const id = this.jobId();
    if (!id) {
      return;
    }
    this.loading.set(true);
    this.api.execute(id).subscribe({
      next: () => {
        this.loading.set(false);
        this.step.set('results');
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  openResults(): void {
    const id = this.jobId();
    if (id) {
      void this.router.navigate(['/app/data-imports', id]);
    }
  }

  stepIndex(): number {
    return this.steps.indexOf(this.step());
  }
}
