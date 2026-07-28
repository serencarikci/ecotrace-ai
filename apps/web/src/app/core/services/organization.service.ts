import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  Page,
} from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class OrganizationService {
  private readonly api = `${environment.apiUrl}${environment.apiV1Prefix}/organizations`;

  constructor(private readonly http: HttpClient) {}

  list(page = 1, pageSize = 20): Observable<Page<Organization>> {
    const params = new HttpParams().set('page', page).set('pageSize', pageSize);
    return this.http.get<Page<Organization>>(this.api, { params });
  }

  get(id: string): Observable<Organization> {
    return this.http.get<Organization>(`${this.api}/${id}`);
  }

  create(payload: OrganizationCreate): Observable<Organization> {
    return this.http.post<Organization>(this.api, payload);
  }

  update(id: string, payload: OrganizationUpdate): Observable<Organization> {
    return this.http.patch<Organization>(`${this.api}/${id}`, payload);
  }
}
