import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Page } from '../models/api.models';
import { AuthService } from './auth.service';
import { buildHttpParams } from './http-params.util';

export interface Product {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  description?: string | null;
  productType: string;
  productCategory?: string | null;
  brand?: string | null;
  model?: string | null;
  sku?: string | null;
  gtin?: string | null;
  countryOfOrigin?: string | null;
  defaultUnitCode: string;
  weightValue?: string | null;
  weightUnitCode?: string | null;
  recyclabilityPercentage?: string | null;
  recycledContentPercentage?: string | null;
  repairabilityScore?: number | null;
  isActive: boolean;
}

export interface Supplier {
  id: string;
  code: string;
  name: string;
  supplierType: string;
  status: string;
  countryCode?: string | null;
  sustainabilityRating?: number | null;
}

export interface Material {
  id: string;
  code: string;
  name: string;
  materialCategory: string;
  defaultUnitCode: string;
  isActive: boolean;
  recycledContentPercentage?: string | null;
}

export interface LcaStudy {
  id: string;
  code: string;
  name: string;
  studyType: string;
  status: string;
  productId: string;
  disclaimer?: string;
}

export interface ProductCarbonFootprint {
  id: string;
  productId: string;
  totalKgCo2e: string;
  cradleToGateKgCo2e?: string | null;
  usePhaseKgCo2e?: string | null;
  endOfLifeKgCo2e?: string | null;
  functionalUnitQuantity: string;
  functionalUnitCode: string;
  status: string;
  disclaimer?: string;
}

export interface DigitalProductPassport {
  id: string;
  passportCode: string;
  title: string;
  version: number;
  status: string;
  publicSlug: string;
  productId: string;
  disclaimer?: string;
  sections?: Array<{
    sectionCode: string;
    title: string;
    isPublic: boolean;
    structuredDataJson?: Record<string, unknown> | null;
  }>;
}

export interface PublicPassport {
  status: string;
  title: string;
  description?: string | null;
  version: number;
  publicSlug: string;
  publishedAt?: string | null;
  revokedAt?: string | null;
  product: Record<string, unknown>;
  manufacturer: Record<string, unknown>;
  sections: Array<Record<string, unknown>>;
  carbonFootprint?: Record<string, unknown> | null;
  disclaimer: string;
  qrCodeReference?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ProductSustainabilityService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private orgBase(path: string): string {
    const id = this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}${path}`;
  }

  listProducts(params: {
    page?: number;
    pageSize?: number;
    search?: string;
    productType?: string;
    isActive?: boolean;
  } = {}): Observable<Page<Product>> {
    return this.http.get<Page<Product>>(this.orgBase('/products'), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        search: params.search,
        productType: params.productType,
        isActive: params.isActive,
      }),
    });
  }

  getProduct(productId: string): Observable<Product> {
    return this.http.get<Product>(this.orgBase(`/products/${productId}`));
  }

  createProduct(payload: Record<string, unknown>): Observable<Product> {
    return this.http.post<Product>(this.orgBase('/products'), payload);
  }

  archiveProduct(productId: string): Observable<Product> {
    return this.http.post<Product>(this.orgBase(`/products/${productId}/archive`), {});
  }

  listSuppliers(params: { page?: number; search?: string } = {}): Observable<Page<Supplier>> {
    return this.http.get<Page<Supplier>>(this.orgBase('/suppliers'), {
      params: buildHttpParams({ page: params.page ?? 1, pageSize: 20, search: params.search }),
    });
  }

  listMaterials(params: { page?: number; search?: string } = {}): Observable<Page<Material>> {
    return this.http.get<Page<Material>>(this.orgBase('/materials'), {
      params: buildHttpParams({ page: params.page ?? 1, pageSize: 20, search: params.search }),
    });
  }

  listBatches(params: { page?: number; search?: string } = {}): Observable<Page<Record<string, unknown>>> {
    return this.http.get<Page<Record<string, unknown>>>(this.orgBase('/product-batches'), {
      params: buildHttpParams({ page: params.page ?? 1, pageSize: 20, search: params.search }),
    });
  }

  listBoms(productId: string): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(this.orgBase(`/products/${productId}/boms`));
  }

  listStudies(params: { page?: number; search?: string } = {}): Observable<Page<LcaStudy>> {
    return this.http.get<Page<LcaStudy>>(this.orgBase('/lca-studies'), {
      params: buildHttpParams({ page: params.page ?? 1, pageSize: 20, search: params.search }),
    });
  }

  getStudyResults(studyId: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(this.orgBase(`/lca-studies/${studyId}/results`));
  }

  calculateStudy(studyId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(
      this.orgBase(`/lca-studies/${studyId}/calculate`),
      {},
    );
  }

  listFootprints(params: { page?: number; productId?: string } = {}): Observable<Page<ProductCarbonFootprint>> {
    return this.http.get<Page<ProductCarbonFootprint>>(this.orgBase('/product-carbon-footprints'), {
      params: buildHttpParams({
        page: params.page ?? 1,
        pageSize: 20,
        productId: params.productId,
      }),
    });
  }

  listPassports(params: { page?: number; search?: string } = {}): Observable<Page<DigitalProductPassport>> {
    return this.http.get<Page<DigitalProductPassport>>(this.orgBase('/digital-product-passports'), {
      params: buildHttpParams({ page: params.page ?? 1, pageSize: 20, search: params.search }),
    });
  }

  getPassport(passportId: string): Observable<DigitalProductPassport> {
    return this.http.get<DigitalProductPassport>(
      this.orgBase(`/digital-product-passports/${passportId}`),
    );
  }

  publishPassport(passportId: string): Observable<DigitalProductPassport> {
    return this.http.post<DigitalProductPassport>(
      this.orgBase(`/digital-product-passports/${passportId}/publish`),
      {},
    );
  }

  getPublicPassport(slug: string): Observable<PublicPassport> {
    return this.http.get<PublicPassport>(
      `${environment.apiUrl}${environment.apiV1Prefix}/public/passports/${slug}`,
    );
  }

  getPublicQr(slug: string): Observable<{ url: string; svg: string; status: string; disclaimer: string }> {
    return this.http.get<{ url: string; svg: string; status: string; disclaimer: string }>(
      `${environment.apiUrl}${environment.apiV1Prefix}/public/passports/${slug}/qr`,
    );
  }
}
