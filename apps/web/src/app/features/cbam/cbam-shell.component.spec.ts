import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Routes, UrlTree } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { Component, signal } from '@angular/core';
import { CbamShellComponent } from './cbam-shell.component';
import { AuthService } from '../../core/services/auth.service';
import { authGuard, organizationContextGuard, roleGuard } from '../../core/guards/auth.guard';
import { CBAM_VIEW_ROLES, canViewCbam } from '../../core/services/roles.util';
import { environment } from '../../../environments/environment';

@Component({
  standalone: true,
  template: '<p>placeholder</p>',
})
class PlaceholderComponent {}

describe('CBAM / SKDM shell and guards', () => {
  let httpMock: HttpTestingController;

  const authMock = {
    currentOrganizationId: signal<string | null>('org-1'),
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

  const cbamRoutes: Routes = [
    { path: '', pathMatch: 'full', component: PlaceholderComponent },
    {
      path: 'app/cbam',
      canActivate: [authGuard, organizationContextGuard, roleGuard(...CBAM_VIEW_ROLES)],
      loadComponent: () => import('./cbam-shell.component').then((m) => m.CbamShellComponent),
    },
    { path: 'login', component: PlaceholderComponent },
    { path: 'unauthorized', component: PlaceholderComponent },
    { path: 'app/organizations', component: PlaceholderComponent },
  ];

  async function configure(routes: Routes = cbamRoutes): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [CbamShellComponent, PlaceholderComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes),
        { provide: AuthService, useValue: authMock },
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    authMock.currentOrganizationId.set('org-1');
    authMock.isAuthenticated = () => true;
    authMock.hasAnyRole = (...roles: string[]) => roles.includes('viewer');
  }

  afterEach(() => {
    httpMock?.verify();
    TestBed.resetTestingModule();
  });

  it('renders SKDM shell with honest foundation status', async () => {
    await configure([]);
    const fixture: ComponentFixture<CbamShellComponent> =
      TestBed.createComponent(CbamShellComponent);
    fixture.detectChanges();
    const req = httpMock.expectOne(
      `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1/module-status`,
    );
    req.flush({
      module: 'cbam',
      uiLabelTr: 'SKDM',
      status: 'mvp_ready_for_domain_validation',
      foundationAvailable: true,
      domainFunctionalityImplemented: true,
      complianceClaim: false,
      calculationImplemented: true,
      reportingImplemented: true,
      message:
        'SKDM tools are ready for review. Official Excel export is available when period data is complete. No compliance claim is made.',
      enforcedPermissions: ['cbam:view', 'cbam:configure'],
    });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('SKDM');
    expect(text).toContain('Installations');
    expect(text).toContain('Reporting Periods');
    expect(text).toContain('Official Excel');
    expect(text).not.toContain('BLOCKED');
    expect(text).not.toContain('READY_FOR_DOMAIN_VALIDATION');
    expect(text.toLowerCase()).not.toContain('compliant');
    expect(text.toLowerCase()).not.toContain('tco2e');
    expect(fixture.nativeElement.querySelector('canvas')).toBeNull();
  });

  it('rejects navigation when organization context is missing', async () => {
    await configure();
    authMock.currentOrganizationId.set(null);
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/app/cbam');
    expect(harness.routeNativeElement?.textContent).not.toContain('SKDM');
    expect(String(harness.routeNativeElement?.textContent ?? '')).toContain('placeholder');
  });

  it('rejects navigation when user lacks CBAM view role', async () => {
    await configure();
    authMock.hasAnyRole = () => false;
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/app/cbam');
    expect(harness.routeNativeElement?.textContent).not.toContain('SKDM');
  });

  it('activates CBAM shell for authorized user with organization context', async () => {
    await configure();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/app/cbam');
    const req = httpMock.expectOne(
      `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1/module-status`,
    );
    req.flush({
      module: 'cbam',
      uiLabelTr: 'SKDM',
      status: 'mvp_ready_for_domain_validation',
      foundationAvailable: true,
      domainFunctionalityImplemented: true,
      complianceClaim: false,
      calculationImplemented: true,
      reportingImplemented: true,
      message:
        'SKDM tools are ready for review. Official Excel export is available when period data is complete. No compliance claim is made.',
      enforcedPermissions: ['cbam:view', 'cbam:configure'],
    });
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('SKDM');
    expect(harness.routeNativeElement?.textContent).toContain('Official Excel');
    expect(harness.routeNativeElement?.textContent).not.toContain('BLOCKED');
    expect(harness.routeNativeElement?.textContent).not.toContain('READY_FOR_DOMAIN_VALIDATION');
  });

  it('organizationContextGuard redirects when organization context is missing', async () => {
    await configure([]);
    authMock.currentOrganizationId.set(null);
    const result = TestBed.runInInjectionContext(() =>
      organizationContextGuard({} as never, {} as never),
    );
    expect(result instanceof UrlTree || String(result).includes('organizations')).toBeTrue();
    expect(String(result)).toContain('organizations');
  });

  it('CBAM role guard rejects user without an allowed view role', async () => {
    await configure([]);
    authMock.hasAnyRole = () => false;
    const guard = roleGuard(...CBAM_VIEW_ROLES);
    const result = TestBed.runInInjectionContext(() => guard({} as never, {} as never));
    expect(result instanceof UrlTree || String(result).includes('unauthorized')).toBeTrue();
    expect(String(result)).toContain('unauthorized');
  });

  it('authGuard redirects unauthenticated users away from CBAM', async () => {
    await configure([]);
    authMock.isAuthenticated = () => false;
    const result = TestBed.runInInjectionContext(() => authGuard({} as never, {} as never));
    expect(String(result)).toContain('login');
  });

  it('exposes canViewCbam for navigation visibility helpers', () => {
    expect(canViewCbam(['viewer'])).toBeTrue();
    expect(canViewCbam(['system_admin'])).toBeTrue();
    expect(canViewCbam([])).toBeFalse();
  });
});
