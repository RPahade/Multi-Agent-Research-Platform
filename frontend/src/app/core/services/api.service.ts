import { HttpClient, HttpEvent, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Page } from '../models';

/** Query params: primitives only, and empty values are dropped. */
export type QueryParams = Record<string, string | number | boolean | undefined | null>;

/**
 * Thin wrapper around HttpClient.
 *
 * It only does two things: prefix the API base URL, and turn a params object
 * into HttpParams while dropping empty filters (so `?q=` never gets sent).
 * Auth headers are NOT added here — that is the interceptor's job (M10).
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  /** Full URL for a path, e.g. url('/jobs/1') -> '/api/v1/jobs/1'. */
  url(path: string): string {
    return `${environment.apiUrl}${path}`;
  }

  get<T>(path: string, params?: QueryParams): Observable<T> {
    return this.http.get<T>(this.url(path), { params: toHttpParams(params) });
  }

  /** Same as get(), typed for the `{ items, total, page, size, pages }` wrapper. */
  getPage<T>(path: string, params?: QueryParams): Observable<Page<T>> {
    return this.get<Page<T>>(path, params);
  }

  /** `headers` is for the odd endpoint that needs one, e.g. Idempotency-Key. */
  post<T>(path: string, body?: unknown, headers?: Record<string, string>): Observable<T> {
    return this.http.post<T>(this.url(path), body ?? {}, { headers });
  }

  /**
   * Multipart upload that reports progress.
   *
   * Returns the raw event stream (`observe: 'events'`) so the caller can drive a
   * progress bar; the calling service turns it into something friendlier.
   * Do NOT set a Content-Type — the browser adds the multipart boundary itself.
   */
  upload<T>(path: string, form: FormData): Observable<HttpEvent<T>> {
    return this.http.post<T>(this.url(path), form, {
      reportProgress: true,
      observe: 'events',
    });
  }

  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(this.url(path), body);
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(this.url(path));
  }
}

/** Drops undefined, null and '' so unset filters are left out of the URL. */
function toHttpParams(params?: QueryParams): HttpParams {
  let httpParams = new HttpParams();
  if (!params) {
    return httpParams;
  }
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      httpParams = httpParams.set(key, String(value));
    }
  }
  return httpParams;
}
