import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { TokenStorage } from '../services/token-storage';

/**
 * Endpoints that must go out WITHOUT a Bearer token, and must never trigger a
 * refresh-retry. `/auth/logout` is not in this list — it needs a valid access
 * token to revoke the refresh token.
 */
function isPublicAuthCall(request: HttpRequest<unknown>): boolean {
  return request.url.includes('/auth/login') || request.url.includes('/auth/refresh');
}

/**
 * Attaches the access token to every API call, and recovers from expiry:
 * on a 401 it refreshes once and retries the original request. If the refresh
 * fails the session is cleared and the user is sent to the login screen.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const tokens = inject(TokenStorage);
  const auth = inject(AuthService);
  const router = inject(Router);

  if (isPublicAuthCall(request)) {
    return next(request);
  }

  const withToken = (token: string | null) =>
    token
      ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : request;

  return next(withToken(tokens.accessToken())).pipe(
    catchError((error: HttpErrorResponse) => {
      // Only an expired/invalid token is worth retrying, and only if we still
      // hold a refresh token. A 403 means "signed in but not allowed" — that
      // must surface to the caller untouched.
      if (error.status !== 401 || !tokens.refreshToken()) {
        return throwError(() => error);
      }

      return auth.refresh().pipe(
        // AuthService.refresh() is single-flight, so simultaneous 401s all wait
        // on the same call and then each retry with the new token.
        switchMap((pair) => next(withToken(pair.access_token))),
        catchError((refreshError) => {
          auth.clearSession();
          router.navigate(['/login'], {
            queryParams: { returnUrl: router.url },
          });
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
