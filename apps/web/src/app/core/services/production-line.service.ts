import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  ProductionLine,
  ProductionLineCreate,
  ProductionLineUpdate,
} from '../models/production-line.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

@Injectable({ providedIn: 'root' })
export class ProductionLineService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private orgBase(orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}`;
  }

  listByFacility(
    facilityId: string,
    page = 1,
    pageSize = 50,
    isActive?: boolean,
  ): Observable<Page<ProductionLine>> {
    return this.http.get<Page<ProductionLine>>(
      `${this.orgBase()}/facilities/${facilityId}/production-lines`,
      {
        params: buildHttpParams({ page, pageSize, isActive }),
      },
    );
  }

  get(productionLineId: string): Observable<ProductionLine> {
    return this.http.get<ProductionLine>(`${this.orgBase()}/production-lines/${productionLineId}`);
  }

  create(facilityId: string, payload: ProductionLineCreate): Observable<ProductionLine> {
    return this.http.post<ProductionLine>(
      `${this.orgBase()}/facilities/${facilityId}/production-lines`,
      payload,
    );
  }

  update(productionLineId: string, payload: ProductionLineUpdate): Observable<ProductionLine> {
    return this.http.patch<ProductionLine>(
      `${this.orgBase()}/production-lines/${productionLineId}`,
      payload,
    );
  }

  archive(productionLineId: string): Observable<ProductionLine> {
    return this.http.post<ProductionLine>(
      `${this.orgBase()}/production-lines/${productionLineId}/archive`,
      {},
    );
  }
}
