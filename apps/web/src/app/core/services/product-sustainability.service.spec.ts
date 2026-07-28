import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ProductSustainabilityService } from './product-sustainability.service';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

describe('ProductSustainabilityService', () => {
  let service: ProductSustainabilityService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        ProductSustainabilityService,
        {
          provide: AuthService,
          useValue: { requireOrganizationId: () => 'org-1' },
        },
      ],
    });
    service = TestBed.inject(ProductSustainabilityService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists products for current organization', () => {
    service.listProducts({ page: 1 }).subscribe((page) => {
      expect(page.items.length).toBe(1);
    });
    const req = http.expectOne(
      (r) =>
        r.url ===
          `${environment.apiUrl}${environment.apiV1Prefix}/organizations/org-1/products` &&
        r.params.get('page') === '1',
    );
    expect(req.request.method).toBe('GET');
    req.flush({ items: [{ id: '1', code: 'P', name: 'N', productType: 'finished_good', defaultUnitCode: 'unit', organizationId: 'org-1', isActive: true }], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
  });

  it('loads public passport without auth org path', () => {
    service.getPublicPassport('ecobottle-750').subscribe((p) => {
      expect(p.publicSlug).toBe('ecobottle-750');
    });
    const req = http.expectOne(
      `${environment.apiUrl}${environment.apiV1Prefix}/public/passports/ecobottle-750`,
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      status: 'published',
      title: 'Demo',
      version: 1,
      publicSlug: 'ecobottle-750',
      product: {},
      manufacturer: {},
      sections: [],
      disclaimer: 'demo',
    });
  });
});
