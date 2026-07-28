import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { FacilityFormComponent } from './facility-form.component';

describe('FacilityFormComponent', () => {
  let fixture: ComponentFixture<FacilityFormComponent>;
  let component: FacilityFormComponent;

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
    await TestBed.configureTestingModule({
      imports: [FacilityFormComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(FacilityFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('requires code, name, and country code', () => {
    component.form.patchValue({
      code: '',
      name: '',
      countryCode: 'X',
    });
    component.submit();
    expect(component.form.invalid).toBeTrue();
    expect(component.form.controls.code.hasError('required')).toBeTrue();
    expect(component.form.controls.name.hasError('required')).toBeTrue();
    expect(component.form.controls.countryCode.hasError('pattern')).toBeTrue();
  });

  it('accepts a valid facility payload shape', () => {
    component.form.patchValue({
      code: 'IZM-01',
      name: 'Izmir Plant',
      facilityType: 'manufacturing',
      countryCode: 'TR',
      timezone: 'Europe/Istanbul',
    });
    expect(component.form.valid).toBeTrue();
  });
});
