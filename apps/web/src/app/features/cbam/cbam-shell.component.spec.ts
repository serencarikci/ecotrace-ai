import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { CbamShellComponent } from './cbam-shell.component';
import { AuthService } from '../../core/services/auth.service';
import { routes } from '../../app.routes';
import { authGuard, organizationContextGuard } from '../../core/guards/auth.guard';
import { canViewCbam } from '../../core/services/roles.util';
import { environment } from '../../../environments/environment';

describe('CBAM / SKDM Phase 1 shell', () => {
  let httpMock: HttpTestingController;

  const authMock = {
    currentOrganizationId: signal('org-1'),
    organizations: signal([
      {
        organizationId: 'org-1',
        organizationName: 'Demo Org',
        organizationSlug: 'demo',
        roleCode: 'viewer',
        isActive: true,
      },
    ]),
    requireOrganizationId: () => 'org-1',
    isAuthenticated: () => true,
    hasAnyRole: (...roles: string[]) => roles.includes('viewer'),
    currentUser: signal({ roles: ['viewer'] }),
    currentRoles: signal(['viewer']),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamShellComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useValue: authMock },
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('registers lazy cbam route with auth and organization context guards', () => {
    const appRoute = routes.find((r) => r.path === 'app');
    const cbam = appRoute?.children?.find((r) => r.path === 'cbam');
    expect(cbam).toBeTruthy();
    expect(cbam?.canActivate?.length).toBe(3);
    expect(cbam?.canActivate?.[0]).toBe(authGuard);
    expect(cbam?.canActivate?.[1]).toBe(organizationContextGuard);
    expect(typeof cbam?.canActivate?.[2]).toBe('function');
    expect(typeof cbam?.loadComponent).toBe('function');
  });

  it('renders SKDM shell with honest not-implemented status', () => {
    const fixture: ComponentFixture<CbamShellComponent> =
      TestBed.createComponent(CbamShellComponent);
    fixture.detectChanges();
    const req = httpMock.expectOne(
      `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1/module-status`,
    );
    req.flush({
      module: 'cbam',
      uiLabelTr: 'SKDM',
      status: 'foundation_available',
      foundationAvailable: true,
      domainFunctionalityImplemented: false,
      complianceClaim: false,
      calculationImplemented: false,
      message:
        'CBAM module foundation is available. CBAM domain functionality is not implemented yet. No compliance claim is made.',
      permissionsDefined: ['cbam:view'],
    });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('SKDM');
    expect(text).toContain('henüz uygulanmadı');
    expect(text.toLowerCase()).not.toContain('compliant');
    expect(text.toLowerCase()).not.toContain('tco2e');
    expect(fixture.nativeElement.querySelector('canvas')).toBeNull();
    expect(fixture.nativeElement.querySelector('form')).toBeNull();
  });

  it('exposes canViewCbam for navigation visibility', () => {
    expect(canViewCbam(['viewer'])).toBeTrue();
    expect(canViewCbam(['system_admin'])).toBeTrue();
    expect(canViewCbam([])).toBeFalse();
  });
});
