import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { CarbonService } from './carbon.service';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

describe('CarbonService', () => {
  let api: CarbonService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
          },
        },
      ],
    });
    api = TestBed.inject(CarbonService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists emission factors with filters', () => {
    api.listFactors({ scope: 'scope_1', status: 'active', page: 1 }).subscribe();
    const req = http.expectOne(
      (r) =>
        r.url === `${environment.apiUrl}${environment.apiV1Prefix}/emission-factors` &&
        r.params.get('scope') === 'scope_1' &&
        r.params.get('status') === 'active',
    );
    expect(req.request.method).toBe('GET');
    req.flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
  });

  it('posts inventory calculate with partial flag', () => {
    api.calculateInventory('inv-1', true).subscribe();
    const req = http.expectOne(
      `${environment.apiUrl}${environment.apiV1Prefix}/organizations/org-1/carbon-inventories/inv-1/calculate`,
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ partialCalculation: true });
    req.flush({
      id: 'run-1',
      inventoryId: 'inv-1',
      runNumber: 1,
      status: 'completed',
      startedAt: null,
      completedAt: null,
      triggeredByUserId: null,
      activityRecordCount: 0,
      calculatedRecordCount: 0,
      skippedRecordCount: 0,
      failedRecordCount: 0,
      totalKgCo2e: '0',
      totalTCo2e: '0',
      errorSummaryJson: null,
      engineVersion: '3.0.0',
      partialCalculation: true,
    });
  });
});
