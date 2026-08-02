import { Injectable, signal } from '@angular/core';

import { TokenPair } from '../models';

/** localStorage key for the refresh token. */
const REFRESH_KEY = 'mar.refresh_token';

/**
 * Holds the JWTs.
 *
 * - **access token: in memory only.** It is short-lived (~30 min) and never
 *   touches disk, so it cannot be read back out of the browser later.
 * - **refresh token: localStorage.** It has to survive a page reload, otherwise
 *   every refresh would send the user back to the login screen.
 *
 * This service deliberately has no HttpClient dependency, so the auth
 * interceptor can read the token without creating a circular dependency.
 */
@Injectable({ providedIn: 'root' })
export class TokenStorage {
  private readonly _accessToken = signal<string | null>(null);
  private readonly _refreshToken = signal<string | null>(
    localStorage.getItem(REFRESH_KEY),
  );

  readonly accessToken = this._accessToken.asReadonly();
  readonly refreshToken = this._refreshToken.asReadonly();

  /**
   * Stores a freshly issued pair.
   *
   * The backend rotates refresh tokens — every refresh invalidates the previous
   * one — so the newest pair must always replace the old one straight away.
   */
  set(pair: TokenPair): void {
    this._accessToken.set(pair.access_token);
    this._refreshToken.set(pair.refresh_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
  }

  clear(): void {
    this._accessToken.set(null);
    this._refreshToken.set(null);
    localStorage.removeItem(REFRESH_KEY);
  }
}
