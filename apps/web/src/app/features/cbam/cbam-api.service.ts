import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';

export interface CbamModuleStatus {
  module: string;
  uiLabelTr: string;
  status: string;
  foundationAvailable: boolean;
  domainFunctionalityImplemented: boolean;
  complianceClaim: boolean;
  calculationImplemented: boolean;
  message: string;
  permissionsDefined: string[];
}

@Injectable({ providedIn: 'root' })
export class CbamApiService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  getModuleStatus(organizationId?: string): Observable<CbamModuleStatus> {
    const id = organizationId ?? this.auth.requireOrganizationId();
    const url = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/${id}/module-status`;
    return this.http.get<CbamModuleStatus>(url);
  }
}
