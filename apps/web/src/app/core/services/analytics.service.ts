import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  AnalyticsDashboard,
  Baseline,
  Recommendation,
  ReductionInitiative,
  Scenario,
  ScenarioRun,
  SustainabilityTarget,
  TrendPoint,
} from '../models/analytics.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

type QueryParams = Record<string, string | number | boolean | null | undefined>;

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private orgBase(suffix: string): string {
    const id = this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}${suffix}`;
  }

  dashboard(params: QueryParams = {}): Observable<AnalyticsDashboard> {
    return this.http.get<AnalyticsDashboard>(this.orgBase('/analytics/dashboard'), {
      params: buildHttpParams(params),
    });
  }

  monthlyTrends(params: QueryParams = {}): Observable<{ points: TrendPoint[]; empty: boolean }> {
    return this.http.get<{ points: TrendPoint[]; empty: boolean }>(
      this.orgBase('/analytics/trends/monthly'),
      { params: buildHttpParams(params) },
    );
  }

  breakdown(dimension: string, params: QueryParams = {}): Observable<{ items: unknown[] }> {
    return this.http.get<{ items: unknown[] }>(
      this.orgBase(`/analytics/breakdowns/${dimension}`),
      { params: buildHttpParams(params) },
    );
  }

  intensity(params: QueryParams = {}): Observable<{ items: unknown[] }> {
    return this.http.get<{ items: unknown[] }>(this.orgBase('/analytics/intensity'), {
      params: buildHttpParams(params),
    });
  }

  kpis(params: QueryParams = {}): Observable<{ items: unknown[] }> {
    return this.http.get<{ items: unknown[] }>(this.orgBase('/analytics/kpis'), {
      params: buildHttpParams(params),
    });
  }

  decisionSupport(params: QueryParams = {}): Observable<Recommendation[]> {
    return this.http.get<Recommendation[]>(this.orgBase('/analytics/decision-support'), {
      params: buildHttpParams(params),
    });
  }

  listBaselines(params: QueryParams = {}): Observable<Page<Baseline>> {
    return this.http.get<Page<Baseline>>(this.orgBase('/sustainability-baselines'), {
      params: buildHttpParams(params),
    });
  }

  listTargets(params: QueryParams = {}): Observable<Page<SustainabilityTarget>> {
    return this.http.get<Page<SustainabilityTarget>>(this.orgBase('/sustainability-targets'), {
      params: buildHttpParams(params),
    });
  }

  targetProgress(id: string, params: QueryParams = {}): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(
      this.orgBase(`/sustainability-targets/${id}/progress`),
      { params: buildHttpParams(params) },
    );
  }

  listInitiatives(params: QueryParams = {}): Observable<Page<ReductionInitiative>> {
    return this.http.get<Page<ReductionInitiative>>(this.orgBase('/reduction-initiatives'), {
      params: buildHttpParams(params),
    });
  }

  listScenarios(params: QueryParams = {}): Observable<Page<Scenario>> {
    return this.http.get<Page<Scenario>>(this.orgBase('/scenarios'), {
      params: buildHttpParams(params),
    });
  }

  calculateScenario(id: string): Observable<ScenarioRun> {
    return this.http.post<ScenarioRun>(this.orgBase(`/scenarios/${id}/calculate`), {});
  }

  listScenarioRuns(id: string): Observable<ScenarioRun[]> {
    return this.http.get<ScenarioRun[]>(this.orgBase(`/scenarios/${id}/runs`));
  }

  downloadReport(path: string, params: QueryParams = {}): Observable<Blob> {
    return this.http.get(this.orgBase(`/reports/${path}`), {
      params: buildHttpParams({ ...params, format: 'csv' }),
      responseType: 'blob',
    });
  }
}
