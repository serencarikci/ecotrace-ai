import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ImportWizardComponent } from './import-wizard.component';

describe('ImportWizardComponent steps', () => {
  let fixture: ComponentFixture<ImportWizardComponent>;
  let component: ImportWizardComponent;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    localStorage.setItem('ecotrace.accessToken', 'token');
    localStorage.setItem(
      'ecotrace.user',
      JSON.stringify({
        id: '1',
        email: 'admin@ecotrace.dev',
        fullName: 'Admin',
        isActive: true,
        isVerified: true,
        roles: ['system_admin'],
        lastLoginAt: null,
      }),
    );
    localStorage.setItem(
      'ecotrace.selectedOrganizationId',
      '11111111-1111-1111-1111-111111111111',
    );

    await TestBed.configureTestingModule({
      imports: [ImportWizardComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    const authModule = await import('../../core/services/auth.service');
    const auth = TestBed.inject(authModule.AuthService);
    auth.organizations.set([
      {
        organizationId: '11111111-1111-1111-1111-111111111111',
        organizationName: 'Demo',
        organizationSlug: 'demo',
        roleCode: 'system_admin',
        isActive: true,
      },
    ]);
    auth.selectOrganization('11111111-1111-1111-1111-111111111111');

    fixture = TestBed.createComponent(ImportWizardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('starts on template step', () => {
    expect(component.step()).toBe('template');
    expect(component.stepIndex()).toBe(0);
    expect(fixture.nativeElement.textContent).toContain('Download template');
  });

  it('moves to select after skipping download', () => {
    component.step.set('select');
    fixture.detectChanges();
    expect(component.step()).toBe('select');
    expect(fixture.nativeElement.textContent).toContain('Select a CSV file');
  });

  it('uploads then advances to validate', () => {
    component.selectedFile.set(new File(['a,b'], 'demo.csv', { type: 'text/csv' }));
    component.step.set('upload');
    component.upload();
    const req = httpMock.expectOne((r) => r.url.includes('/imports/activity-records'));
    expect(req.request.method).toBe('POST');
    req.flush({
      id: 'job-1',
      organizationId: '11111111-1111-1111-1111-111111111111',
      fileName: 'demo.csv',
      storedFileName: 'stored.csv',
      status: 'uploaded',
      totalRows: 0,
      validRows: 0,
      invalidRows: 0,
      importedRows: 0,
      duplicateRows: 0,
      startedAt: null,
      completedAt: null,
      createdByUserId: null,
      executedAt: null,
    });
    expect(component.jobId()).toBe('job-1');
    expect(component.step()).toBe('validate');
  });
});
