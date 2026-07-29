import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AuthService } from '../../core/services/auth.service';
import {
  AgentApprovalsComponent,
  AnomaliesComponent,
  ForecastFormComponent,
  RegulatoryListComponent,
  REG_DISCLAIMER,
  schedulePreview,
} from './ops-pages.component';

describe('Ops pages', () => {
  beforeEach(async () => {
    localStorage.setItem('ecotrace.selectedOrganizationId', 'org-1');
    await TestBed.configureTestingModule({
      imports: [
        AgentApprovalsComponent,
        AnomaliesComponent,
        ForecastFormComponent,
        RegulatoryListComponent,
        NoopAnimationsModule,
      ],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    const auth = TestBed.inject(AuthService);
    auth.organizations.set([
      {
        organizationId: 'org-1',
        organizationName: 'Demo',
        organizationSlug: 'demo',
        roleCode: 'organization_admin',
        isActive: true,
      },
    ]);
    auth.selectOrganization('org-1');
  });

  afterEach(() => localStorage.clear());

  it('renders schedule preview helper', () => {
    expect(schedulePreview('monthly')).toContain('month');
  });

  it('shows regulatory disclaimer', () => {
    const fixture = TestBed.createComponent(RegulatoryListComponent);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(REG_DISCLAIMER);
  });

  it('shows anomaly disclaimer', () => {
    const fixture = TestBed.createComponent(AnomaliesComponent);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'not automatically an error',
    );
  });

  it('shows approval policy copy', () => {
    const fixture = TestBed.createComponent(AgentApprovalsComponent);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'never execute before approval',
    );
  });

  it('creates forecast form component', () => {
    const fixture = TestBed.createComponent(ForecastFormComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });
});
