import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ActivityAttachment } from '../models/attachment.models';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AttachmentService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(activityRecordId: string, orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/activity-records/${activityRecordId}/attachments`;
  }

  list(activityRecordId: string): Observable<ActivityAttachment[]> {
    return this.http.get<ActivityAttachment[]>(this.base(activityRecordId));
  }

  upload(activityRecordId: string, file: File): Observable<ActivityAttachment> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ActivityAttachment>(this.base(activityRecordId), formData);
  }

  download(activityRecordId: string, attachmentId: string): Observable<Blob> {
    return this.http.get(`${this.base(activityRecordId)}/${attachmentId}/download`, {
      responseType: 'blob',
    });
  }

  delete(activityRecordId: string, attachmentId: string): Observable<void> {
    return this.http.delete<void>(`${this.base(activityRecordId)}/${attachmentId}`);
  }
}
