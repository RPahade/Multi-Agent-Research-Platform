import { HttpParams } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, of, shareReplay, switchMap, tap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { TokenPair, User, UserRole } from '../models';
import { ApiService } from './api.service';
import { TokenStorage } from './token-storage';

/**
 * Everything about the signed-in session: login, logout, token refresh and the
 * current user. Components read `user()` / `isAuthenticated()` / `role()`.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly tokens = inject(TokenStorage);

  private readonly _user = signal<User | null>(null);

  readonly user = this._user.asReadonly();
  readonly isAuthenticated = computed(() => this._user() !== null);
  readonly role = computed<UserRole | null>(() => this._user()?.role ?? null);

  /** The refresh request currently in progress, if any (see `refresh()`). */
  private refreshInFlight: Observable<TokenPair> | null = null;

  /**
   * Sign in. The backend uses the OAuth2 password form, so this is
   * form-encoded — not JSON — and the email goes in the `username` field.
   * Passing HttpParams as the body makes Angular set the right Content-Type.
   */
  login(email: string, password: string): Observable<User> {
    const body = new HttpParams().set('username', email).set('password', password);

    return this.api.post<TokenPair>('/auth/login', body).pipe(
      tap((pair) => this.tokens.set(pair)),
      switchMap(() => this.loadCurrentUser()),
    );
  }

  /** Fetch the signed-in user and cache it in the `user` signal. */
  loadCurrentUser(): Observable<User> {
    return this.api.get<User>('/auth/me').pipe(tap((user) => this._user.set(user)));
  }

  /**
   * Exchange the refresh token for a new pair.
   *
   * Single-flight on purpose: if several requests get a 401 at the same moment
   * they must all wait on ONE refresh call. Firing several in parallel would
   * fail, because rotation invalidates each token as the next call uses it.
   */
  refresh(): Observable<TokenPair> {
    if (this.refreshInFlight) {
      return this.refreshInFlight;
    }

    const refreshToken = this.tokens.refreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token stored.'));
    }

    this.refreshInFlight = this.api
      .post<TokenPair>('/auth/refresh', { refresh_token: refreshToken })
      .pipe(
        tap({
          next: (pair) => {
            this.tokens.set(pair);
            this.refreshInFlight = null;
          },
          error: () => {
            this.refreshInFlight = null;
          },
        }),
        shareReplay({ bufferSize: 1, refCount: false }),
      );

    return this.refreshInFlight;
  }

  /** Revoke the refresh token server-side, then drop the local session. */
  logout(): Observable<unknown> {
    const refreshToken = this.tokens.refreshToken();

    const revoke = refreshToken
      ? this.api
          .post('/auth/logout', { refresh_token: refreshToken })
          // Already expired or revoked? Sign out locally regardless.
          .pipe(catchError(() => of(null)))
      : of(null);

    return revoke.pipe(tap(() => this.clearSession()));
  }

  clearSession(): void {
    this.tokens.clear();
    this._user.set(null);
  }

  /**
   * Runs once at start-up (see app.config.ts).
   *
   * The access token only lives in memory, so after a reload all we have is the
   * refresh token: swap it for a new access token, then load the user. Doing it
   * before the app renders avoids a flash of the login screen.
   */
  restoreSession(): Observable<unknown> {
    if (!this.tokens.refreshToken()) {
      return of(null);
    }

    return this.refresh().pipe(
      switchMap(() => this.loadCurrentUser()),
      catchError(() => {
        // Refresh token expired or revoked — start clean.
        this.clearSession();
        return of(null);
      }),
    );
  }
}
