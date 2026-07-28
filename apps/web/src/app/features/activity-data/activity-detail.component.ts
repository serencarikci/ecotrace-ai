import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { forkJoin } from 'rxjs';
import { ActivityRecordService } from '../../core/services/activity-record.service';
import { AttachmentService } from '../../core/services/attachment.service';
import { AuthService } from '../../core/services/auth.service';
import {
  ActivityRecord,
  ActivityRecordRevision,
} from '../../core/models/activity-record.models';
import { ActivityAttachment } from '../../core/models/attachment.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { activityWorkflowActions, canWriteActivity } from '../../core/services/roles.util';
import { ConfirmDialogComponent } from '../../shared/confirm-dialog.component';

@Component({
  selector: 'app-activity-detail',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatTableModule],
  templateUrl: './activity-detail.component.html',
})
export class ActivityDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ActivityRecordService);
  private readonly attachmentsApi = inject(AttachmentService);
  private readonly auth = inject(AuthService);
  private readonly dialog = inject(MatDialog);

  readonly record = signal<ActivityRecord | null>(null);
  readonly revisions = signal<ActivityRecordRevision[]>([]);
  readonly attachments = signal<ActivityAttachment[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly loading = signal(true);
  readonly canWrite = canWriteActivity(this.auth.currentRoles());

  readonly workflowActions = computed(() => {
    const record = this.record();
    if (!record) {
      return [] as Array<'submit' | 'approve' | 'reject' | 'correct' | 'archive'>;
    }
    return activityWorkflowActions(record.status, this.auth.currentRoles());
  });

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.errorMessage.set('Record not found.');
      this.loading.set(false);
      return;
    }
    this.loading.set(true);
    forkJoin({
      record: this.api.get(id),
      revisions: this.api.revisions(id),
      attachments: this.attachmentsApi.list(id),
    }).subscribe({
      next: (result) => {
        this.record.set(result.record);
        this.revisions.set(result.revisions);
        this.attachments.set(result.attachments.filter((a) => !a.isDeleted));
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  runWorkflow(action: 'submit' | 'approve' | 'reject' | 'correct' | 'archive'): void {
    const record = this.record();
    if (!record) {
      return;
    }
    const needsReason = action === 'reject' || action === 'correct';
    this.dialog
      .open(ConfirmDialogComponent, {
        data: {
          title: `${action[0].toUpperCase()}${action.slice(1)} record`,
          message: `Confirm ${action} for this activity record?`,
          confirmLabel: action[0].toUpperCase() + action.slice(1),
          requireReason: needsReason,
          reasonLabel: action === 'reject' ? 'Rejection reason' : 'Correction reason',
        },
      })
      .afterClosed()
      .subscribe((result) => {
        if (!result?.confirmed) {
          return;
        }
        const request$ =
          action === 'submit'
            ? this.api.submit(record.id, record.rowVersion)
            : action === 'approve'
              ? this.api.approve(record.id, record.rowVersion)
              : action === 'reject'
                ? this.api.reject(record.id, {
                    reason: result.reason ?? '',
                    rowVersion: record.rowVersion,
                  })
                : action === 'correct'
                  ? this.api.correct(record.id, {
                      reason: result.reason ?? '',
                      rowVersion: record.rowVersion,
                    })
                  : this.api.archive(record.id, record.rowVersion);
        request$.subscribe({
          next: () => this.reload(),
          error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
        });
      });
  }

  onFileSelected(event: Event): void {
    const record = this.record();
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!record || !file) {
      return;
    }
    this.attachmentsApi.upload(record.id, file).subscribe({
      next: () => this.reload(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    input.value = '';
  }

  downloadAttachment(attachment: ActivityAttachment): void {
    const record = this.record();
    if (!record) {
      return;
    }
    this.attachmentsApi.download(record.id, attachment.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = attachment.originalFileName;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  deleteAttachment(attachment: ActivityAttachment): void {
    const record = this.record();
    if (!record || !confirm(`Delete ${attachment.originalFileName}?`)) {
      return;
    }
    this.attachmentsApi.delete(record.id, attachment.id).subscribe({
      next: () => this.reload(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
