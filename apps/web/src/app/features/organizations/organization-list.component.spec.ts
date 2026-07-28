import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { OrganizationListComponent } from './organization-list.component';
import { AuthService } from '../../core/services/auth.service';

describe('OrganizationListComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    localStorage.setItem('ecotrace.accessToken', 'token');
    await TestBed.configureTestingModule({
      imports: [OrganizationListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        AuthService,
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('renders organizations from API', () => {
    const fixture: ComponentFixture<OrganizationListComponent> =
      TestBed.createComponent(OrganizationListComponent);
    fixture.detectChanges();
    const req = httpMock.expectOne((r) => r.url.includes('/organizations'));
    req.flush({
      items: [
        {
          id: '1',
          name: 'EcoTrace Demo Industries',
          slug: 'ecotrace-demo-industries',
          legalName: null,
          countryCode: 'DE',
          timezone: 'Europe/Berlin',
          isActive: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
      ],
      page: 1,
      pageSize: 20,
      totalItems: 1,
      totalPages: 1,
    });
    fixture.detectChanges();
    expect(fixture.componentInstance.organizations().length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('EcoTrace Demo Industries');
  });
});
