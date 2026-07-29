import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of } from 'rxjs';
import { ShellComponent } from './shell.component';
import { AuthService } from '../core/services/auth.service';
import { MeResponse } from '../core/models/api.models';

describe('ShellComponent role-based navigation', () => {
  async function setup(roles: string[]): Promise<ComponentFixture<ShellComponent>> {
    localStorage.setItem('ecotrace.accessToken', 'token');
    const user: MeResponse = {
      id: '1',
      email: 'user@ecotrace.dev',
      fullName: 'User',
      isActive: true,
      isVerified: true,
      roles,
      lastLoginAt: null,
    };
    localStorage.setItem('ecotrace.user', JSON.stringify(user));

    await TestBed.configureTestingModule({
      imports: [ShellComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: BreakpointObserver,
          useValue: { observe: () => of({ matches: false, breakpoints: {} }) },
        },
      ],
    }).compileComponents();

    const auth = TestBed.inject(AuthService);
    auth.currentUser.set(user);
    auth.organizations.set([
      {
        organizationId: 'org-1',
        organizationName: 'Demo Org',
        organizationSlug: 'demo',
        roleCode: roles[0] ?? 'viewer',
        isActive: true,
      },
    ]);

    const fixture = TestBed.createComponent(ShellComponent);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => {
    localStorage.clear();
    TestBed.resetTestingModule();
  });

  it('shows System Administration for system_admin', async () => {
    const fixture = await setup(['system_admin']);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('System Administration');
    expect(text).toContain('Units');
    expect(text).toContain('Activity Types');
    expect(text).toContain('Facilities');
    expect(text).toContain('Activity Data');
    expect(text).toContain('Carbon Accounting');
    expect(text).toContain('Carbon Inventories');
    expect(text).toContain('v0.7.3');
    expect(text).toContain('Intelligence');
    expect(text).toContain('AI Agents');
    expect(text).toContain('Health');
  });

  it('hides System Administration for viewer', async () => {
    const fixture = await setup(['viewer']);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('System Administration');
    expect(text).toContain('Facilities');
    expect(text).toContain('Carbon Accounting');
    expect(text).toContain('AI Copilot');
    expect(text).toContain('Sustainability Copilot');
    expect(text).toContain('Anomalies');
    expect(text).toContain('Automation Rules');
  });
});
