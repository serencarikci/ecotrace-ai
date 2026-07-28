import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { MetaResponse } from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class MetaService {
  constructor(private readonly http: HttpClient) {}

  getMeta(): Observable<MetaResponse> {
    return this.http.get<MetaResponse>(
      `${environment.apiUrl}${environment.apiV1Prefix}/meta`,
    );
  }

  getHealth(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(`${environment.apiUrl}/health`);
  }
}
