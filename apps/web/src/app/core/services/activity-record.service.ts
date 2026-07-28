import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  ActivityRecord,
  ActivityRecordCorrectRequest,
  ActivityRecordCreate,
  ActivityRecordListParams,
  ActivityRecordRejectRequest,
  ActivityRecordRevision,
  ActivityRecordUpdate,
} from '../models/activity-record.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class ActivityRecordService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/activity-records`;
  }

  list(params: ActivityRecordListParams = {}): Observable<Page<ActivityRecord>> {
    return this.http.get<Page<ActivityRecord>>(this.base(), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        search: params.search,
        facilityId: params.facilityId,
        productionLineId: params.productionLineId,
        equipmentId: params.equipmentId,
        dataSourceId: params.dataSourceId,
        activityTypeId: params.activityTypeId,
        reportingPeriodId: params.reportingPeriodId,
        status: params.status,
        dateFrom: params.dateFrom,
        dateTo: params.dateTo,
        sortBy: params.sortBy,
        sortDirection: params.sortDirection,
      }),
    });
  }

  get(activityRecordId: string): Observable<ActivityRecord> {
    return this.http.get<ActivityRecord>(`${this.base()}/${activityRecordId}`);
  }

  create(payload: ActivityRecordCreate): Observable<ActivityRecord> {
    return this.http.post<ActivityRecord>(this.base(), payload);
  }

  update(activityRecordId: string, payload: ActivityRecordUpdate): Observable<ActivityRecord> {
    return this.http.patch<ActivityRecord>(`${this.base()}/${activityRecordId}`, payload);
  }

  submit(activityRecordId: string, rowVersion: number): Observable<ActivityRecord> {
    return this.http.post<ActivityRecord>(`${this.base()}/${activityRecordId}/submit`, {
      rowVersion,
    });
  }

  approve(activityRecordId: string, rowVersion: number): Observable<ActivityRecord> {
    return this.http.post<ActivityRecord>(`${this.base()}/${activityRecordId}/approve`, {
      rowVersion,
    });
  }

  reject(
    activityRecordId: string,
    payload: ActivityRecordRejectRequest,
  ): Observable<ActivityRecord> {
    return this.http.post<ActivityRecord>(`${this.base()}/${activityRecordId}/reject`, payload);
  }

  correct(
    activityRecordId: string,
    payload: ActivityRecordCorrectRequest,
  ): Observable<ActivityRecord> {
    return this.http.post<ActivityRecord>(`${this.base()}/${activityRecordId}/correct`, payload);
  }

  archive(activityRecordId: string, rowVersion: number): Observable<ActivityRecord> {
    return this.http.post<ActivityRecord>(`${this.base()}/${activityRecordId}/archive`, {
      rowVersion,
    });
  }

  revisions(activityRecordId: string): Observable<ActivityRecordRevision[]> {
    return this.http.get<ActivityRecordRevision[]>(
      `${this.base()}/${activityRecordId}/revisions`,
    );
  }
}
