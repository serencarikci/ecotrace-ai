import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  Facility,
  FacilityCreate,
  FacilityListParams,
  FacilityUpdate,
} from '../models/facility.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class FacilityService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/facilities`;
  }

  list(params: FacilityListParams = {}): Observable<Page<Facility>> {
    return this.http.get<Page<Facility>>(this.base(), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        search: params.search,
        facilityType: params.facilityType,
        countryCode: params.countryCode,
        city: params.city,
        isActive: params.isActive,
      }),
    });
  }

  get(facilityId: string): Observable<Facility> {
    return this.http.get<Facility>(`${this.base()}/${facilityId}`);
  }

  create(payload: FacilityCreate): Observable<Facility> {
    return this.http.post<Facility>(this.base(), payload);
  }

  update(facilityId: string, payload: FacilityUpdate): Observable<Facility> {
    return this.http.patch<Facility>(`${this.base()}/${facilityId}`, payload);
  }

  archive(facilityId: string): Observable<Facility> {
    return this.http.post<Facility>(`${this.base()}/${facilityId}/archive`, {});
  }
}
