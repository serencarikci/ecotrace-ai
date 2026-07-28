import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const refreshInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401) {
        return throwError(() => error);
      }
      if (req.url.includes('/auth/login') || req.url.includes('/auth/refresh')) {
        return throwError(() => error);
      }
      if (!auth.getRefreshToken()) {
        auth.clearSession();
        void router.navigate(['/login']);
        return throwError(() => error);
      }

      return auth.refresh().pipe(
        switchMap(() => {
          const token = auth.getAccessToken();
          const retry = req.clone({
            setHeaders: token ? { Authorization: `Bearer ${token}` } : {},
          });
          return next(retry);
        }),
        catchError((refreshError) => {
          auth.clearSession();
          void router.navigate(['/login']);
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
