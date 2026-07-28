import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  ReportingPeriod,
  ReportingPeriodCreate,
  ReportingPeriodListParams,
  ReportingPeriodUpdate,
} from '../models/reporting-period.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class ReportingPeriodService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/reporting-periods`;
  }

  list(params: ReportingPeriodListParams = {}): Observable<Page<ReportingPeriod>> {
    return this.http.get<Page<ReportingPeriod>>(this.base(), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        search: params.search,
        status: params.status,
        periodType: params.periodType,
      }),
    });
  }

  get(periodId: string): Observable<ReportingPeriod> {
    return this.http.get<ReportingPeriod>(`${this.base()}/${periodId}`);
  }

  create(payload: ReportingPeriodCreate): Observable<ReportingPeriod> {
    return this.http.post<ReportingPeriod>(this.base(), payload);
  }

  update(periodId: string, payload: ReportingPeriodUpdate): Observable<ReportingPeriod> {
    return this.http.patch<ReportingPeriod>(`${this.base()}/${periodId}`, payload);
  }

  lock(periodId: string): Observable<ReportingPeriod> {
    return this.http.post<ReportingPeriod>(`${this.base()}/${periodId}/lock`, {});
  }

  unlock(periodId: string): Observable<ReportingPeriod> {
    return this.http.post<ReportingPeriod>(`${this.base()}/${periodId}/unlock`, {});
  }

  archive(periodId: string): Observable<ReportingPeriod> {
    return this.http.post<ReportingPeriod>(`${this.base()}/${periodId}/archive`, {});
  }
}
