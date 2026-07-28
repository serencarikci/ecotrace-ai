import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmLabel?: string;
  requireReason?: boolean;
  reasonLabel?: string;
}

export interface ConfirmDialogResult {
  confirmed: boolean;
  reason?: string;
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <mat-dialog-content>
      <p>{{ data.message }}</p>
      @if (data.requireReason) {
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ data.reasonLabel || 'Reason' }}</mat-label>
          <textarea matInput rows="3" [formControl]="reason"></textarea>
          @if (reason.touched && reason.invalid) {
            <mat-error>Reason is required.</mat-error>
          }
        </mat-form-field>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" mat-dialog-close>Cancel</button>
      <button mat-flat-button color="primary" type="button" (click)="confirm()">
        {{ data.confirmLabel || 'Confirm' }}
      </button>
    </mat-dialog-actions>
  `,
})
export class ConfirmDialogComponent {
  readonly data = inject<ConfirmDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ConfirmDialogComponent, ConfirmDialogResult>);
  private readonly fb = inject(FormBuilder);

  readonly reason = this.fb.nonNullable.control('', this.data.requireReason ? Validators.required : []);

  confirm(): void {
    if (this.data.requireReason) {
      if (this.reason.invalid) {
        this.reason.markAsTouched();
        return;
      }
      this.dialogRef.close({ confirmed: true, reason: this.reason.value.trim() });
      return;
    }
    this.dialogRef.close({ confirmed: true });
  }
}
