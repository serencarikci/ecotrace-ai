import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ReportingPeriodService } from '../../core/services/reporting-period.service';
import { AuthService } from '../../core/services/auth.service';
import { ReportingPeriod } from '../../core/models/reporting-period.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canLockPeriod, canManagePeriods, canUnlockPeriod } from '../../core/services/roles.util';
import { ConfirmDialogComponent } from '../../shared/confirm-dialog.component';

@Component({
  selector: 'app-reporting-period-detail',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './reporting-period-detail.component.html',
})
export class ReportingPeriodDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ReportingPeriodService);
  private readonly auth = inject(AuthService);
  private readonly dialog = inject(MatDialog);
  private readonly fb = inject(FormBuilder);

  readonly period = signal<ReportingPeriod | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly editing = signal(false);
  readonly roles = this.auth.currentRoles();
  readonly canManage = canManagePeriods(this.roles);
  readonly canLock = canLockPeriod(this.roles);
  readonly canUnlock = canUnlockPeriod(this.roles);

  readonly editForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    startDate: ['', Validators.required],
    endDate: ['', Validators.required],
  });

  ngOnInit(): void { this.reload(); }

  reload(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.api.get(id).subscribe({
      next: (period) => {
        this.period.set(period);
        this.editForm.patchValue({ name: period.name, startDate: period.startDate, endDate: period.endDate });
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  save(): void {
    const period = this.period();
    if (!period || this.editForm.invalid) { this.editForm.markAllAsTouched(); return; }
    this.api.update(period.id, this.editForm.getRawValue()).subscribe({
      next: () => { this.editing.set(false); this.reload(); },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  lock(): void {
    const period = this.period();
    if (!period) return;
    this.dialog.open(ConfirmDialogComponent, {
      data: { title: 'Lock period', message: 'Locked periods reject activity create/update/workflow actions. Continue?', confirmLabel: 'Lock' },
    }).afterClosed().subscribe((result) => {
      if (!result?.confirmed) return;
      this.api.lock(period.id).subscribe({ next: () => this.reload(), error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)) });
    });
  }

  unlock(): void {
    const period = this.period();
    if (!period) return;
    this.dialog.open(ConfirmDialogComponent, {
      data: { title: 'Unlock period', message: 'Unlocking allows activity changes again. Continue?', confirmLabel: 'Unlock' },
    }).afterClosed().subscribe((result) => {
      if (!result?.confirmed) return;
      this.api.unlock(period.id).subscribe({ next: () => this.reload(), error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)) });
    });
  }

  archive(): void {
    const period = this.period();
    if (!period) return;
    this.dialog.open(ConfirmDialogComponent, {
      data: { title: 'Archive period', message: `Archive ${period.name}?`, confirmLabel: 'Archive' },
    }).afterClosed().subscribe((result) => {
      if (!result?.confirmed) return;
      this.api.archive(period.id).subscribe({ next: () => this.reload(), error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)) });
    });
  }
}
