import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { environment } from '../../../environments/environment';
import { CbamInstallationListComponent } from './installation-list.component';

describe('CbamInstallationListComponent', () => {
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<CbamInstallationListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamInstallationListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
            currentRoles: signal(['organization_admin']),
          },
        },
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(CbamInstallationListComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('lists installations and exposes create for configure roles', () => {
    const req = httpMock.expectOne(
      (r) =>
        r.url ===
        `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1/installations`,
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      items: [
        {
          id: 'i1',
          organizationId: 'org-1',
          facilityId: 'f1',
          code: 'INST-1',
          name: 'Demo',
          status: 'draft',
          timezone: 'UTC',
          operatorIdentityRef: null,
          metadataJson: null,
          rowVersion: 1,
        },
      ],
      page: 1,
      pageSize: 20,
      totalItems: 1,
      totalPages: 1,
    });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('SKDM Installations');
    expect(text).toContain('INST-1');
    expect(text).toContain('New Installation');
    expect(text.toLowerCase()).not.toContain('cn code');
    expect(text.toLowerCase()).not.toContain('calculation');
  });
});
