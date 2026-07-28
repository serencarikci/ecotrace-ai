import { TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { LoginComponent } from './login.component';
import { AuthService } from '../../core/services/auth.service';
import { of, throwError } from 'rxjs';

describe('LoginComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, ReactiveFormsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        AuthService,
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    localStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should validate required fields', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    component.submit();
    expect(component.form.invalid).toBeTrue();
    expect(component.form.controls.email.hasError('required')).toBeTrue();
  });

  it('should login successfully and navigate', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    const component = fixture.componentInstance;
    const router = TestBed.inject(Router);
    const navigateSpy = spyOn(router, 'navigate').and.resolveTo(true);
    const auth = TestBed.inject(AuthService);
    spyOn(auth, 'login').and.returnValue(
      of({
        accessToken: 'a',
        refreshToken: 'r',
        tokenType: 'bearer',
        expiresIn: 900,
        user: {
          id: '1',
          email: 'admin@ecotrace.dev',
          fullName: 'Admin',
          roles: ['system_admin'],
        },
      }),
    );
    spyOn(auth, 'loadMyOrganizations').and.returnValue(of([]));

    component.form.setValue({
      email: 'admin@ecotrace.dev',
      password: 'EcoTraceAdmin!2024',
    });
    component.submit();
    expect(navigateSpy).toHaveBeenCalledWith(['/app/dashboard']);
  });

  it('should show error on failed login', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    const component = fixture.componentInstance;
    const auth = TestBed.inject(AuthService);
    spyOn(auth, 'login').and.returnValue(
      throwError(() => ({ error: { error: { message: 'Invalid email or password.' } } })),
    );
    component.form.setValue({
      email: 'admin@ecotrace.dev',
      password: 'wrong-password',
    });
    component.submit();
    expect(component.errorMessage()).toContain('Invalid email or password.');
  });
});
