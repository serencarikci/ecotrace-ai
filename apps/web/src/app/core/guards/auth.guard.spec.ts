import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { authGuard, guestGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('auth guards', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        AuthService,
      ],
    });
  });

  afterEach(() => localStorage.clear());

  it('authGuard redirects unauthenticated users to login', () => {
    const result = TestBed.runInInjectionContext(() => authGuard({} as never, {} as never));
    expect(String(result)).toContain('login');
  });

  it('authGuard allows authenticated users', () => {
    localStorage.setItem('ecotrace.accessToken', 'token');
    const result = TestBed.runInInjectionContext(() => authGuard({} as never, {} as never));
    expect(result).toBeTrue();
  });

  it('guestGuard redirects authenticated users to dashboard', () => {
    localStorage.setItem('ecotrace.accessToken', 'token');
    const result = TestBed.runInInjectionContext(() => guestGuard({} as never, {} as never));
    expect(String(result)).toContain('dashboard');
  });
});
