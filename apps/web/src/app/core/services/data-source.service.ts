import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  DataSource,
  DataSourceCreate,
  DataSourceListParams,
  DataSourceUpdate,
} from '../models/data-source.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class DataSourceService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/data-sources`;
  }

  list(params: DataSourceListParams = {}): Observable<Page<DataSource>> {
    return this.http.get<Page<DataSource>>(this.base(), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        search: params.search,
        facilityId: params.facilityId,
        equipmentId: params.equipmentId,
        sourceType: params.sourceType,
        isActive: params.isActive,
      }),
    });
  }

  get(dataSourceId: string): Observable<DataSource> {
    return this.http.get<DataSource>(`${this.base()}/${dataSourceId}`);
  }

  create(payload: DataSourceCreate): Observable<DataSource> {
    return this.http.post<DataSource>(this.base(), payload);
  }

  update(dataSourceId: string, payload: DataSourceUpdate): Observable<DataSource> {
    return this.http.patch<DataSource>(`${this.base()}/${dataSourceId}`, payload);
  }

  archive(dataSourceId: string): Observable<DataSource> {
    return this.http.post<DataSource>(`${this.base()}/${dataSourceId}/archive`, {});
  }
}
