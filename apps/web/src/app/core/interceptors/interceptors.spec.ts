import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { authInterceptor } from './auth.interceptor';
import { refreshInterceptor } from './refresh.interceptor';
import { AuthService } from '../services/auth.service';

describe('HTTP interceptors', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor, refreshInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
        AuthService,
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('attaches Authorization header when access token exists', () => {
    localStorage.setItem('ecotrace.accessToken', 'access-123');
    http.get('/api/v1/auth/me').subscribe();
    const req = httpMock.expectOne('/api/v1/auth/me');
    expect(req.request.headers.get('Authorization')).toBe('Bearer access-123');
    req.flush({
      id: '1',
      email: 'a@b.c',
      fullName: 'A',
      isActive: true,
      isVerified: true,
      roles: [],
      lastLoginAt: null,
    });
  });

  it('refreshes token once on 401 and retries', () => {
    localStorage.setItem('ecotrace.accessToken', 'old');
    localStorage.setItem('ecotrace.refreshToken', 'refresh-1');

    http.get('/api/v1/organizations').subscribe();
    const first = httpMock.expectOne('/api/v1/organizations');
    first.flush({ error: { code: 'AUTHENTICATION_ERROR', message: 'expired' } }, { status: 401, statusText: 'Unauthorized' });

    const refresh = httpMock.expectOne((r) => r.url.includes('/auth/refresh'));
    refresh.flush({
      accessToken: 'new-access',
      refreshToken: 'new-refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: { id: '1', email: 'a@b.c', fullName: 'A', roles: [] },
    });

    const retry = httpMock.expectOne('/api/v1/organizations');
    expect(retry.request.headers.get('Authorization')).toBe('Bearer new-access');
    retry.flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
  });

  it('clears session on logout', () => {
    localStorage.setItem('ecotrace.accessToken', 'a');
    localStorage.setItem('ecotrace.refreshToken', 'r');
    auth.clearSession();
    expect(auth.getAccessToken()).toBeNull();
    expect(auth.currentUser()).toBeNull();
  });
});
