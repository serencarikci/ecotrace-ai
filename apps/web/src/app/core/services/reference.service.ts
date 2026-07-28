import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  ActivityType,
  ActivityTypeCreate,
  ActivityTypeUpdate,
  ReferenceListParams,
  Unit,
  UnitCreate,
  UnitUpdate,
} from '../models/reference.models';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class ReferenceService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}${environment.apiV1Prefix}/reference`;

  listUnits(params: ReferenceListParams = {}): Observable<Page<Unit>> {
    return this.http.get<Page<Unit>>(`${this.api}/units`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 100,
        search: params.search,
        activeOnly: params.activeOnly,
        dimension: params.dimension,
      }),
    });
  }

  createUnit(payload: UnitCreate): Observable<Unit> {
    return this.http.post<Unit>(`${this.api}/units`, payload);
  }

  updateUnit(unitId: string, payload: UnitUpdate): Observable<Unit> {
    return this.http.patch<Unit>(`${this.api}/units/${unitId}`, payload);
  }

  listActivityTypes(params: ReferenceListParams = {}): Observable<Page<ActivityType>> {
    return this.http.get<Page<ActivityType>>(`${this.api}/activity-types`, {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 100,
        search: params.search,
        activeOnly: params.activeOnly,
        category: params.category,
      }),
    });
  }

  createActivityType(payload: ActivityTypeCreate): Observable<ActivityType> {
    return this.http.post<ActivityType>(`${this.api}/activity-types`, payload);
  }

  updateActivityType(activityTypeId: string, payload: ActivityTypeUpdate): Observable<ActivityType> {
    return this.http.patch<ActivityType>(`${this.api}/activity-types/${activityTypeId}`, payload);
  }
}
