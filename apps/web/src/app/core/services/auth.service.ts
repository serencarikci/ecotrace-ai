import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, throwError, finalize, shareReplay } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  MeResponse,
  OrganizationMembership,
  TokenResponse,
} from '../models/api.models';

const ACCESS_KEY = 'ecotrace.accessToken';
const REFRESH_KEY = 'ecotrace.refreshToken';
const USER_KEY = 'ecotrace.user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = `${environment.apiUrl}${environment.apiV1Prefix}/auth`;
  private refreshInFlight: Observable<TokenResponse> | null = null;

  readonly currentUser = signal<MeResponse | null>(this.readStoredUser());
  readonly organizations = signal<OrganizationMembership[]>([]);
  readonly selectedOrganizationId = signal<string | null>(
    localStorage.getItem('ecotrace.selectedOrganizationId'),
  );
  readonly isAuthenticated = computed(() => !!this.getAccessToken());
  readonly currentOrganizationId = computed(() => {
    const selected = this.selectedOrganizationId();
    const orgs = this.organizations();
    if (selected && orgs.some((o) => o.organizationId === selected)) {
      return selected;
    }
    return orgs[0]?.organizationId ?? null;
  });
  readonly currentRoles = computed(() => this.currentUser()?.roles ?? []);

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router,
  ) {}

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.api}/login`, { email, password }).pipe(
      tap((response) => this.persistSession(response)),
    );
  }

  refresh(): Observable<TokenResponse> {
    if (this.refreshInFlight) {
      return this.refreshInFlight;
    }
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token'));
    }
    this.refreshInFlight = this.http
      .post<TokenResponse>(`${this.api}/refresh`, { refreshToken })
      .pipe(
        tap((response) => this.persistSession(response)),
        catchError((err) => {
          this.clearSession();
          return throwError(() => err);
        }),
        finalize(() => {
          this.refreshInFlight = null;
        }),
        shareReplay(1),
      );
    return this.refreshInFlight;
  }

  logout(): Observable<void> {
    const refreshToken = this.getRefreshToken();
    const request$ = refreshToken
      ? this.http.post<void>(`${this.api}/logout`, { refreshToken })
      : new Observable<void>((subscriber) => {
          subscriber.next();
          subscriber.complete();
        });
    return request$.pipe(
      catchError(() => {
        return new Observable<void>((subscriber) => {
          subscriber.next();
          subscriber.complete();
        });
      }),
      tap(() => {
        this.clearSession();
        void this.router.navigate(['/login']);
      }),
    );
  }

  loadMe(): Observable<MeResponse> {
    return this.http.get<MeResponse>(`${this.api}/me`).pipe(
      tap((me) => {
        this.currentUser.set(me);
        localStorage.setItem(USER_KEY, JSON.stringify(me));
      }),
    );
  }

  loadMyOrganizations(): Observable<OrganizationMembership[]> {
    return this.http.get<OrganizationMembership[]>(`${this.api}/me/organizations`).pipe(
      tap((orgs) => {
        this.organizations.set(orgs);
        const selected = this.selectedOrganizationId();
        if (!selected || !orgs.some((o) => o.organizationId === selected)) {
          this.selectOrganization(orgs[0]?.organizationId ?? null);
        }
      }),
    );
  }

  selectOrganization(organizationId: string | null): void {
    this.selectedOrganizationId.set(organizationId);
    if (organizationId) {
      localStorage.setItem('ecotrace.selectedOrganizationId', organizationId);
    } else {
      localStorage.removeItem('ecotrace.selectedOrganizationId');
    }
  }

  requireOrganizationId(): string {
    const orgId = this.currentOrganizationId();
    if (!orgId) {
      throw new Error('No organization selected.');
    }
    return orgId;
  }

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  clearSession(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem('ecotrace.selectedOrganizationId');
    this.currentUser.set(null);
    this.organizations.set([]);
    this.selectedOrganizationId.set(null);
  }

  hasAnyRole(...roles: string[]): boolean {
    const user = this.currentUser();
    if (!user) {
      return false;
    }
    return roles.some((role) => user.roles.includes(role));
  }

  private persistSession(response: TokenResponse): void {
    localStorage.setItem(ACCESS_KEY, response.accessToken);
    localStorage.setItem(REFRESH_KEY, response.refreshToken);
    const me: MeResponse = {
      id: response.user.id,
      email: response.user.email,
      fullName: response.user.fullName,
      isActive: true,
      isVerified: true,
      roles: response.user.roles,
      lastLoginAt: null,
    };
    this.currentUser.set(me);
    localStorage.setItem(USER_KEY, JSON.stringify(me));
  }

  private readStoredUser(): MeResponse | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as MeResponse;
    } catch {
      return null;
    }
  }
}
