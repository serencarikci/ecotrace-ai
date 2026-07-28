import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import {
  CalculationItem,
  CalculationRun,
  CarbonInventory,
  EmissionFactor,
  EmissionFactorSource,
  FactorPreference,
  InventorySummary,
  ValidationResult,
} from '../models/carbon.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

type QueryParams = Record<string, string | number | boolean | null | undefined>;

@Injectable({ providedIn: 'root' })
export class CarbonService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private api(path: string): string {
    return `${environment.apiUrl}${environment.apiV1Prefix}${path}`;
  }

  private orgBase(suffix: string, orgId?: string): string {
    const id = orgId ?? this.auth.requireOrganizationId();
    return this.api(`/organizations/${id}${suffix}`);
  }

  listSources(params: QueryParams = {}): Observable<Page<EmissionFactorSource>> {
    return this.http.get<Page<EmissionFactorSource>>(this.api('/emission-factor-sources'), {
      params: buildHttpParams(params),
    });
  }

  getSource(id: string): Observable<EmissionFactorSource> {
    return this.http.get<EmissionFactorSource>(this.api(`/emission-factor-sources/${id}`));
  }

  createSource(payload: Partial<EmissionFactorSource>): Observable<EmissionFactorSource> {
    return this.http.post<EmissionFactorSource>(this.api('/emission-factor-sources'), payload);
  }

  archiveSource(id: string): Observable<EmissionFactorSource> {
    return this.http.post<EmissionFactorSource>(
      this.api(`/emission-factor-sources/${id}/archive`),
      {},
    );
  }

  listFactors(params: QueryParams = {}): Observable<Page<EmissionFactor>> {
    return this.http.get<Page<EmissionFactor>>(this.api('/emission-factors'), {
      params: buildHttpParams(params),
    });
  }

  getFactor(id: string): Observable<EmissionFactor> {
    return this.http.get<EmissionFactor>(this.api(`/emission-factors/${id}`));
  }

  createFactor(payload: Record<string, unknown>): Observable<EmissionFactor> {
    return this.http.post<EmissionFactor>(this.api('/emission-factors'), payload);
  }

  updateFactor(id: string, payload: Record<string, unknown>): Observable<EmissionFactor> {
    return this.http.patch<EmissionFactor>(this.api(`/emission-factors/${id}`), payload);
  }

  activateFactor(id: string): Observable<EmissionFactor> {
    return this.http.post<EmissionFactor>(this.api(`/emission-factors/${id}/activate`), {});
  }

  supersedeFactor(id: string): Observable<EmissionFactor> {
    return this.http.post<EmissionFactor>(this.api(`/emission-factors/${id}/supersede`), {});
  }

  cloneFactor(id: string): Observable<EmissionFactor> {
    return this.http.post<EmissionFactor>(this.api(`/emission-factors/${id}/clone-version`), {});
  }

  listFactorVersions(id: string): Observable<EmissionFactor[]> {
    return this.http.get<EmissionFactor[]>(this.api(`/emission-factors/${id}/versions`));
  }

  listPreferences(): Observable<FactorPreference[]> {
    return this.http.get<FactorPreference[]>(this.orgBase('/emission-factor-preferences'));
  }

  createPreference(payload: Record<string, unknown>): Observable<FactorPreference> {
    return this.http.post<FactorPreference>(this.orgBase('/emission-factor-preferences'), payload);
  }

  deletePreference(id: string): Observable<FactorPreference> {
    return this.http.delete<FactorPreference>(this.orgBase(`/emission-factor-preferences/${id}`));
  }

  previewMatch(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.orgBase('/factor-matching/preview'), payload);
  }

  listInventories(params: QueryParams = {}): Observable<Page<CarbonInventory>> {
    return this.http.get<Page<CarbonInventory>>(this.orgBase('/carbon-inventories'), {
      params: buildHttpParams(params),
    });
  }

  getInventory(id: string): Observable<CarbonInventory> {
    return this.http.get<CarbonInventory>(this.orgBase(`/carbon-inventories/${id}`));
  }

  createInventory(payload: Record<string, unknown>): Observable<CarbonInventory> {
    return this.http.post<CarbonInventory>(this.orgBase('/carbon-inventories'), payload);
  }

  validateInventory(id: string): Observable<ValidationResult> {
    return this.http.post<ValidationResult>(this.orgBase(`/carbon-inventories/${id}/validate`), {});
  }

  calculateInventory(id: string, partial = false): Observable<CalculationRun> {
    return this.http.post<CalculationRun>(this.orgBase(`/carbon-inventories/${id}/calculate`), {
      partialCalculation: partial,
    });
  }

  submitReview(id: string): Observable<CarbonInventory> {
    return this.http.post<CarbonInventory>(
      this.orgBase(`/carbon-inventories/${id}/submit-review`),
      {},
    );
  }

  approveInventory(id: string): Observable<CarbonInventory> {
    return this.http.post<CarbonInventory>(this.orgBase(`/carbon-inventories/${id}/approve`), {});
  }

  recalculate(id: string, partial = false): Observable<CalculationRun> {
    return this.http.post<CalculationRun>(this.orgBase(`/carbon-inventories/${id}/recalculate`), {
      partialCalculation: partial,
    });
  }

  listRuns(id: string): Observable<CalculationRun[]> {
    return this.http.get<CalculationRun[]>(this.orgBase(`/carbon-inventories/${id}/runs`));
  }

  listItems(id: string, params: QueryParams = {}): Observable<Page<CalculationItem>> {
    return this.http.get<Page<CalculationItem>>(this.orgBase(`/carbon-inventories/${id}/items`), {
      params: buildHttpParams(params),
    });
  }

  getSummary(id: string): Observable<InventorySummary> {
    return this.http.get<InventorySummary>(this.orgBase(`/carbon-inventories/${id}/summary`));
  }

  getItemDetail(itemId: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(
      this.orgBase(`/carbon-calculation-items/${itemId}`),
    );
  }
}
