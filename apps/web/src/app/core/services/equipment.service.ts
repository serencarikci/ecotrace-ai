import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  Equipment,
  EquipmentCreate,
  EquipmentListParams,
  EquipmentUpdate,
} from '../models/equipment.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class EquipmentService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private base(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}/equipment`;
  }

  list(params: EquipmentListParams = {}): Observable<Page<Equipment>> {
    return this.http.get<Page<Equipment>>(this.base(), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        search: params.search,
        facilityId: params.facilityId,
        productionLineId: params.productionLineId,
        equipmentType: params.equipmentType,
        isActive: params.isActive,
      }),
    });
  }

  get(equipmentId: string): Observable<Equipment> {
    return this.http.get<Equipment>(`${this.base()}/${equipmentId}`);
  }

  create(payload: EquipmentCreate): Observable<Equipment> {
    return this.http.post<Equipment>(this.base(), payload);
  }

  update(equipmentId: string, payload: EquipmentUpdate): Observable<Equipment> {
    return this.http.patch<Equipment>(`${this.base()}/${equipmentId}`, payload);
  }

  archive(equipmentId: string): Observable<Equipment> {
    return this.http.post<Equipment>(`${this.base()}/${equipmentId}/archive`, {});
  }
}
