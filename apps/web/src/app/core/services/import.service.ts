import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  ImportJob,
  ImportJobListParams,
  ImportJobRow,
  ImportRowListParams,
} from '../models/import.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class ImportService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/imports/activity-records`;
  }

  list(params: ImportJobListParams = {}): Observable<Page<ImportJob>> {
    return this.http.get<Page<ImportJob>>(this.base(), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        status: params.status,
      }),
    });
  }

  get(importJobId: string): Observable<ImportJob> {
    return this.http.get<ImportJob>(`${this.base()}/${importJobId}`);
  }

  rows(importJobId: string, params: ImportRowListParams = {}): Observable<Page<ImportJobRow>> {
    return this.http.get<Page<ImportJobRow>>(`${this.base()}/${importJobId}/rows`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 50,
        validationStatus: params.validationStatus,
      }),
    });
  }

  upload(file: File): Observable<ImportJob> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImportJob>(this.base(), formData);
  }

  validate(importJobId: string): Observable<ImportJob> {
    return this.http.post<ImportJob>(`${this.base()}/${importJobId}/validate`, {});
  }

  execute(importJobId: string): Observable<ImportJob> {
    return this.http.post<ImportJob>(`${this.base()}/${importJobId}/execute`, {});
  }

  downloadTemplate(): Observable<Blob> {
    return this.http.get(`${this.base()}/template`, { responseType: 'blob' });
  }
}
